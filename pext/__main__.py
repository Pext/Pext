#!/usr/bin/env python3

# Copyright (c) 2015 - 2023 Sylvia van Os <sylvia@hackerchick.me>
#
# This file is part of Pext.
#
# Pext is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Pext.

This is the main Pext file. It will initialize, run and manage the whole of
Pext.
"""

import argparse
import atexit
import configparser
import json
import os
import platform
import re
import signal
import sys
import threading
import traceback

from importlib import reload  # type: ignore
from inspect import getmembers, isfunction, ismethod, signature
from shutil import rmtree
from subprocess import check_output, CalledProcessError
from queue import Queue, Empty
try:
    from typing import Any, Callable, Dict, List, Optional, Union
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional, Union  # type: ignore  # noqa: F401

import requests

from dulwich import client, porcelain
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor

from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.Qt import QIcon
from PyQt5.QtGui import QPalette, QColor

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pext.configretriever import ConfigRetriever
from pext.enums import OutputMode, SortMode, UIType
from pext.localemanager import LocaleManager
from pext.settings import Logger, ObjectManager, ProfileManager, Settings, UpdateManager
from pext.translation import Translation
from pext.uimodule import UiModule
from pext.viewmodel import ViewModel

client.get_ssh_vendor = ParamikoSSHVendor

from pext.appfile import AppFile  # noqa: E402
# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(os.path.join(AppFile.get_path(), 'helpers'))
sys.path.append(os.path.join(AppFile.get_path()))

from pext_base import ModuleBase  # noqa: E402
from pext_helpers import Action, Selection  # noqa: E402


class Core():
    """Core-related functionality."""

    __active_modules = []  # type: List[UiModule]
    __focused_module = -1

    @staticmethod
    def add_module(module: UiModule, index=None) -> int:
        """Add a module to the list of active modules."""
        if index is not None:
            Core.__active_modules.insert(index, module)
            return index

        Core.__active_modules.append(module)
        return len(Core.__active_modules) - 1

    @staticmethod
    def remove_module(index: int) -> None:
        """Remove a module from the list of active modules."""
        del Core.__active_modules[index]

    @staticmethod
    def get_module(index: int) -> UiModule:
        """Get a module by index."""
        return Core.__active_modules[index]

    @staticmethod
    def get_modules() -> List[UiModule]:
        """Get all active modules."""
        return Core.__active_modules

    @staticmethod
    def get_focused_module_id() -> int:
        """Get the id (index) of the focused module."""
        return Core.__focused_module

    @staticmethod
    def set_focused_module_id(index: int) -> None:
        """Set the id (index) of the focused module."""
        Core.__focused_module = index

    @staticmethod
    def restart(extra_args=None):
        """Restart Pext, possibly with extra arguments."""
        # Call _shut_down manually because it isn't called when using os.execv
        Core._shut_down()

        args = [sys.executable, "-m", "pext"]
        args.extend(sys.argv[1:])
        if extra_args:
            args.extend(extra_args)

        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

        print(args)
        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    @staticmethod
    def _shut_down() -> None:
        """Clean up."""
        modules = Core.get_modules()

        profile = Settings.get('profile')
        ProfileManager().save_modules(profile, modules)

        for module in modules:
            try:
                module.vm.stop()
            except Exception as e:
                print("Failed to cleanly stop module {}: {}".format(module.metadata['name'], e))
                traceback.print_exc()

        ProfileManager.unlock_profile(profile)


class RunConseq():
    """A simple helper to run several functions consecutively."""

    def __init__(self, functions: List) -> None:
        """Run the given function consecutively."""
        for function in functions:
            if len(function['args']) > 0:
                function['name'](*function['args'], **function['kwargs'])
            else:
                function['name'](**function['kwargs'])


class InternalCallProcessor():
    """Process internal calls."""

    queue = Queue()  # type: Queue

    window = None
    module_manager = None
    theme_manager = None

    # Temporarily store module_data between reload phases
    temp_module_datas = []  # type: List[Dict[str, Any]]

    @staticmethod
    def bind(window: 'Window', module_manager: 'ModuleManager',  # type: ignore # noqa: F821
             theme_manager: 'ThemeManager') -> None:
        """Bind the Window, ModuleManager and ThemeManager to the InternalCallProcessor."""
        if window is not None:
            InternalCallProcessor.window = window

        if module_manager is not None:
            InternalCallProcessor.module_manager = module_manager

        if theme_manager is not None:
            InternalCallProcessor.theme_manager = theme_manager

    @staticmethod
    def enqueue(call: str) -> None:
        """Queue an internal call."""
        InternalCallProcessor.queue.put(call)

    @staticmethod
    def process() -> None:
        """Process an internal call."""
        try:
            call = InternalCallProcessor.queue.get_nowait()
        except Empty:
            return

        parts = call.split(":")
        if parts[0] != "pext":
            raise ValueError("Cannot process non-pext call")

        # Call function
        getattr(InternalCallProcessor, "_{}".format(parts[1].replace('-', '_')))(parts[2:])

    @staticmethod
    def _update_module_in_use(arguments: List) -> None:
        # update-module-in-use
        #   module_id
        if not InternalCallProcessor.module_manager:
            raise ValueError("Module manager not yet initialized.")

        if not InternalCallProcessor.window:
            raise ValueError("Window not yet initialized.")

        functions = [
            {
                'name': InternalCallProcessor.module_manager.update,
                'args': (arguments[0], True,),
                'kwargs': {}
            }
        ]

        for index, module in enumerate(Core.get_modules()):
            if module.metadata['id'] == arguments[0]:
                module_data = InternalCallProcessor.module_manager.reload_step_unload(
                    index,
                    InternalCallProcessor.window
                )
                InternalCallProcessor.temp_module_datas.append(module_data)
                functions.append({
                    'name': InternalCallProcessor.enqueue,
                    'args': ("pext:finalize-module:{}:{}".format(
                        index, len(InternalCallProcessor.temp_module_datas) - 1),),
                    'kwargs': {}
                })

        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    @staticmethod
    def _finalize_module(arguments: List) -> None:
        # finalize-module
        #   tab_id
        #   module_data (multiple fields likely, json contains also :
        if not InternalCallProcessor.module_manager:
            raise ValueError("Module manager not yet initialized.")

        if not InternalCallProcessor.window:
            raise ValueError("Window not yet initialized.")

        InternalCallProcessor.module_manager.reload_step_load(
            int(arguments[0]),
            InternalCallProcessor.temp_module_datas[int(arguments[1])],
            InternalCallProcessor.window
        )

    @staticmethod
    def _open_load_tab(arguments: List) -> None:
        # open-load-tab
        if not InternalCallProcessor.window:
            raise ValueError("Window not yet initialized.")

        InternalCallProcessor.window.open_load_tab()

    @staticmethod
    def _update_theme(arguments: List) -> None:
        # update-theme
        #   theme_id
        if not InternalCallProcessor.theme_manager:
            raise ValueError("Theme manager not yet initialized.")

        InternalCallProcessor.theme_manager.update(arguments[0], True)


class PextFileSystemEventHandler(FileSystemEventHandler):
    """Watches the file system to ensure state changes when relevant."""

    def __init__(self, window: 'Window', modules_path: str):  # type: ignore # noqa: F821
        """Initialize filesystem event handler."""
        self.window = window
        self.modules_path = modules_path

    def on_deleted(self, event):
        """Unload modules on deletion."""
        if not event.is_directory:
            return

        if event.src_path.startswith(self.modules_path):
            for index, module in enumerate(Core.get_modules()):
                if event.src_path == os.path.join(self.modules_path, module.metadata['id'].replace('.', '_')):
                    print("Module {} was removed, sending unload event".format(module.metadata['id']))
                    self.window.module_manager.unload(index, False, self.window)


class MainLoop():
    """Main application loop.

    The main application loop connects the application, queue and UI events and
    ensures these events get managed without locking up the UI.
    """

    def __init__(self, app: QApplication, main_loop_queue: Queue, module_manager: 'ModuleManager',
                 window: 'Window') -> None:  # type: ignore # noqa: F821
        """Initialize the main loop."""
        self.app = app
        self.main_loop_queue = main_loop_queue
        self.module_manager = module_manager
        self.window = window

    def _process_module_action(self, index: int, module: UiModule, focused_module: bool) -> None:
        action = module.vm.queue.get_nowait()

        if action[0] == Action.critical_error:
            # Stop the module
            self.module_manager.stop(index)

            # Disable with reason: crash
            self.window.disable_module(index, 1)

            if len(action) > 2:
                self.window.update_state(index, action[2])

            # Log critical error
            Logger.log_critical(
                module.metadata['name'],
                str(action[1]),
                str(action[2]) if len(action) > 2 else None,
                module.metadata
            )
        elif action[0] == Action.add_message:
            Logger.log(module.metadata['name'], str(action[1]))

        elif action[0] == Action.add_error:
            Logger.log_error(module.metadata['name'], str(action[1]))

        elif action[0] == Action.add_entry:
            module.vm.entry_list = module.vm.entry_list + [action[1]]

        elif action[0] == Action.prepend_entry:
            module.vm.entry_list = [action[1]] + module.vm.entry_list

        elif action[0] == Action.remove_entry:
            module.vm.entry_list.remove(action[1])

        elif action[0] == Action.replace_entry_list:
            if len(action) > 1:
                module.vm.entry_list = action[1]
            else:
                module.vm.entry_list = []

        elif action[0] == Action.add_command:
            module.vm.command_list = module.vm.command_list + [action[1]]

        elif action[0] == Action.prepend_command:
            module.vm.command_list = [action[1]] + module.vm.command_list

        elif action[0] == Action.remove_command:
            module.vm.command_list.remove(action[1])

        elif action[0] == Action.replace_command_list:
            if len(action) > 1:
                module.vm.command_list = action[1]
            else:
                module.vm.command_list = []

        elif action[0] == Action.set_header:
            if len(action) > 1:
                module.vm.set_header(str(action[1]))
            else:
                module.vm.set_header("")

        elif action[0] == Action.set_filter:
            if len(action) > 1:
                module.vm.search_string = str(action[1])
            else:
                module.vm.search_string = ""

            module.vm.search_string_changed(module.vm.search_string)

        elif action[0] in [Action.ask_question, Action.ask_question_default_yes, Action.ask_question_default_no]:
            self.window.ask_question(
                module.metadata['name'],
                action[1],
                action[2] if len(action) > 2 else None,
                module.vm.module.process_response)

        elif action[0] == Action.ask_choice:
            self.window.ask_choice(
                module.metadata['name'],
                action[1],
                action[2],
                action[3] if len(action) > 3 else None,
                module.vm.module.process_response)

        elif action[0] == Action.ask_input:
            self.window.ask_input(
                module.metadata['name'],
                action[1],
                action[2] if len(action) > 2 else "",
                False,
                False,
                action[3] if len(action) > 3 else None,
                module.vm.module.process_response)

        elif action[0] == Action.ask_input_password:
            self.window.ask_input(
                module.metadata['name'],
                action[1],
                action[2] if len(action) > 2 else "",
                True,
                False,
                action[3] if len(action) > 3 else None,
                module.vm.module.process_response)

        elif action[0] == Action.ask_input_multi_line:
            self.window.ask_input(
                module.metadata['name'],
                action[1],
                action[2] if len(action) > 2 else "",
                False,
                True,
                action[3] if len(action) > 3 else None,
                module.vm.module.process_response)

        elif action[0] == Action.copy_to_clipboard:
            # Copy the given data to the user-chosen clipboard
            self.window.output_queue.append(str(action[1]))
            if Settings.get('output_mode') == OutputMode.AutoType:
                Logger.log(module.metadata['name'], Translation.get("data_queued_for_typing"))
            else:
                Logger.log(module.metadata['name'], Translation.get("data_queued_for_clipboard"))

        elif action[0] == Action.set_selection:
            if len(action) > 1:
                module.vm.selection = [
                    entry if isinstance(entry, Selection) else Selection(entry)
                    for entry in action[1]
                ]
            else:
                module.vm.selection = []

            module.vm.selection_changed(module.vm.selection)

            if module.vm.selection_thread:
                module.vm.selection_thread.join()

            module.vm.make_selection()

        elif action[0] == Action.close:
            # Don't close and stay on the same depth if the user explicitly requested to not close after last input
            if not module.vm.minimize_disabled:
                module.vm.close_request(False, False)

                selection = []  # type: List[Selection]
            else:
                selection = module.vm.selection[:-1]

            module.vm.minimize_disabled = False

            module.vm.queue.put([Action.set_selection, selection])

        elif action[0] == Action.set_entry_info:
            if len(action) > 2:
                module.vm.extra_info_entries[str(action[1])] = str(action[2])
            else:
                try:
                    del module.vm.extra_info_entries[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_entry_info_dict:
            if len(action) > 1:
                module.vm.extra_info_entries = action[1]
            else:
                module.vm.extra_info_entries = {}

        elif action[0] == Action.set_command_info:
            if len(action) > 2:
                module.vm.extra_info_commands[str(action[1])] = str(action[2])
            else:
                try:
                    del module.vm.extra_info_commands[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_command_info_dict:
            if len(action) > 1:
                module.vm.extra_info_commands = action[1]
            else:
                module.vm.extra_info_commands = {}

        elif action[0] == Action.set_base_info:
            if len(action) > 1:
                module.vm.update_base_info_panel(action[1])
            else:
                module.vm.update_base_info_panel("")

        elif action[0] == Action.set_entry_context:
            if len(action) > 2:
                module.vm.context_menu_entries[str(action[1])] = action[2]
            else:
                try:
                    del module.vm.context_menu_entries[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_entry_context_dict:
            if len(action) > 1:
                module.vm.context_menu_entries = action[1]
            else:
                module.vm.context_menu_entries = {}

        elif action[0] == Action.set_command_context:
            if len(action) > 2:
                module.vm.context_menu_commands[str(action[1])] = action[2]
            else:
                try:
                    del module.vm.context_menu_commands[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_command_context_dict:
            if len(action) > 1:
                module.vm.context_menu_commands = action[1]
            else:
                module.vm.context_menu_commands = {}

        elif action[0] == Action.set_base_context:
            if len(action) > 1:
                module.vm.context_menu_base = action[1]
            else:
                module.vm.context_menu_base = []

        else:
            print('WARN: Module requested unknown action {}'.format(action[0]))

        if focused_module and module.entries_processed >= 100:
            module.vm.search(new_entries=True)
            module.entries_processed = 0

        module.vm.queue.task_done()

    def run(self) -> None:
        """Process actions modules put in the queue and keep the window working."""
        while True:
            try:
                # Ever going above 30FPS is just a waste of CPU
                main_loop_request = self.main_loop_queue.get(True, (1 / 30))
                main_loop_request()
            except Empty:
                pass

            # Process a call if there is any to process
            InternalCallProcessor.process()

            self.app.sendPostedEvents()
            self.app.processEvents()  # type: ignore
            Logger.show_next_message()

            for index, module in enumerate(Core.get_modules()):
                if not module.init:
                    continue

                module.vm.unprocessed_count_changed(module.vm.queue.qsize())

                if index == Core.get_focused_module_id():
                    focused_module = True
                else:
                    focused_module = False

                try:
                    self._process_module_action(index, module, focused_module)
                    module.entries_processed += 1
                except Empty:
                    if focused_module and module.entries_processed:
                        module.vm.search(new_entries=True)

                    module.entries_processed = 0
                except Exception as e:
                    print('WARN: Module {} caused exception {}'.format(module.metadata['name'], e))
                    traceback.print_exc()


class ModuleManager():
    """Install, remove, update and list modules."""

    def __init__(self) -> None:
        """Initialize the module manager."""
        self.module_dir = os.path.join(ConfigRetriever.get_path(),
                                       'modules')
        self.module_dependencies_dir = os.path.join(ConfigRetriever.get_path(),
                                                    'module_dependencies')

    def _pip_install(self, identifier: str) -> Optional[str]:
        """Install module dependencies using pip."""
        module_requirements_path = os.path.join(self.module_dir, identifier.replace('.', '_'), 'requirements.txt')
        module_dependencies_path = os.path.join(self.module_dependencies_dir, identifier.replace('.', '_'))

        if not os.path.isfile(module_requirements_path):
            return None

        try:
            os.mkdir(module_dependencies_path)
        except OSError:
            # Probably already exists, that's okay
            pass

        # Create the pip command
        pip_command = [sys.executable,
                       '-m',
                       'pip',
                       'install',
                       '--isolated']

        # TODO: Remove after Debian 9 is no longer supported
        # This works around Debian 9's faultily-patched pip
        # We try to prevent false positives by checking for (mini)conda or a venv
        # This is tracked upstream at https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=830892
        # It has been fixed in Debian Buster (10)
        if ("conda" not in sys.version and os.path.isfile('/etc/issue.net') and
                re.match(r"Debian GNU/Linux \d$", open('/etc/issue.net', 'r').read()) and
                not hasattr(sys, 'real_prefix') and
                not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
            pip_command += ['--system']

        pip_command += ['--upgrade',
                        '--target',
                        module_dependencies_path,
                        '-r',
                        module_requirements_path]

        # Actually run the pip command
        try:
            check_output(pip_command, universal_newlines=True)
        except CalledProcessError as e:
            return e.output

        return None

    def load(self, module: Dict[str, Any], index=None, window=None) -> bool:
        """Load a module and attach it to the main window."""
        # Append modulePath if not yet appendend
        module_path = os.path.join(ConfigRetriever.get_path(), 'modules')
        if module_path not in sys.path:
            sys.path.append(module_path)

        # Append module dependencies path if not yet appended
        module_dependencies_path = os.path.join(ConfigRetriever.get_path(),
                                                'module_dependencies',
                                                module['metadata']['id'].replace('.', '_'))
        if module_dependencies_path not in sys.path:
            sys.path.append(module_dependencies_path)

        # Set default for internal settings not loaded from file
        if '__pext_sort_mode' not in module['settings']:
            module['settings']['__pext_sort_mode'] = 'Module'

        view_settings = {}
        module_settings = {}
        for setting in module['settings']:
            value = module['settings'][setting]
            if setting.startswith("__pext_"):
                # Export settings relevant for ViewModel to ViewModel variable
                if setting == '__pext_sort_mode':
                    try:
                        value = SortMode[value]
                    except KeyError:
                        pass

                view_settings[setting] = value
            else:
                # Don't export internal Pext settings to module itself
                module_settings[setting] = value

        module['settings'] = module_settings

        # Prepare ViewModel
        vm = ViewModel(view_settings)

        # Prepare module
        try:
            module_import = __import__(module['metadata']['id'].replace('.', '_'), fromlist=['Module'])
        except (ImportError, NameError) as e1:
            Logger.log_critical(
                module['metadata']['name'],
                str(e1),
                traceback.format_exc(),
                module['metadata']
            )

            # Remove module dependencies path
            sys.path.remove(module_dependencies_path)

            return False

        try:
            Module = getattr(module_import, 'Module')
        except AttributeError as e2:
            Logger.log_critical(
                module['metadata']['name'],
                str(e2),
                traceback.format_exc(),
                module['metadata']
            )

            # Remove module dependencies path
            sys.path.remove(module_dependencies_path)

            return False

        # Ensure the module implements the base
        if not issubclass(Module, ModuleBase):
            Logger.log_critical(
                module['metadata']['name'],
                Translation.get("module_class_does_not_implement_modulebase"),
                None,
                module['metadata']
            )

            # Remove module dependencies path
            sys.path.remove(module_dependencies_path)

            return False

        # Set up a queue so that the module can communicate with the main
        # thread
        q = Queue()  # type: Queue

        # Load module
        try:
            module_code = Module()
        except TypeError as e3:
            Logger.log_critical(
                module['metadata']['name'],
                str(e3),
                traceback.format_exc(),
                module['metadata']
            )

            # Remove module dependencies path
            sys.path.remove(module_dependencies_path)

            return False

        # Check if the required functions have enough parameters
        required_param_lengths = {}

        for name, value in getmembers(ModuleBase, isfunction):
            required_param_lengths[name] = len(signature(value).parameters) - 1  # Python is inconsistent with self

        for name, value in getmembers(module_code, ismethod):
            try:
                required_param_length = required_param_lengths[name]
            except KeyError:
                continue

            param_length = len(signature(value).parameters)

            if param_length != required_param_length:
                if name == 'process_response' and param_length == 1:
                    print("WARN: Module {} uses old process_response signature and will not be able to receive an "
                          "identifier if requested".format(module['metadata']['name']))
                else:
                    Logger.log_error(
                        None,
                        Translation.get("module_failed_load_wrong_param_count")
                        .format(module['metadata']['name'], name, param_length, required_param_length))

                    return False

        # Prefill API version and locale
        locale = LocaleManager.find_best_locale(Settings.get('locale')).name()

        module['settings']['_api_version'] = [0, 13, 0]
        module['settings']['_locale'] = locale
        module['settings']['_portable'] = Settings.get('_portable')

        # Start the module in the background
        module_thread = ModuleThreadInitializer(
            module['metadata']['name'],
            q,
            target=module_code.init,
            args=(module['settings'], q))
        module_thread.start()

        # Turn this into an UiModule
        vm.bind_queue(q)
        vm.bind_module(module_code)
        ui_module = UiModule(vm, module_code, module_import, module['metadata'], module['settings'])
        Core.add_module(ui_module, index)

        # Ask Window to attach
        if window:
            return window.add_module(ui_module, index)

        return True

    def stop(self, index: int) -> None:
        """Call a module's stop function by index."""
        module = Core.get_module(index)
        try:
            module.vm.stop()
        except Exception as e:
            print('WARN: Module {} caused exception {} on unload'
                  .format(module.metadata['name'], e))
            traceback.print_exc()

    def unload(self, index: int, for_reload=False, window=None) -> None:
        """Unload a module by tab index."""
        Core.remove_module(index)
        if window:
            window.remove_module(index, for_reload)

    def get_info(self, module_id: str) -> Optional[Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return the metadata and source of one single module."""
        return ObjectManager().list_object(os.path.join(self.module_dir, module_id.replace('.', '_')))

    def list(self) -> Dict[str, Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return a list of modules together with their source."""
        return ObjectManager().list_objects(self.module_dir)

    def reload_step_unload(self, index: int, window=None) -> Dict[str, str]:
        """Reload a module by index: Unload step."""
        # Get the needed info to load the module
        module_data = Core.get_module(index)
        module = {
            'metadata': module_data.metadata,
            'settings': module_data.settings,
            'module_import': module_data.module_import
        }

        # Stop the module
        self.stop(index)

        # Disable with reason: update
        if window:
            window.disable_module(index, 2)

        return module

    def reload_step_load(self, index: int, module_data: Dict[str, Any], window=None) -> bool:
        """Reload a module by index: Load step."""
        # Unload the module
        self.unload(index, True, window)

        # Force a reload to make code changes happen
        reload(module_data['module_import'])

        # Load it into the UI
        module = {
            'metadata': module_data['metadata'],
            'settings': module_data['settings']
        }

        if not self.load(module, index, window):
            return False

        return True

    def install(self, url: str, identifier: str, name: str, branch: bytes, verbose=False, interactive=True) -> bool:
        """Install a module."""
        module_path = os.path.join(self.module_dir, identifier.replace('.', '_'))
        dep_path = os.path.join(self.module_dependencies_dir, identifier.replace('.', '_'))

        if os.path.exists(module_path):
            if verbose:
                Logger.log(None, Translation.get("already_installed").format(name))

            return False

        if verbose:
            Logger.log(None, Translation.get("downloading_from_url").format(name, url))

        try:
            porcelain.clone(
                UpdateManager.fix_git_url_for_dulwich(url), target=module_path, checkout=branch
            )
        except Exception as e:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_download").format(name, e),
                    traceback.format_exc())

            try:
                rmtree(module_path)
            except FileNotFoundError:
                pass

            return False

        if verbose:
            Logger.log(None, Translation.get("downloading_dependencies").format(name))

        pip_error_output = self._pip_install(identifier)
        if pip_error_output is not None:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_download_dependencies").format(name),
                    pip_error_output)

            try:
                rmtree(module_path)
            except FileNotFoundError:
                pass

            try:
                rmtree(dep_path)
            except FileNotFoundError:
                pass

            return False

        if verbose:
            Logger.log(None, Translation.get("installed").format(name))

        return True

    def uninstall(self, identifier: str, verbose=False) -> bool:
        """Uninstall a module."""
        module_path = os.path.join(self.module_dir, identifier.replace('.', '_'))
        dep_path = os.path.join(self.module_dependencies_dir, identifier.replace('.', '_'))

        try:
            with open(os.path.join(module_path, "metadata.json"), 'r') as metadata_json:
                name = json.load(metadata_json)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(module_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            pass

        if verbose:
            Logger.log(None, Translation.get("uninstalling").format(name), show_in_module=identifier)

        try:
            rmtree(module_path)
        except FileNotFoundError:
            if verbose:
                Logger.log(None, Translation.get("already_uninstalled").format(name), show_in_module=identifier)

            return False

        try:
            rmtree(dep_path)
        except FileNotFoundError:
            pass

        if verbose:
            Logger.log(None, Translation.get("uninstalled").format(name), show_in_module=identifier)

        return True

    def has_update(self, identifier: str) -> bool:
        """Check if a module has an update available."""
        module_path = os.path.join(self.module_dir, identifier.replace('.', '_'))
        return UpdateManager.has_update(module_path)

    def update(self, identifier: str, verbose=False) -> bool:
        """Update a module."""
        if not self.has_update(identifier):
            return True

        module_path = os.path.join(self.module_dir, identifier.replace('.', '_'))

        try:
            with open(os.path.join(module_path, "metadata.json"), 'r') as metadata_json:
                name = json.load(metadata_json)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(module_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            pass

        if verbose:
            Logger.log(None, Translation.get("updating").format(name), show_in_module=identifier)

        try:
            if not UpdateManager.update(module_path):
                if verbose:
                    Logger.log(None, Translation.get("already_up_to_date").format(name), show_in_module=identifier)

                return False

        except Exception as e:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_download_update").format(name, e),
                    traceback.format_exc(),
                    show_in_module=identifier)

            return False

        if verbose:
            Logger.log(None, Translation.get("updating_dependencies").format(name), show_in_module=identifier)

        pip_error_output = self._pip_install(identifier)
        if pip_error_output is not None:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_update_dependencies").format(name),
                    pip_error_output)

            return False

        if verbose:
            Logger.log(None, Translation.get("updated").format(name), show_in_module=identifier)

        return True

    def update_all(self, verbose=False) -> bool:
        """Update all modules."""
        success = True

        for identifier in self.list().keys():
            if not self.update(identifier, verbose=verbose):
                success = False

        return success


class ModuleThreadInitializer(threading.Thread):
    """Initialize a thread for the module."""

    def __init__(self, module_name: str, q: Queue, target=None, args=()) -> None:
        """Initialize the module thread initializer."""
        self.module_name = module_name
        self.queue = q
        threading.Thread.__init__(self, target=target, args=args)

    def run(self) -> None:
        """Start the module's thread.

        The thread will run forever, until an exception is thrown. If an
        exception is thrown, an Action.critical_error is appended to the
        queue.
        """
        try:
            threading.Thread.run(self)
        except Exception as e:
            self.queue.put([Action.critical_error, str(e), traceback.format_exc()])


class ThemeManager():
    """Manages the theme."""

    def __init__(self) -> None:
        """Initialize the module manager."""
        self.theme_dir = os.path.join(ConfigRetriever.get_path(), 'themes')

    def _get_palette_mappings(self) -> Dict[str, Dict[Any, Any]]:
        mapping = {'colour_roles': {}, 'colour_groups': {}}  # type: Dict[str, Dict[Any, Any]]
        for key in dir(QPalette):
            value = getattr(QPalette, key)
            if isinstance(value, QPalette.ColorRole):
                mapping['colour_roles'][key] = value
                mapping['colour_roles'][value] = key
            elif isinstance(value, QPalette.ColorGroup):
                mapping['colour_groups'][key] = value
                mapping['colour_groups'][value] = key

        return mapping

    def list(self) -> Dict[str, Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return a list of themes together with their source."""
        return ObjectManager().list_objects(self.theme_dir)

    def load(self, identifier: str) -> QPalette:
        """Return the parsed palette."""
        palette = QPalette()
        palette_mappings = self._get_palette_mappings()

        config = configparser.ConfigParser()
        config.optionxform = lambda option: option  # type: ignore  # No lowercase
        config.read(os.path.join(self.theme_dir, identifier.replace('.', '_'), 'theme.conf'))

        for colour_group in config.sections():
            for colour_role in config[colour_group]:
                colour_code_list = [int(x) for x in config[colour_group][colour_role].split(",")]

                try:
                    palette.setColor(palette_mappings['colour_groups'][colour_group],
                                     palette_mappings['colour_roles'][colour_role],
                                     QColor(*colour_code_list))
                except KeyError as e:
                    print("Theme contained an unknown key, {}, skipping".format(e))

        return palette

    def apply(self, palette: QPalette, app: QApplication) -> None:
        """Apply the palette to the app (use this before creating a window)."""
        app.setPalette(palette)

    def install(self, url: str, identifier: str, name: str, branch: bytes, verbose=False, interactive=True) -> bool:
        """Install a theme."""
        theme_path = os.path.join(self.theme_dir, identifier.replace('.', '_'))

        if os.path.exists(theme_path):
            if verbose:
                Logger.log(None, Translation.get("already_installed").format(name))

            return False

        if verbose:
            Logger.log(None, Translation.get("downloading_from_url").format(name, url))

        try:
            porcelain.clone(UpdateManager.fix_git_url_for_dulwich(url), target=theme_path, checkout=branch)
        except Exception as e:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_download").format(name, e),
                    traceback.format_exc())

            try:
                rmtree(os.path.join(self.theme_dir, identifier))
            except FileNotFoundError:
                pass

            return False

        if verbose:
            Logger.log(None, Translation.get("installed").format(name))

        return True

    def uninstall(self, identifier: str, verbose=False) -> bool:
        """Uninstall a theme."""
        theme_path = os.path.join(self.theme_dir, identifier.replace('.', '_'))

        try:
            with open(os.path.join(theme_path, "metadata.json"), 'r') as metadata_json:
                name = json.load(metadata_json)['name']
        except (FileNotFoundError, IndexError, KeyError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(theme_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, KeyError, json.decoder.JSONDecodeError):
            pass

        if verbose:
            Logger.log(None, Translation.get("uninstalling").format(name))

        try:
            rmtree(theme_path)
        except FileNotFoundError:
            if verbose:
                Logger.log(None, Translation.get("already_uninstalled").format(name))

            return False

        if verbose:
            Logger.log(None, Translation.get("uninstalled").format(name))

        return True

    def has_update(self, identifier: str) -> bool:
        """Check if a theme has an update available."""
        theme_path = os.path.join(self.theme_dir, identifier.replace('.', '_'))
        return UpdateManager.has_update(theme_path)

    def update(self, identifier: str, verbose=False) -> bool:
        """Update a theme."""
        if not self.has_update(identifier):
            return True

        theme_path = os.path.join(self.theme_dir, identifier.replace('.', '_'))

        try:
            with open(os.path.join(theme_path, "metadata.json"), 'r') as metadata_json:
                name = json.load(metadata_json)['name']
        except (FileNotFoundError, IndexError, KeyError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(theme_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, KeyError, json.decoder.JSONDecodeError):
            pass

        if verbose:
            Logger.log(None, Translation.get("updating").format(name))

        try:
            if not UpdateManager.update(theme_path):
                if verbose:
                    Logger.log(None, Translation.get("already_up_to_date").format(name))

                return False

        except Exception as e:
            if verbose:
                Logger.log_critical(
                    None,
                    Translation.get("failed_to_download_update").format(name, e),
                    traceback.format_exc())

            return False

        if verbose:
            Logger.log(None, Translation.get("updated").format(name))

        return True

    def update_all(self, verbose=False) -> bool:
        """Update all themes."""
        success = True

        for identifier in self.list().keys():
            if not self.update(identifier, verbose=verbose):
                success = False

        return success


class ModuleOptionParser(argparse.Action):
    """Parse module options from the command line."""

    def __call__(self, parser, namespace, value, option_string=None):
        """Save the module and appropriate module options in the correct order."""
        if '_modules' not in namespace:
            setattr(namespace, '_modules', [])

        modules = namespace._modules

        if self.dest == 'module':
            module_dir = os.path.join(ConfigRetriever.get_path(), 'modules')
            data = ObjectManager.list_object(os.path.join(module_dir, value.replace('.', '_')))
            if not data:
                print("Could not find module {}".format(value))
                return

            modules.append({'metadata': data['metadata'], 'settings': {}})
            setattr(namespace, '_modules', modules)
        else:
            modules[-1]['settings'][self.dest[len('module-'):]] = value
            setattr(namespace, '_modules', modules)


def _init_persist(profile: str, background: bool) -> None:
    """Open Pext if an instance is already running.

    Checks if Pext is already running and if so, send it SIGUSR1 to bring it
    to the foreground. If Pext is not already running, saves a PIDfile so that
    another Pext instance can find us.
    """
    lock = ProfileManager.get_lock_instance(profile)
    if lock:
        # Notify the main process if we are not using --background
        if not background:
            if platform.system() == 'Windows':
                print("Pext is already running and foregrounding the running instance is currently not supported "
                      "on Windows. Doing nothing...")
            else:
                os.kill(lock, signal.SIGUSR1)
        else:
            print("Pext is already running, but --background was given. Doing nothing...")

        sys.exit(0)

    ProfileManager.lock_profile(profile)


def _parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='The Python-based extendable tool.')
    parser.add_argument('-v', '--version', action='version',
                        version='Pext {}'.format(UpdateManager().get_core_version()))
    parser.add_argument('--data-path', help='use given directory to store settings and data.')
    parser.add_argument('--locale', help='load the given locale.')
    parser.add_argument('--list-locales', action='store_true',
                        help='print a list of the available locales.')
    parser.add_argument('--list-styles', action='store_true',
                        help='print a list of loadable Qt system styles and exit.')
    parser.add_argument('--style', help='use the given Qt system style for the UI.')
    parser.add_argument('--background', action='store_true', help='do not open the user interface this invocation.')
    parser.add_argument('--output', choices=['default-clipboard', 'x11-selection-clipboard', 'macos-findbuffer'],
                        help='choose the location to output entries to.')
    parser.add_argument('--module', '-m', action=ModuleOptionParser,
                        help='name the module to use. This option may be given multiple times. '
                        'When this option is given, the profile module list will be overwritten.')
    parser.add_argument('--install-module', action='append',
                        help='download and install a module from the given metadata.json URL.')
    parser.add_argument('--uninstall-module', action='append', help='uninstall a module by identifier.')
    parser.add_argument('--update-module', action='append', help='update a module by identifier.')
    parser.add_argument('--update-modules', action='store_true', help='update all modules.')
    parser.add_argument('--list-modules', action='store_true', help='list all installed modules.')
    parser.add_argument('--theme', help='use the chosen theme.')
    parser.add_argument('--install-theme', action='append',
                        help='download and install a theme from the given metadata.json URL.')
    parser.add_argument('--uninstall-theme', action='append', help='uninstall a theme by identifier.')
    parser.add_argument('--update-theme', action='append', help='update a theme by identifier.')
    parser.add_argument('--update-themes', action='store_true', help='update all themes.')
    parser.add_argument('--list-themes', action='store_true', help='list all installed themes.')
    parser.add_argument('--profile', '-p',
                        help='use the chosen profile, creating it if it doesn\'t exist yet. '
                        'Defaults to "default", use "none" to not save the application state between runs.')
    parser.add_argument('--create-profile', action='append', help='create a new profile with the given name.')
    parser.add_argument('--remove-profile', action='append', help='remove the chosen profile.')
    parser.add_argument('--rename-profile', nargs=2, action='append', help='rename the chosen profile.')
    parser.add_argument('--list-profiles', action='store_true', help='list all profiles.')
    parser.add_argument('--tray', action='store_true', dest='tray', default=None,
                        help='create a tray icon (this is the default).')
    parser.add_argument('--no-tray', action='store_false', dest='tray', default=None,
                        help='do not create a tray icon.')
    parser.add_argument('--portable', action='store_true', dest='portable', default=None,
                        help='load and store everything in a local directory.')
    parser.add_argument('--no-portable', action='store_false', dest='portable', default=None,
                        help='load and store everything in the user directory.')
    parser.add_argument('--turbo', action='store_true', dest='turbo_mode', default=None,
                        help='automatically select entries when expecting the user to want to (possibly dangerous).')
    parser.add_argument('--no-turbo', action='store_false', dest='turbo_mode', default=None,
                        help='do not automatically select entries (safer).')
    # TODO: Remove in favor of a proper per-module selection
    parser.add_argument('--force-module-branch-type',
                        help='Set to beta if you want to test beta versions of all modules. Please report breakage.')

    # Remove weird macOS-added parameter
    # https://stackoverflow.com/questions/10242115/os-x-strange-psn-command-line-parameter-when-launched-from-finder
    if platform.system() == "Darwin":
        proper_argv = []
        for arg in argv:
            if not arg.startswith("-psn_0_"):
                proper_argv.append(arg)

        argv = proper_argv

    # Ensure module options get parsed
    for arg in argv:
        arg = arg.split("=")[0]
        if arg.startswith("--module-"):
            try:
                parser.add_argument(arg, action=ModuleOptionParser)
            except argparse.ArgumentError:
                # Probably already added
                pass

    args = parser.parse_args(argv)
    return args


def _load_settings(args: argparse.Namespace) -> None:
    """Load the settings from the command line and set defaults."""
    # First, check for profile
    if args.profile:
        Settings.set('profile', args.profile)

    # Create directory for profile if not existant
    try:
        ProfileManager().create_profile(str(Settings.get('profile')))
    except OSError:
        pass

    # Load all settings
    Settings.update_global(ProfileManager().retrieve_settings(None))
    Settings.update(ProfileManager().retrieve_settings(str(Settings.get('profile'))))

    # Then, check for the rest
    if args.locale:
        Settings.set('locale', args.locale)

    # TODO: Remove in favor of a proper per-module selection
    if args.force_module_branch_type is not None:
        Settings.set('_force_module_branch_type', args.force_module_branch_type)

    if args.list_locales:
        locales = LocaleManager.get_locales()
        for locale in locales:
            print("{} ({})".format(locale, locales[locale]))

        Settings.set('_launch_app', False)

    if args.list_styles:
        for style in QStyleFactory().keys():
            print(style)

        Settings.set('_launch_app', False)

    if args.style:
        if args.style in QStyleFactory().keys():
            Settings.set('style', args.style)
        else:
            # PyQt5 does not have bindings for QQuickStyle yet
            os.environ["QT_QUICK_CONTROLS_STYLE"] = args.style

    if args.background:
        Settings.set('background', True)

    if args.output:
        if args.output == 'default-clipboard':
            Settings.set('output_mode', OutputMode.DefaultClipboard)
        elif args.output == 'x11-selection-clipboard':
            Settings.set('output_mode', OutputMode.SelectionClipboard)
        elif args.output == 'macos-findbuffer':
            Settings.set('output_mode', OutputMode.FindBuffer)
        elif args.output == 'autotype':
            Settings.set('output_mode', OutputMode.AutoType)

    if args.install_module:
        for metadata_url in args.install_module:
            try:
                metadata = requests.get(metadata_url).json()

                try:
                    translated_metadata_url = re.sub(r'\.json$', '_{}.json'.format(
                        LocaleManager.find_best_locale(Settings.get('locale')).name()), metadata_url)
                    r = requests.get(translated_metadata_url)
                    metadata.update(r.json())
                except json.decoder.JSONDecodeError:
                    print("Could not parse localized metadata file {}, ignoring...".format(translated_metadata_url))

                if not ModuleManager().install(metadata['git_urls'][0],
                                               metadata['id'],
                                               metadata['name'],
                                               UpdateManager.get_wanted_branch_from_metadata(metadata, metadata['id']),
                                               verbose=True):
                    sys.exit(3)
            except Exception as e:
                print("Failed installing module from {}: {}".format(metadata_url, e))
                traceback.print_exc()

        Settings.set('_launch_app', False)

    if args.uninstall_module:
        for identifier in args.uninstall_module:
            if not ModuleManager().uninstall(identifier, verbose=True):
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.update_module:
        for identifier in args.update_module:
            if not ModuleManager().update(identifier, verbose=True):
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.update_modules:
        if not ModuleManager().update_all(verbose=True):
            sys.exit(3)

        Settings.set('_launch_app', False)

    if args.list_modules:
        for module_identifier, module_data in ModuleManager().list().items():
            print('{} ({})'.format(module_identifier, module_data['source']))

        Settings.set('_launch_app', False)

    if args.theme:
        Settings.set('theme', args.themes)

    if args.install_theme:
        for metadata_url in args.install_theme:
            try:
                metadata = requests.get(metadata_url).json()

                try:
                    translated_metadata_url = re.sub(r'\.json$', '_{}.json'.format(
                        LocaleManager.find_best_locale(Settings.get('locale')).name()), metadata_url)
                    r = requests.get(translated_metadata_url)
                    metadata.update(r.json())
                except json.decoder.JSONDecodeError:
                    print("Could not parse localized metadata file {}, ignoring...".format(translated_metadata_url))

                if not ThemeManager().install(metadata['git_urls'][0],
                                              metadata['id'],
                                              metadata['name'],
                                              UpdateManager.get_wanted_branch_from_metadata(metadata, metadata['id']),
                                              verbose=True):
                    sys.exit(3)
            except Exception as e:
                print("Failed installing theme from {}: {}".format(metadata_url, e))
                traceback.print_exc()

        Settings.set('_launch_app', False)

    if args.uninstall_theme:
        for identifier in args.uninstall_theme:
            if not ThemeManager().uninstall(identifier, verbose=True):
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.update_theme:
        for identifier in args.update_theme:
            if not ThemeManager().update(identifier, verbose=True):
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.update_themes:
        if not ThemeManager().update_all(verbose=True):
            sys.exit(3)

        Settings.set('_launch_app', False)

    if args.list_themes:
        for theme_name, theme_data in ThemeManager().list().items():
            print('{} ({})'.format(theme_name, theme_data['source']))

        Settings.set('_launch_app', False)

    if args.create_profile:
        for profile in args.create_profile:
            if not ProfileManager().create_profile(profile):
                print('Could not create profile {}, it already exists.'.format(profile))
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.remove_profile:
        for profile in args.remove_profile:
            if not ProfileManager().remove_profile(profile):
                print('Could not delete profile {}, it is in use.'.format(profile))
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.rename_profile:
        for old_name, new_name in args.rename_profile:
            if not ProfileManager().rename_profile(old_name, new_name):
                print('Could not rename profile {} to {}.'.format(old_name, new_name))
                sys.exit(3)

        Settings.set('_launch_app', False)

    if args.list_profiles:
        for profile in ProfileManager().list_profiles():
            print(profile)

        Settings.set('_launch_app', False)

    if args.tray is not None:
        Settings.set('tray', args.tray)

    if args.portable:
        Settings.set('_portable', args.portable)

    if args.turbo_mode is not None:
        Settings.set('turbo_mode', args.turbo_mode)

    # Set up the parsed modules
    if '_modules' in args:
        Settings.set('modules', args._modules)


def main(ui_type: UIType) -> None:
    """Start the application."""
    # Parse arguments
    args = _parse_args(sys.argv[1:])

    # Load configuration
    ConfigRetriever.set_data_path(args.data_path)
    ConfigRetriever.make_portable(args.portable)

    # Lock profile or call existing profile if running
    _init_persist(args.profile if args.profile else ProfileManager.default_profile_name(),
                  args.background if args.background else False)

    # Ensure our necessary directories exist
    for directory in ['modules',
                      'module_dependencies',
                      'themes',
                      'profiles',
                      os.path.join('profiles', ProfileManager.default_profile_name())]:
        try:
            os.makedirs(os.path.join(ConfigRetriever.get_path(), directory))
        except OSError:
            # Probably already exists, that's okay
            pass

    _load_settings(args)
    del args

    if not Settings.get('_launch_app'):
        sys.exit(0)

    # Set up the app
    if Settings.get('profile') == ProfileManager.default_profile_name():
        appname = 'Pext'
    else:
        appname = 'Pext ({})'.format(Settings.get('profile'))

    app = QApplication([appname])

    # Load the locale
    locale_manager = LocaleManager()
    locale_manager.load_locale(app, LocaleManager.find_best_locale(Settings.get('locale')))

    # Load the app icon
    # KDE doesn't support svg in the system tray and macOS makes the png in
    # the dock yellow. Let's assume svg for macOS and PNG for Linux for now.
    if platform.system() == "Darwin":
        app_icon = QIcon(os.path.join(AppFile.get_path(), 'images', 'scalable', 'pext.svg'))
    else:
        app_icon = QIcon(os.path.join(AppFile.get_path(), 'images', '128x128', 'pext.png'))

    # Create managers
    module_manager = ModuleManager()
    theme_manager = ThemeManager()

    app.setWindowIcon(app_icon)

    if Settings.get('style') is not None:
        app.setStyle(QStyleFactory().create(Settings.get('style')))  # type: ignore

    # Qt5's default style for macOS seems to have sizing bugs for buttons, so
    # we force the Fusion theme instead
    if platform.system() == 'Darwin':
        app.setStyle(QStyleFactory().create('Fusion'))  # type: ignore

    theme_identifier = Settings.get('theme')
    if theme_identifier is not None:
        # Qt5's default style for Windows, windowsvista, does not support palettes properly
        # If the user doesn't explicitly chose a style, but wants theming, we force
        # it to use Fusion, which gets themed properly
        if platform.system() == 'Windows' and Settings.get('style') is None:
            app.setStyle(QStyleFactory().create('Fusion'))  # type: ignore

        theme = theme_manager.load(theme_identifier)
        theme_manager.apply(theme, app)

    # Prepare UI-specific
    if ui_type == UIType.Qt5:
        from pext.ui_qt5 import Window, Tray, HotkeyHandler, SignalHandler
    else:
        raise ValueError("Invalid UI type requested")

    # Get a window
    window = Window(app, locale_manager, module_manager, theme_manager)

    # Prepare InternalCallProcessor
    InternalCallProcessor.bind(window, module_manager, theme_manager)

    # Give the logger a reference to the window
    Logger.bind_window(window)

    if ui_type == UIType.Qt5:
        # Create a tray icon
        # This needs to be stored in a variable to prevent the Python garbage collector from removing the Qt tray
        tray = Tray(window, app_icon)  # noqa: F841

        # Give the window a reference to the tray
        window.bind_tray(tray)

    # Clean up on exit
    atexit.register(Core._shut_down)

    # Create a main loop
    main_loop_queue = Queue()  # type: Queue[Callable[[], None]]
    main_loop = MainLoop(app, main_loop_queue, module_manager, window)

    if ui_type == UIType.Qt5:
        # Handle SIGUSR1 UNIX signal
        signal_handler = SignalHandler(window)
        if not platform.system() == 'Windows':
            signal.signal(signal.SIGUSR1, signal_handler.handle)

        # Start handling the global hotkey
        HotkeyHandler(main_loop_queue, window)

    # Start watching for uninstalls
    event_handler = PextFileSystemEventHandler(window, os.path.join(ConfigRetriever.get_path(), 'modules'))
    observer = Observer()
    observer.schedule(event_handler, os.path.join(ConfigRetriever.get_path(), 'modules'), recursive=True)
    observer.start()

    # Start update check
    window._menu_check_updates(verbose=False, manual=False)

    # And run...
    main_loop.run()


def run_qt5() -> None:
    """Entrypoint for starting with Qt5 UI."""
    main(UIType.Qt5)


if __name__ == "__main__":
    main(UIType.Qt5)
