#!/usr/bin/env python3

# Copyright (c) 2015 - 2020 Sylvia van Os <sylvia@hackerchick.me>
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
import time
import traceback
import tempfile
import psutil

from datetime import datetime
from distutils.util import strtobool
from enum import IntEnum
from importlib import reload  # type: ignore
from inspect import getmembers, isfunction, ismethod, signature
from pkg_resources import parse_version
from shutil import rmtree
from subprocess import check_output, CalledProcessError
try:
    from typing import Any, Callable, Dict, List, Optional, Union
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional, Union  # type: ignore  # noqa: F401
from urllib.parse import quote_plus
from queue import Queue, Empty

import requests

from dulwich import client, porcelain
from dulwich.repo import Repo
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor

from PyQt5.QtWidgets import QApplication, QStyleFactory, QSystemTrayIcon
from PyQt5.Qt import QIcon, QLocale, QTranslator, QQmlProperty
from PyQt5.QtGui import QPalette, QColor

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

client.get_ssh_vendor = ParamikoSSHVendor
# Windows doesn't support getuid
if platform.system() == 'Windows':
    import getpass  # NOQA

if False:
    # To make MyPy understand Window exists...
    import Window


class AppFile():
    """Get access to application-specific files."""

    @staticmethod
    def get_path() -> str:
        """Return the absolute current path."""
        return os.path.dirname(os.path.abspath(__file__))


# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(os.path.join(AppFile.get_path(), 'helpers'))
sys.path.append(os.path.join(AppFile.get_path()))

from pext_base import ModuleBase  # noqa: E402
from pext_helpers import Action, SelectionType, Selection  # noqa: E402


class UIType(IntEnum):
    """A list of supported UI types."""

    Qt5 = 0


class MinimizeMode(IntEnum):
    """A list of possible ways Pext can react on minimization."""

    Normal = 0
    Tray = 1
    NormalManualOnly = 2
    TrayManualOnly = 3


class SortMode(IntEnum):
    """A list of possible ways Pext can sort module entries."""

    Module = 0
    Ascending = 1
    Descending = 2


class OutputMode(IntEnum):
    """A list of possible locations to output to."""

    DefaultClipboard = 0
    SelectionClipboard = 1
    FindBuffer = 2
    AutoType = 3


class OutputSeparator(IntEnum):
    """A list of possible separators to put between entries in the output queue."""

    None_ = 0
    Tab = 1
    Enter = 2


class UiModule():
    """The module and all the relevant data to make UI display possible."""

    def __init__(self, vm: 'ViewModel', module_code, module_import, metadata, settings) -> None:
        """Put together the module and relevant classes and data."""
        self.init = False
        self.vm = vm
        self.module_code = module_code
        self.module_import = module_import
        self.metadata = metadata
        self.settings = settings

        self.entries_processed = 0


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

        args = sys.argv[:]
        if extra_args:
            args.extend(extra_args)

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

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


class ConfigRetriever():
    """Retrieve global configuration entries."""

    __config_data_path = None
    __config_temp_path = None

    @staticmethod
    def set_data_path(path: Optional[str]) -> None:
        """Set the root configuration directory for Pext to store in and load from."""
        ConfigRetriever.__config_data_path = path

    @staticmethod
    def make_portable(portable: Optional[bool]) -> None:
        """Make changes to locations so that Pext can be considered portable."""
        if not portable:
            return

        if not ConfigRetriever.__config_data_path:
            if 'APPIMAGE' in os.environ:
                base_path = os.path.dirname(os.path.abspath(os.environ['APPIMAGE']))
            else:
                base_path = AppFile.get_path()
            ConfigRetriever.__config_data_path = os.path.join(base_path, 'pext_data')

        ConfigRetriever.__config_temp_path = os.path.join(ConfigRetriever.__config_data_path, 'pext_temp')

    @staticmethod
    def get_path() -> str:
        """Get the config path."""
        if ConfigRetriever.__config_data_path:
            config_data_path = os.path.expanduser(ConfigRetriever.__config_data_path)
            os.makedirs(config_data_path, exist_ok=True)
            return config_data_path

        # Fall back to default config location
        try:
            config_data_path = os.environ['XDG_CONFIG_HOME']
        except Exception:
            config_data_path = os.path.join(os.path.expanduser('~'), '.config')

        os.makedirs(config_data_path, exist_ok=True)
        return os.path.join(config_data_path, 'pext')

    @staticmethod
    def get_temp_path() -> str:
        """Get the temp path."""
        if ConfigRetriever.__config_temp_path:
            temp_path = os.path.expanduser(ConfigRetriever.__config_temp_path)
        else:
            temp_path = tempfile.gettempdir()

        os.makedirs(temp_path, exist_ok=True)
        return temp_path


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
    def bind(window: 'Window', module_manager: 'ModuleManager', theme_manager: 'ThemeManager') -> None:  # noqa: F821
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


class Logger():
    """Log events to the appropriate location.

    Shows events in the main window and, if the main window is not visible,
    as a desktop notification.
    """

    queued_messages = []  # type: List[Dict[str, str]]
    last_update = None  # type: Optional[float]

    window = None

    @staticmethod
    def bind_window(window: 'Window') -> None:  # noqa: F821
        """Give the logger the ability to log info to the main window."""
        Logger.window = window

    @staticmethod
    def _queue_message(module_name: str, message: str, type_name: str) -> None:
        """Queue a message for display."""
        for formatted_message in Logger._format_message(module_name, message):
            Logger.queued_messages.append(
                {'message': formatted_message, 'type': type_name})

    @staticmethod
    def _format_message(module_name: str, message: str) -> List[str]:
        """Format message for display, including splitting multiline messages."""
        message_lines = []
        for line in message.splitlines():
            if not (not line or line.isspace()):
                if module_name:
                    message = '{}: {}'.format(module_name, line)
                else:
                    message = line

                message_lines.append(message)

        return message_lines

    @staticmethod
    def _show_in_module(identifier: Optional[str], message: str) -> None:
        """Show in the module disabled screen."""
        if identifier and Logger.window:
            for tab_id, tab in enumerate(Logger.window.tab_bindings):  # type: ignore
                if tab.uiModule.metadata['id'] == identifier:
                    Logger.window.update_state(tab_id, message)

    @staticmethod
    def log(module_name: Optional[str], message: str, show_in_module=None) -> None:
        """If a logger is provided, log to the logger. Otherwise, print."""
        if Logger.window:
            if not module_name:
                module_name = ""

            Logger._queue_message(module_name, message, 'message')
            Logger._show_in_module(show_in_module, message)
        else:
            print(message)

    @staticmethod
    def log_error(module_name: Optional[str], message: str, show_in_module=None) -> None:
        """If a logger is provided, log to the logger. Otherwise, print."""
        if Logger.window:
            if not module_name:
                module_name = ""

            Logger._queue_message(module_name, message, 'error')
            Logger._show_in_module(show_in_module, message)
        else:
            print(message)

    @staticmethod
    def log_critical(module_name: Optional[str], message: str, detailed_message: Optional[str], metadata=None,
                     show_in_module=None) -> None:
        """If a window is provided, pop up a window. Otherwise, print."""
        if not module_name:
            module_name = ""
        if not detailed_message:
            detailed_message = ""

        if metadata and 'bugtracker' in metadata and 'bugtracker_type' in metadata:
            if metadata['bugtracker_type'] == "github":
                bugtracker_url = "".join([
                    metadata['bugtracker'],
                    "/issues/new?title=",
                    quote_plus(message),
                    "&body=Module%20version%20",
                    quote_plus(metadata['version']),
                    "%0APext%20",
                    quote_plus(UpdateManager().get_core_version()),
                    "%20on%20",
                    quote_plus(sys.platform),
                    "%0A%0A",
                    "```%0A",
                    quote_plus(detailed_message),
                    "```"
                ])
            else:
                bugtracker_url = metadata['bugtracker']
        else:
            bugtracker_url = ""

        if Logger.window and module_name:
            Logger.window.add_actionable(
                "module_error_{}".format(module_name),
                Translation.get("actionable_error_in_module").format(module_name, message),
                Translation.get("actionable_report_error_in_module") if bugtracker_url else "",
                bugtracker_url)
            Logger._show_in_module(show_in_module, detailed_message)

        print("{}\n{}\n{}".format(module_name if module_name else "Pext", message, detailed_message))

    @staticmethod
    def show_next_message() -> None:
        """Show next statusbar message.

        Display the next message. If no more messages are available, clear the
        status bar after it has been displayed for 5 seconds.
        """
        if not Logger.window:
            return

        current_time = time.time()

        if len(Logger.queued_messages) == 0:
            if not Logger.last_update or current_time - 5 > Logger.last_update:
                Logger.window.set_status_text("")
                Logger.last_update = None
        else:
            message = Logger.queued_messages.pop(0)

            if message['type'] == 'error':
                statusbar_message = "<font color='red'>⚠ {}</color>".format(message['message'])
                icon = QSystemTrayIcon.Warning
            else:
                statusbar_message = message['message']
                icon = QSystemTrayIcon.Information

            Logger.window.set_status_text(statusbar_message)

            if Logger.window.tray:
                Logger.window.tray.tray.showMessage('Pext', message['message'], icon)

            Logger.last_update = current_time


class PextFileSystemEventHandler(FileSystemEventHandler):
    """Watches the file system to ensure state changes when relevant."""

    def __init__(self, window: 'Window', modules_path: str):  # noqa: F821
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


class Translation():
    """Retrieves translations for Python code.

    This works by reading values from QML.
    """

    __window = None

    @staticmethod
    def bind_window(window: 'Window') -> None:  # noqa: F821
        """Give the translator access to the translations stored in the window."""
        Translation.__window = window

    @staticmethod
    def get(string_id: str) -> str:
        """Return the translated value."""
        if Translation.__window:
            translation = QQmlProperty.read(Translation.__window.window, 'tr_{}'.format(string_id))
            if translation:
                return translation

            return "TRANSLATION MISSING: {}".format(string_id)

        return "TRANSLATION SYSTEM NOT YET AVAILABLE: {}".format(string_id)


class MainLoop():
    """Main application loop.

    The main application loop connects the application, queue and UI events and
    ensures these events get managed without locking up the UI.
    """

    def __init__(self, app: QApplication, main_loop_queue: Queue, module_manager: 'ModuleManager',
                 window: 'Window') -> None:  # noqa: F821
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


class LocaleManager():
    """Load and switch locales."""

    def __init__(self) -> None:
        """Initialize the locale manager."""
        self.locale_dir = os.path.join(AppFile.get_path(), 'i18n')
        self.current_locale = None
        self.translator = QTranslator()  # prevent Python from garbage collecting it after load_locale function

    @staticmethod
    def get_locales() -> Dict[str, str]:
        """Return the list of supported locales.

        It is return as a dictionary formatted as follows: {nativeLanguageName: languageCode}.
        """
        locales = {}

        try:
            for locale_file in os.listdir(os.path.join(AppFile.get_path(), 'i18n')):
                if not locale_file.endswith('.qm'):
                    continue

                locale_code = os.path.splitext(locale_file)[0][len('pext_'):]
                locale_name = QLocale(locale_code).nativeLanguageName()
                locales[locale_name] = locale_code
        except FileNotFoundError:
            print("No translations found")

        return locales

    def get_current_locale(self, system_if_unset=True) -> Optional[QLocale]:
        """Get the current locale.

        If no locale is explicitly set, it will return the current system locale, unless system_if_unset is set to
        False, in which case it will return None.
        """
        if self.current_locale:
            return self.current_locale

        if system_if_unset:
            return QLocale()

        return None

    @staticmethod
    def find_best_locale(locale=None) -> QLocale:
        """Find the best locale to use, defaulting to system locale."""
        return QLocale(locale) if locale else QLocale()

    def load_locale(self, app: QApplication, locale: QLocale) -> None:
        """Load the given locale into the application."""
        system_locale = QLocale()

        if locale != system_locale:
            self.current_locale = locale

        print('Using locale: {} {}'
              .format(locale.name(), "(system locale)" if locale == system_locale else ""))
        print('Localization loaded:',
              self.translator.load(locale, 'pext', '_', self.locale_dir, '.qm'))

        app.installTranslator(self.translator)


class ProfileManager():
    """Create, remove, list, load and save to a profile."""

    def __init__(self) -> None:
        """Initialize the profile manager."""
        self.profile_dir = os.path.join(ConfigRetriever.get_path(), 'profiles')
        self.module_dir = os.path.join(ConfigRetriever.get_path(), 'modules')
        self.saved_settings = ['_window_geometry',
                               'turbo_mode',
                               'locale',
                               'minimize_mode',
                               'output_mode',
                               'output_separator',
                               'theme',
                               'tray',
                               'global_hotkey_enabled',
                               'last_update_check',
                               'update_check',
                               'object_update_check',
                               'object_update_install']

    @staticmethod
    def _get_pid_path(profile: str) -> str:
        if platform.system() == 'Windows':
            uid = getpass.getuser()
        else:
            uid = str(os.getuid())

        return os.path.join(ConfigRetriever.get_temp_path(), '{}_pext_{}.pid'.format(uid, profile))

    @staticmethod
    def lock_profile(profile: str) -> None:
        """Claim the profile as in-use."""
        pidfile = ProfileManager._get_pid_path(profile)
        pid = str(os.getpid())
        open(pidfile, 'w').write(pid)

    @staticmethod
    def get_lock_instance(profile: str) -> Optional[int]:
        """Get the pid of the current process having a lock, if any."""
        pidfile = ProfileManager._get_pid_path(profile)
        if not os.path.isfile(pidfile):
            return None

        pid = int(open(pidfile, 'r').read())

        if not psutil.pid_exists(pid):
            return None

        return pid

    @staticmethod
    def unlock_profile(profile: str) -> None:
        """Remove the status of the profile currently being in use."""
        pidfile = ProfileManager._get_pid_path(profile)
        os.unlink(pidfile)

    @staticmethod
    def default_profile_name() -> str:
        """Return the default profile name."""
        return "default"

    def create_profile(self, profile: str) -> bool:
        """Create a new empty profile if name not in use already."""
        try:
            os.mkdir(os.path.join(self.profile_dir, profile))
        except OSError:
            return False

        return True

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile that's currently not in use, if the new name doesn't already exist."""
        if ProfileManager.get_lock_instance(old_name):
            return False

        try:
            os.rename(os.path.join(self.profile_dir, old_name), os.path.join(self.profile_dir, new_name))
        except OSError:
            return False

        return True

    def remove_profile(self, profile: str) -> bool:
        """Remove a profile and all associated data if not in use."""
        if ProfileManager.get_lock_instance(profile):
            return False

        rmtree(os.path.join(self.profile_dir, profile))
        return True

    def list_profiles(self) -> List[str]:
        """List the existing profiles."""
        return os.listdir(self.profile_dir)

    def save_modules(self, profile: str, modules: List[UiModule]) -> None:
        """Save the list of open modules and their settings to the profile."""
        config = configparser.ConfigParser()
        for number, module in enumerate(modules):
            settings = {}
            for setting in module.settings:
                # Only save non-internal variables
                if setting[0] != "_":
                    value = module.settings[setting]
                    settings[setting] = str(value) if value is not None else ''

            # Append Pext state variables
            for setting in module.vm.settings:
                try:
                    value = module.vm.settings[setting].name
                except KeyError:
                    value = module.vm.settings[setting]

                settings[setting] = str(value) if value is not None else ''

            config['{}_{}'.format(number, module.metadata['id'])] = settings

        with open(os.path.join(self.profile_dir, profile, 'modules'), 'w') as configfile:
            config.write(configfile)

    def retrieve_modules(self, profile: str) -> List[Dict]:
        """Retrieve the list of modules and their settings from the profile."""
        config = configparser.ConfigParser()
        modules = []

        config.read(os.path.join(self.profile_dir, profile, 'modules'))

        for module in config.sections():
            identifier = module.split('_', 1)[1]
            data = ObjectManager.list_object(os.path.join(self.module_dir, identifier.replace('.', '_')))
            if not data:
                # Module no longer seems to exist, skip
                continue

            settings = {}

            for key in config[module]:
                settings[key] = config[module][key]

            modules.append({'metadata': data['metadata'], 'settings': settings})

        return modules

    def save_settings(self, profile: Optional[str], changed_key: Optional[str] = None) -> None:
        """Save the current settings to the profile."""
        if changed_key and changed_key not in self.saved_settings:
            return

        config = configparser.ConfigParser()
        settings_to_store = {}
        for setting in Settings.get_all(profile if profile else None):
            if setting in self.saved_settings:
                setting_data = Settings.get(setting)
                try:
                    setting_data = setting_data.value
                except AttributeError:
                    pass
                if setting_data is not None and setting_data != "":
                    settings_to_store[setting] = setting_data

        config['settings'] = settings_to_store

        if profile:
            path = os.path.join(self.profile_dir, profile, 'settings')
        else:
            path = os.path.join(ConfigRetriever.get_path(), 'settings')

        with open(path, 'w') as configfile:
            config.write(configfile)

    def retrieve_settings(self, profile: Optional[str]) -> Dict[str, Any]:
        """Retrieve the settings from the profile."""
        config = configparser.ConfigParser()
        setting_dict = {}  # type: Dict[str, Any]

        if profile:
            path = os.path.join(self.profile_dir, profile, 'settings')
        else:
            path = os.path.join(ConfigRetriever.get_path(), 'settings')

        config.read(path)

        try:
            for setting in config['settings']:
                if setting in self.saved_settings:
                    setting_value = config['settings'][setting]  # type: Any
                    try:
                        setting_value = bool(strtobool(setting_value.lower()))
                    except ValueError:
                        pass
                    setting_dict[setting] = setting_value
        except KeyError:
            pass

        return setting_dict


class ObjectManager():
    """Shared management for modules and themes."""

    @staticmethod
    def list_object(full_path: str) -> Optional[Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return the identifier, name, source and metadata of an object."""
        if not os.path.isdir(full_path):
            return None

        location = os.path.basename(full_path)

        try:
            source = UpdateManager.get_remote_url(full_path)  # type: Optional[str]
        except Exception:
            source = None

        try:
            with open(os.path.join(full_path, "metadata.json"), 'r') as metadata_json:
                metadata = json.load(metadata_json)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Object {} lacks a correctly formatted metadata.json file".format(location))
            return None

        try:
            with open(os.path.join(full_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                metadata.update(json.load(metadata_json_i18n))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Object {} has no metadata_{}.json file".format(location,
                  LocaleManager.find_best_locale(Settings.get('locale')).name()))

        # Ensure the required metadata is set
        if 'id' not in metadata:
            print("Object {} lacks required field id".format(location))
            return None

        if 'name' not in metadata:
            print("Object {} lacks required field name".format(location))
            return None

        # Ensure the location makes sense
        if location != metadata['id'].replace('.', '_'):
            print("Object {}'s location is not correct for identifier {}".format(location, metadata['id']))
            return None

        # Add revision last updated time
        if source:
            try:
                version = UpdateManager.get_version(full_path)
                metadata['version'] = version
            except Exception:
                pass

            try:
                last_updated = UpdateManager.get_last_updated(full_path)
                metadata['last_updated'] = str(last_updated)
            except Exception:
                pass

        return {"source": source, "metadata": metadata}

    @staticmethod
    def list_objects(core_directory: str) -> Dict[str, Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return a list of objects together with their identifier, name, source and metadata."""
        objects = {}

        for directory in os.listdir(core_directory):
            dir_object = ObjectManager.list_object(os.path.join(core_directory, directory))
            if dir_object and isinstance(dir_object['metadata'], dict) and 'id' in dir_object['metadata']:
                object_id = dir_object['metadata']['id']
                objects[object_id] = dir_object

        return objects


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
                UpdateManager.fix_git_url_for_dulwich(url), target=module_path, checkout=branch, force=True
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


class UpdateManager():
    """Manages scheduling and checking automatic updates."""

    def __init__(self) -> None:
        """Initialize the UpdateManager and store the version info of Pext."""
        self.version = "Unknown"
        version = None
        try:
            version = UpdateManager.get_version(os.path.dirname(AppFile.get_path()))
        except Exception:
            pass

        if not version:
            with open(os.path.join(AppFile.get_path(), 'VERSION')) as version_file:
                version = version_file.read().strip()

        if version:
            self.version = version

    @staticmethod
    def _path_to_repo(directory: str) -> Repo:
        return Repo(directory)

    def get_core_version(self) -> str:
        """Return the version info of Pext itself."""
        return self.version

    @staticmethod
    def fix_git_url_for_dulwich(url: str) -> str:
        """Append .git to the URL to work around a Dulwich + GitHub issue.

        Dulwich before 0.18.4 sends an user agent GitHub doesn't respond to correctly.
        """
        if url.startswith("https://") and not url.endswith(".git"):
            url += ".git"

        return url

    @staticmethod
    def get_wanted_branch_from_metadata(metadata: Dict[Any, Any], identifier: str) -> bytes:
        """Get the wanted branch from the given metadata.json."""
        branch_type = "stable"
        if Settings.get('_force_module_branch_type'):
            branch_type = Settings.get('_force_module_branch_type')

        try:
            branch = metadata["git_branch_{}".format(branch_type)]
        except (IndexError, KeyError, json.decoder.JSONDecodeError):
            print("Couldn't figure out branch for type {} of {}, defaulting to master".format(branch_type, identifier))
            return "refs/heads/master".encode()

        return "refs/heads/{}".format(branch).encode()

    @staticmethod
    def get_wanted_branch(directory: str) -> bytes:
        """Get the wanted branch from the metadata.json for this git object."""
        try:
            with open(os.path.join(directory, "metadata.json"), 'r') as metadata_json:
                branch = UpdateManager.get_wanted_branch_from_metadata(json.load(metadata_json), directory)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Couldn't figure out branch for {}, defaulting to master".format(directory))
            return "refs/heads/master".encode()

        return branch

    @staticmethod
    def get_remote_url(directory: str) -> str:
        """Get the url of the given remote for the specified git-managed directory."""
        with UpdateManager._path_to_repo(directory) as repo:
            config = repo.get_config()
            return config.get(("remote".encode(), "origin".encode()), "url".encode()).decode()

    @staticmethod
    def ensure_repo_branch(directory: str, branch: bytes) -> None:
        """Check if an update is available for the git-managed directory."""
        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            # Get current branch
            current_branch = repo.refs.get_symrefs()[b"HEAD"]

            if current_branch != branch:
                # Update to wanted branch
                remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
                try:
                    porcelain.pull(repo, remote_url, branch, force=True)
                    # Ensure a clean state on the wanted branch
                    repo.reset_index(repo[branch].tree)
                    repo.refs.set_symbolic_ref(b"HEAD", branch)
                except KeyError as e:
                    Logger.log_error(None, Translation.get("failed_to_checkout_branch").format(directory, e))
                    traceback.print_exc()

    @staticmethod
    def has_update(directory: str, branch=None) -> bool:
        """Check if an update is available for the git-managed directory."""
        if branch is None:
            branch = UpdateManager.get_wanted_branch(directory)

        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            UpdateManager.ensure_repo_branch(directory, branch)

            old_commit = repo[repo.head()]
            remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
            try:
                remote_commit = porcelain.ls_remote(remote_url)[branch]
            except Exception as e:
                Logger.log_error(None, Translation.get("failed_to_check_for_module_update").format(directory, e))
                traceback.print_exc()

                return False

            return remote_commit != old_commit.id

    @staticmethod
    def update(directory: str) -> bool:
        """If an update is available, attempt to update the git-managed directory."""
        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            old_commit = repo[repo.head()]

            # Update
            remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
            porcelain.pull(repo, remote_url, force=True)

            # See if anything was updated
            return old_commit != repo[repo.head()]

    @staticmethod
    def get_version(directory: str) -> Optional[str]:
        """Get the version of the git-managed directory."""
        return porcelain.describe(directory)

    @staticmethod
    def get_last_updated(directory: str) -> Optional[datetime]:
        """Return the time of the latest update of the git-managed directory."""
        with UpdateManager._path_to_repo(directory) as repo:
            commit = repo[repo.head()]
            return datetime.fromtimestamp(commit.commit_time)

    def check_core_update(self) -> Optional[str]:
        """Check if there is an update of the core and if so, return the name of the new version."""
        # Normalize own version
        if self.version.find('+dev') != -1:
            version = self.version[:self.version.find('+dev')]
        else:
            version = self.version

        if self.version.find('-') != -1:
            available_version = requests.get('https://pext.io/version/nightly').text.splitlines()[0].strip()
        else:
            available_version = requests.get('https://pext.io/version/stable').text.splitlines()[0].strip()

        if parse_version(version.lstrip('v')) < parse_version(available_version.lstrip('v')):
            return available_version

        return None


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


class ViewModel():
    """Manage the communication between user interface and module."""

    def __init__(self, view_settings) -> None:
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self._settings = {}  # type: Dict[str, Any]
        self.entry_list = []  # type: List
        self.filtered_entry_list = []  # type: List
        self.command_list = []  # type: List
        self.filtered_command_list = []  # type: List
        self.result_list = []  # type: List
        self.result_list_index = -1
        self.result_list_model_max_index = -1
        self.selection = []  # type: List[Selection]
        self.search_string = ""
        self.last_search = ""
        self.context_menu_enabled = False
        self.context_menu_index = -1
        self.context_menu_list = []  # type: List
        self.context_menu_base_list = []  # type: List
        self.context_menu_list_full = []  # type: List
        self.extra_info_entries = {}  # type: Dict[str, str]
        self.extra_info_commands = {}  # type: Dict[str, str]
        self.context_menu_entries = {}  # type: Dict[str, List[str]]
        self.context_menu_commands = {}  # type: Dict[str, List[str]]
        self.context_menu_base = []  # type: List[str]
        self.selection_thread = None  # type: Optional[threading.Thread]
        self.minimize_disabled = False

        self.settings = view_settings

        self.stopped = False

        # Callback functions
        self.search_string_changed = lambda search_string: None  # type: Callable[[str], None]
        self.result_list_changed = lambda results, normal_count, entry_count, unfiltered_entry_count: None \
            # type: Callable[[List[str], int, int, int], None]
        self.result_list_index_changed = lambda index: None  # type: Callable[[int], None]
        self.context_menu_enabled_changed = lambda value: None  # type: Callable[[bool], None]
        self.context_menu_index_changed = lambda index: None  # type: Callable[[int], None]
        self.context_menu_list_changed = lambda base, entry_specific: None \
            # type: Callable[[List[str], List[str]], None]
        self.context_info_panel_changed = lambda value: None  # type: Callable[[str], None]
        self.sort_mode_changed = lambda mode: None  # type: Callable[[str], None]
        self.unprocessed_count_changed = lambda count: None  # type: Callable[[int], None]
        self.selection_changed = lambda selection: None  # type: Callable[[List[Selection]], None]
        self.header_text_changed = lambda value: None  # type: Callable[[str], None]

        self.ask_argument = lambda entry, callback: None  # type: Callable[[str, Callable], None]
        self.close_request = lambda manual, force_tray: None  # type: Callable[[bool, bool], None]

    @property
    def settings(self):
        """Return all ViewModel settings."""
        return self._settings

    @settings.setter
    def settings(self, settings):
        """Overwrite ViewModel settings."""
        self._settings = settings

    @property
    def sort_mode(self):
        """Retrieve the current sorting mode as printable name."""
        for data in SortMode:
            if data == self._settings['__pext_sort_mode']:
                return data.name

        # Maybe mode doesn't exist (anymore)
        # Return first value
        for data in SortMode:
            self.sort_mode = data
            return data.name

    @sort_mode.setter
    def sort_mode(self, sort_mode: SortMode):
        """Set the new sorting mode."""
        self._settings['__pext_sort_mode'] = sort_mode
        self.sort_mode_changed(self.sort_mode)

        # Force a resort
        self.search(new_entries=True)

    def stop(self) -> None:
        """Stop the module."""
        self.stopped = True
        self.module.stop()

    def next_sort_mode(self):
        """Calculate and set the next sorting mode available."""
        want_next = False
        for data in SortMode:
            if want_next:
                self.sort_mode = data
                return

            if data == self._settings['__pext_sort_mode']:
                want_next = True

        # End of list reached
        for data in SortMode:
            self.sort_mode = data
            return

    def make_selection(self, disable_minimize=False) -> None:
        """Make a selection if no selection is currently being processed.

        Running the selection making in another thread prevents it from locking
        up Pext's UI, while ensuring existing thread completion prevents race
        conditions.
        """
        if self.stopped:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        self.minimize_disabled = disable_minimize
        self.selection_thread = threading.Thread(target=self.module.selection_made, args=(self.selection,))
        self.selection_thread.start()

    def _get_longest_common_string(self, entries: List[str], start="") -> Optional[str]:
        """Return the longest common string.

        Returns the longest common string for each entry in the list, starting
        at the start.

        Keyword arguments:
        entries -- the list of entries
        start -- the string to start with (default "")

        All entries not starting with start are discarded before additional
        matches are looked for.

        Returns the longest common string, or None if not a single value
        matches start.
        """
        # Filter out all entries that don't match at the start
        entry_list = []
        for entry in entries:
            if entry.startswith(start):
                entry_list.append(entry)

        common_chars = list(start)

        try:
            while True:
                common_char = None
                for entry in entry_list:
                    if common_char is None:
                        common_char = entry[len(common_chars)]
                    elif common_char != entry[len(common_chars)]:
                        return ''.join(common_chars)

                if common_char is None:
                    return None

                common_chars.append(common_char)
        except IndexError:
            # We fully match a string
            return ''.join(common_chars)

    def clear_queue(self) -> None:
        """Clear all enqueued actions."""
        while True:
            try:
                self.queue.get_nowait()
            except Empty:
                return
            self.queue.task_done()

    def bind_search_string_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the search_string_changed callback.

        This ensures we can notify the window when the search string changes.
        """
        self.search_string_changed = function

    def bind_result_list_changed_callback(self, function: Callable[[List[str], int, int, int], None]) -> None:
        """Bind the result_list_changed callback.

        This ensures we can notify the window when the result list changes.
        """
        self.result_list_changed = function

    def bind_result_list_index_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the result_list_index_changed callback.

        This ensures we can notify the window when the result list index changes.
        """
        self.result_list_index_changed = function

    def bind_context_menu_enabled_changed_callback(self, function: Callable[[bool], None]) -> None:
        """Bind the context_menu_enabled_changed callback.

        This ensures we can notify the window when the state of the context menu changes.
        """
        self.context_menu_enabled_changed = function

    def bind_context_menu_index_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the context_menu_index_changed callback.

        This ensures we can notify the window when the context menu index changes.
        """
        self.context_menu_index_changed = function

    def bind_context_menu_list_changed_callback(self, function: Callable[[List[str], List[str]], None]) -> None:
        """Bind the context_menu_list_changed callback.

        This ensures we can notify the window when the context menu's list changes.
        """
        self.context_menu_list_changed = function

    def bind_context_info_panel_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the context_info_panel_changed callback.

        This ensures we can notify the window when the context info menu changes.
        """
        self.context_info_panel_changed = function

    def bind_base_info_panel_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the base_info_panel_changed callback.

        This ensures we can notify the window when the base info menu changes.
        """
        self.base_info_panel_changed = function

    def bind_sort_mode_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the sort_mode_changed callback.

        This ensures we can notify the window when the sort mode changes.
        """
        self.sort_mode_changed = function

    def bind_unprocessed_count_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the unprocessed_count_changed callback.

        This ensures we can notify the window when the unprocessed count changes.
        """
        self.unprocessed_count_changed = function

    def bind_selection_changed_callback(self, function: Callable[[List[Selection]], None]) -> None:
        """Bind the selection_changed callback.

        This ensures we can notify the window when the selection changes.
        """
        self.selection_changed = function

    def bind_header_text_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the header_text_changed callback.

        This ensures we can notify the window when the header text changes.
        """
        self.header_text_changed = function

    def bind_ask_argument_callback(self, function: Callable[[str, Callable], None]) -> None:
        """Bind the ask_argument callback.

        This ensures we can notify the window when an argument is requested.
        """
        self.ask_argument = function

    def bind_close_request_callback(self, function: Callable[[bool, bool], None]) -> None:
        """Bind the close_request callback.

        This ensures we can notify the window when a window closure is requested.
        """
        self.close_request = function

    def bind_queue(self, queue: Queue) -> None:
        """Bind the queue."""
        self.queue = queue

    def bind_module(self, module: ModuleBase) -> None:
        """Bind the module.

        This ensures we can call functions in it.
        """
        self.module = module

    def update_result_list_index(self, index: int) -> None:
        """Update the result list index."""
        self.result_list_index = index

    def update_context_menu_index(self, index: int) -> None:
        """Update the context menu index."""
        self.context_menu_index = index

    def go_up(self, to_base=False) -> None:
        """Go one level up.

        This means that, if we're currently in the entry content list, we go
        back to the entry list. If we're currently in the entry list, we clear
        the search bar. If we're currently in the entry list and the search bar
        is empty, we tell the window to hide/close itself.
        """
        if self.context_menu_enabled:
            self.hide_context()
            if not to_base:
                return

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
            if not to_base:
                return

        if self.stopped:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        if len(self.selection) > 0:
            if not to_base:
                self.selection.pop()
            else:
                self.selection = []

            self.entry_list = []
            self.command_list = []

            self.search(new_entries=True)

            self.selection_changed(self.selection)

            self.clear_queue()

            self.make_selection()
        else:
            self.close_request(True, False)

    def search(self, new_entries=False, manual=False) -> None:
        """Filter the entry list.

        Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        if self.stopped:
            return

        # Don't search if nothing changed
        if not new_entries and self.search_string == self.last_search:
            return

        # Notify window the search string changed
        self.search_string_changed(self.search_string)

        # Enable checking for changes next time
        self.last_search = self.search_string

        current_match = None
        current_index = 0

        # If context menu is open, search in context menu
        if self.context_menu_enabled:
            current_entry = self._get_entry()
            try:
                if current_entry['type'] == SelectionType.entry:
                    entry_list = [entry for entry in self.context_menu_entries[current_entry['value']]]
                else:
                    entry_list = [entry for entry in self.context_menu_commands[current_entry['value']]]
            except KeyError:
                entry_list = []

            if current_entry['type'] == SelectionType.command:
                entry_list.insert(0, Translation.get("enter_arguments"))

            # Sort if sorting is enabled
            if self.settings['__pext_sort_mode'] != SortMode.Module:
                reverse = self.settings['__pext_sort_mode'] == SortMode.Descending
                self.sorted_context_list = sorted(entry_list, reverse=reverse)
                self.sorted_context_base_list = sorted(self.context_menu_base, reverse=reverse)
            else:
                self.sorted_context_list = entry_list
                self.sorted_context_base_list = self.context_menu_base

            # Get current match
            try:
                current_match = self.context_menu_list_full[self.context_menu_index]
            except IndexError:
                pass
        # Else, search in normal list
        else:
            # Sort if sorting is enabled
            if self.settings['__pext_sort_mode'] != SortMode.Module:
                reverse = self.settings['__pext_sort_mode'] == SortMode.Descending
                self.sorted_entry_list = sorted(self.entry_list, reverse=reverse)
                self.sorted_command_list = sorted(self.command_list, reverse=reverse)
                self.sorted_filtered_entry_list = sorted(self.filtered_entry_list, reverse=reverse)
                self.sorted_filtered_command_list = sorted(self.filtered_command_list, reverse=reverse)
            else:
                self.sorted_entry_list = self.entry_list
                self.sorted_command_list = self.command_list
                self.sorted_filtered_entry_list = self.filtered_entry_list
                self.sorted_filtered_command_list = self.filtered_command_list

            # Get current match
            try:
                current_match = self.result_list[self.result_list_index]
            except IndexError:
                pass

        # If empty, show all
        if not self.search_string and not new_entries:
            if self.context_menu_enabled:
                self.filtered_context_list = entry_list
                self.filtered_context_base_list = self.context_menu_base
                self.sorted_filtered_context_list = self.sorted_context_list
                self.sorted_filtered_context_base_list = self.sorted_context_base_list

                self.context_menu_list_changed(
                    self.sorted_filtered_context_base_list,
                    self.sorted_filtered_context_list)
            else:
                self.filtered_entry_list = self.entry_list
                self.filtered_command_list = self.command_list
                self.sorted_filtered_entry_list = self.sorted_entry_list
                self.sorted_filtered_command_list = self.sorted_command_list

                combined_list = self.sorted_filtered_entry_list + self.sorted_filtered_command_list

                self.result_list = combined_list
                self.result_list_changed(
                    self.result_list,
                    len(self.sorted_filtered_entry_list),
                    len(self.sorted_filtered_command_list),
                    len(self.entry_list) + len(self.command_list))

            # Keep existing selection, otherwise ensure something is selected
            if current_match:
                try:
                    current_index = combined_list.index(current_match)
                except ValueError:
                    current_index = 0

            if self.context_menu_enabled:
                self.context_menu_index = current_index
                self.context_menu_index_changed(self.context_menu_index)
            else:
                self.result_list_index = current_index
                self.result_list_index_changed(self.result_list_index)

            self.update_context_info_panel()

            return

        if self.context_menu_enabled:
            self.filtered_context_list = []
            self.filtered_context_base_list = []
        else:
            self.filtered_entry_list = []
            self.filtered_command_list = []

        # String matching logic
        list_match = self.search_string.lower().split(' ')

        def check_list_match(entries, string_list) -> List[str]:
            return_list = []  # type: List[str]
            for entry in entries:
                lower_entry = str(entry).lower()
                for self.search_string_part in string_list:
                    if self.search_string_part not in lower_entry:
                        break
                else:
                    # If exact match, put on top
                    if len(string_list) == 1 and string_list[0] == lower_entry:
                        return_list.insert(0, entry)
                    # otherwise, put on bottom
                    else:
                        return_list.append(entry)

            return return_list

        if self.context_menu_enabled:
            self.filtered_context_list = check_list_match(self.sorted_context_list, list_match)
            self.filtered_context_base_list = check_list_match(self.sorted_context_base_list, list_match)
        else:
            self.filtered_entry_list = check_list_match(self.sorted_entry_list, list_match)
            self.filtered_command_list = check_list_match(self.sorted_command_list, list_match)

        if self.context_menu_enabled:
            self.context_menu_list_changed(self.filtered_context_base_list, self.filtered_context_list)
            combined_list = self.filtered_context_list + self.filtered_context_base_list
        else:
            combined_list = self.filtered_entry_list + self.filtered_command_list
            self.result_list = combined_list
            self.result_list_changed(
                self.result_list,
                len(self.filtered_entry_list),
                len(self.filtered_command_list),
                len(self.entry_list) + len(self.command_list))

        # See if we have an exact match
        if combined_list and len(list_match) == 1 and str(combined_list[0]).lower() == list_match[0]:
            current_index = 0
        # Otherwise, keep existing selection
        elif current_match:
            try:
                current_index = combined_list.index(current_match)
            # As fallback, ensure something is selected
            except ValueError:
                current_index = 0

        if self.context_menu_enabled:
            self.context_menu_index = current_index
            self.context_menu_index_changed(self.context_menu_index)
        else:
            self.result_list_index = current_index
            self.result_list_index_changed(self.result_list_index)

        self.update_context_info_panel()

        # Turbo mode: Select entry if only entry left
        if Settings.get('turbo_mode') and len(combined_list) == 1 and self.queue.empty() and self.search_string:
            self.select(force_args=True)

    def _get_entry(self, include_context=False) -> Selection:
        """Get info on the entry that's currently focused."""
        if include_context and self.context_menu_enabled:
            current_index = self.context_menu_index

            selected_entry = self._get_entry()

            # Return entry-specific option if selected, otherwise base option
            if current_index >= len(self.filtered_context_list):
                # Selection is a base entry
                return Selection(
                    type=SelectionType.none,
                    value=None,
                    context_option=self.filtered_context_base_list[current_index - len(self.filtered_context_list)]
                )
            else:
                selected_entry.context_option = self.filtered_context_list[current_index]

            return selected_entry

        current_index = self.result_list_index

        if current_index >= len(self.filtered_entry_list):
            # Selection is a command
            selection_type = SelectionType.command
            entry = self.filtered_command_list[current_index - len(self.filtered_entry_list)]
        else:
            selection_type = SelectionType.entry
            entry = self.filtered_entry_list[current_index]

        return Selection(type=selection_type, value=entry, context_option=None)

    def select(self, command_args="", force_args=False, disable_minimize=False) -> None:
        """Notify the module of our selection entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        selection = self._get_entry(include_context=True)
        if selection.type == SelectionType.command:
            if not command_args and (force_args or selection.context_option == Translation.get("enter_arguments")):
                self.input_args()
                return

        if selection.context_option == Translation.get("enter_arguments"):
            selection.context_option = None

        selection.args = command_args
        self.selection.append(selection)

        self.context_menu_enabled = False
        self.context_menu_enabled_changed(self.context_menu_enabled)
        self.selection_changed(self.selection)

        self.entry_list = []
        self.command_list = []
        self.extra_info_entries = {}
        self.extra_info_commands = {}
        self.context_menu_entries = {}
        self.context_menu_commands = {}

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search(new_entries=True, manual=True)
        self.clear_queue()

        self.make_selection(disable_minimize=disable_minimize)

    def show_context(self) -> None:
        """Show the context menu of the selected entry."""
        if self.stopped:
            return

        if not self.filtered_command_list and not self.filtered_entry_list:
            return

        current_entry = self._get_entry()

        entries = 0

        # Get all menu-specific entries
        try:
            if current_entry['type'] == SelectionType.entry:
                entries += len(self.context_menu_entries[current_entry['value']])
            else:
                entries += len(self.context_menu_commands[current_entry['value']])
        except KeyError:
            pass

        if not entries and not self.context_menu_base:
            if current_entry['type'] == SelectionType.command:
                self.input_args()
                return

            Logger.log(None, Translation.get("no_context_menu_available"))
            return

        self.context_menu_enabled = True
        self.context_menu_enabled_changed(self.context_menu_enabled)
        self.context_menu_index_changed(0)

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search(new_entries=True)

    def hide_context(self) -> None:
        """Hide the context menu."""
        if self.stopped:
            return

        self.context_menu_enabled = False
        self.context_menu_enabled_changed(self.context_menu_enabled)

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search()

    def update_context_info_panel(self, request_update=True) -> None:
        """Update the context info panel with the info panel data of the currently selected entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            self.context_info_panel_changed("")
            return

        current_entry = self._get_entry()

        if request_update:
            info_selection = self.selection[:]
            new_selection_entry = current_entry
            info_selection.append(new_selection_entry)

            threading.Thread(target=self.module.extra_info_request, args=(info_selection,)).start()

        try:
            if current_entry.value is not None:
                if current_entry.type == SelectionType.entry:
                    self.context_info_panel_changed(self.extra_info_entries[current_entry.value])
                else:
                    self.context_info_panel_changed(self.extra_info_commands[current_entry.value])
        except KeyError:
            self.context_info_panel_changed("")

    def update_base_info_panel(self, base_info: str) -> None:
        """Update the base info panel based on the current module state."""
        self.base_info_panel_changed(str(base_info))

    def set_header(self, content) -> None:
        """Set the header text."""
        self.header_text_changed(str(content))

    def tab_complete(self) -> None:
        """Tab-complete based on the current seach input.

        This tab-completes the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        if self.stopped:
            return

        current_input = self.search_string
        combined_list = self.filtered_entry_list + self.filtered_command_list

        entry = self._get_longest_common_string(
                [entry.lower() for entry in combined_list],
                start=current_input.lower())
        if entry is None or len(entry) <= len(current_input):
            self.queue.put(
                [Action.add_error, Translation.get("no_tab_completion_possible")])
            return

        self.search_string = entry
        self.search_string_changed(entry)
        self.search()

    def input_args(self) -> None:
        """Open dialog that allows the user to input command arguments."""
        if self.stopped:
            return

        if not self.filtered_command_list and not self.filtered_entry_list:
            self.queue.put(
                [Action.add_error, Translation.get("no_entry_selected")])
            return

        selected_entry = self._get_entry(include_context=True)
        if not self.context_menu_enabled and selected_entry["type"] != SelectionType.command:
            if len(self.filtered_command_list) > 0:
                # Jump to the first command in case the current selection
                # is not a command
                self.result_list_index = len(self.filtered_entry_list)
                self.result_list_index_changed(self.result_list_index)
                selected_entry = self._get_entry(include_context=True)
            else:
                self.queue.put(
                    [Action.add_error, Translation.get("no_command_available_for_current_filter")])
                return

        self.ask_argument(selected_entry["value"], self.select)


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
            porcelain.clone(UpdateManager.fix_git_url_for_dulwich(url), target=theme_path, checkout=branch, force=True)
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


class Settings():
    """A globally accessible class that stores all Pext's settings."""

    __settings = {
        '_launch_app': True,  # Keep track if launching is normal
        '_window_geometry': None,
        '_portable': False,
        '_force_module_branch_type': None,  # TODO: Remove in favor of a proper per-module selection
        'background': False,
        'turbo_mode': False,
        'locale': None,
        'modules': [],
        'minimize_mode': MinimizeMode.Normal if platform.system() == "Darwin" else MinimizeMode.Tray,
        'profile': ProfileManager.default_profile_name(),
        'output_mode': OutputMode.DefaultClipboard,
        'output_separator': OutputSeparator.Enter,
        'style': None,
        'theme': None,
        'global_hotkey_enabled': True,
        'tray': True
    }  # type: Dict[str, Any]

    __global_settings = {
        'last_update_check': None,
        'update_check': None,  # None = not asked, True/False = permission
        'object_update_check': None,  # None = not asked, True/False = permission
        'object_update_install': True  # True/False = permission
    }

    @staticmethod
    def get(name, default=None):
        """Return the value of a single setting, falling back to default if None."""
        try:
            value = Settings.__global_settings[name]
            if value is None:
                return default

            return value
        except KeyError:
            pass

        try:
            value = Settings.__settings[name]
        except KeyError:
            value = None

        if value is None:
            return default

        return value

    @staticmethod
    def get_all(profile=None):
        """Return all settings."""
        if profile:
            return Settings.__settings
        else:
            return Settings.__global_settings

    @staticmethod
    def set(name, value):
        """Set a single setting if this setting is known."""
        if name in Settings.__global_settings:
            profile = None
        else:
            profile = Settings.get('profile')
            if name not in Settings.__settings:
                raise NameError('{} is not a key of Settings'.format(name))

        if Settings.get(name) == value:
            return

        if name in Settings.__global_settings:
            Settings.__global_settings[name] = value
        else:
            Settings.__settings[name] = value

        ProfileManager().save_settings(profile, changed_key=name)

    @staticmethod
    def update(value):
        """Update the dictionary with new values if any changed."""
        Settings.__settings.update(value)

    @staticmethod
    def update_global(value):
        """Update the globals dictionary with new values if any changed."""
        Settings.__global_settings.update(value)


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
        from ui_qt5 import Window, Tray, HotkeyHandler, SignalHandler
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
