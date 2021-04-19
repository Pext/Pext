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
import json
import os
import platform
import re
import signal
import sys
import time
import traceback

from enum import IntEnum
try:
    from typing import Any, Callable, Dict, List, Optional, Union
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional, Union  # type: ignore  # noqa: F401
from queue import Empty, Queue

import requests

from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.Qt import QIcon

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .shared import (AppFile, ConfigRetriever, Core, InternalCallProcessor, LocaleManager, Logger, ModuleManager,
                     ObjectManager, OutputMode, ProfileManager, Settings, ThemeManager, Translation, UiModule,
                     UpdateManager)


# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(os.path.join(AppFile.get_path(), 'helpers'))
sys.path.append(os.path.join(AppFile.get_path()))

from pext_helpers import Action, Selection  # noqa: E402

if False:
    # To make MyPy understand Window exists...
    import Window


class UIType(IntEnum):
    """A list of supported UI types."""

    Qt5 = 0


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
                main_loop_request = self.main_loop_queue.get_nowait()
                main_loop_request()
            except Empty:
                pass

            # Process a call if there is any to process
            InternalCallProcessor.process()

            self.app.sendPostedEvents()
            self.app.processEvents()
            Logger.show_next_message()

            all_empty = True
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
                    all_empty = False
                except Empty:
                    if focused_module and module.entries_processed:
                        module.vm.search(new_entries=True)

                    module.entries_processed = 0
                except Exception as e:
                    print('WARN: Module {} caused exception {}'.format(module.metadata['name'], e))
                    traceback.print_exc()

            if all_empty:
                if self.window.window.isVisible():
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)


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


def main(ui_type: UIType = UIType.Qt5) -> None:
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
        app.setStyle(QStyleFactory().create(Settings.get('style')))

    # Qt5's default style for macOS seems to have sizing bugs for buttons, so
    # we force the Fusion theme instead
    if platform.system() == 'Darwin':
        app.setStyle(QStyleFactory().create('Fusion'))

    theme_identifier = Settings.get('theme')
    if theme_identifier is not None:
        # Qt5's default style for Windows, windowsvista, does not support palettes properly
        # If the user doesn't explicitly chose a style, but wants theming, we force
        # it to use Fusion, which gets themed properly
        if platform.system() == 'Windows' and Settings.get('style') is None:
            app.setStyle(QStyleFactory().create('Fusion'))

        theme = theme_manager.load(theme_identifier)
        theme_manager.apply(theme, app)

    # Prepare UI-specific
    if ui_type == UIType.Qt5:
        from ui.qt5 import Window, Tray, HotkeyHandler, SignalHandler
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


if __name__ == "__main__":
    main(UIType.Qt5)
