#!/usr/bin/env python3

# Copyright (c) 2016 - 2017 Sylvia van Os <sylvia@hackerchick.me>
#
# This file is part of Pext
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

import atexit
import collections
import configparser
import getopt
import json
import os
import platform
import signal
import sys
import threading
import time
import traceback
import webbrowser

from importlib import reload  # type: ignore
from inspect import getmembers, isfunction, ismethod, signature
from shutil import rmtree
from subprocess import check_call, check_output, CalledProcessError, Popen
try:
    from typing import Dict, List, Optional, Tuple
except ImportError:
    from backports.typing import Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import urlopen
from queue import Queue, Empty

# FIXME: Workaround for https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826
if platform.system() == "Linux":
    try:
        from OpenGL import GL
    except ImportError:
        print("python3-opengl is not installed. If Pext fails to render, please try installing it. See https://github.com/Pext/Pext/issues/11.")

from PyQt5.QtCore import QStringListModel, QLocale, QTranslator
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QDialogButtonBox,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QMenu, QMessageBox, QTextEdit, QVBoxLayout,
                             QStyleFactory, QSystemTrayIcon)
from PyQt5.Qt import QClipboard, QIcon, QObject, QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlProperty, QUrl


class AppFile():
    """Get access to application-specific files."""

    @staticmethod
    def get_path(name: str) -> str:
        """Return the absolute path by file or directory name."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(AppFile.get_path('helpers'))

from pext_base import ModuleBase  # noqa: E402
from pext_helpers import Action, SelectionType  # noqa: E402


class VersionRetriever():
    """Retrieve general information."""

    @staticmethod
    def get_version() -> str:
        """Return the version information and cache it."""
        with open(AppFile.get_path('VERSION')) as version_file:
            return version_file.read().strip()


class ConfigRetriever():

    """Retrieve configuration entries."""

    def __init__(self) -> None:
        """Initialize the configuration."""
        # Initialze defaults
        try:
            config_home = os.environ['XDG_CONFIG_HOME']
        except:
            config_home = os.path.expanduser('~/.config/')

        self.config = {'config_path': os.path.join(config_home, 'pext/')}

    def get_setting(self, variable: str):
        """Get a specific configuration setting."""
        return self.config[variable]


class RunConseq():
    """A simple helper to run several functions consecutively."""

    def __init__(self, functions: List) -> None:
        """Run the given function consecutively."""
        for function in functions:
            if len(function['args']) > 0:
                function['name'](function['args'], **function['kwargs'])
            else:
                function['name'](**function['kwargs'])


class InputDialog(QDialog):
    """A simple dialog requesting user input."""

    def __init__(self, question: str, text: str, parent=None) -> None:
        """Initialize the dialog."""
        super().__init__(parent)

        self.setWindowTitle("Pext")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(question))
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(text)
        layout.addWidget(self.text_edit)
        button = QDialogButtonBox(QDialogButtonBox.Ok)
        button.accepted.connect(self.accept)
        layout.addWidget(button)

    def show(self) -> Tuple[str, bool]:
        """Show the dialog."""
        result = self.exec_()
        return (self.text_edit.toPlainText(), result == QDialog.Accepted)


class Logger():
    """Log events to the appropriate location.

    Shows events in the main window and, if the main window is not visible,
    as a desktop notification.
    """

    def __init__(self, window: 'Window') -> None:
        """Initialize the logger and add a status bar to the main window."""
        self.window = window
        self.queued_messages = []  # type: List[Dict[str, str]]

        self.last_update = None  # type: Optional[float]
        self.status_text = self.window.window.findChild(QObject, "statusText")
        self.status_queue = self.window.window.findChild(QObject, "statusQueue")

    def _queue_message(self, module_name: str, message: str, type_name: str) -> None:
        """Queue a message for display."""
        for formatted_message in self._format_message(module_name, message):
            self.queued_messages.append(
                {'message': formatted_message, 'type': type_name})

    def _format_message(self, module_name: str, message: str) -> List[str]:
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

    def show_next_message(self) -> None:
        """Show next statusbar message.

        If the status bar has not been updated for 1 second, display the next
        message. If no messages are available, clear the status bar after it
        has been displayed for 5 seconds.
        """
        current_time = time.time()
        time_diff = 5 if len(self.queued_messages) < 1 else 1
        if self.last_update and current_time - time_diff < self.last_update:
            return

        if len(self.queued_messages) == 0:
            QQmlProperty.write(self.status_text, "text", "")
            self.last_update = None
        else:
            message = self.queued_messages.pop(0)

            if message['type'] == 'error':
                statusbar_message = "<font color='red'>{}</color>".format(
                    message['message'])
                notification_message = 'E: {}'.format(message['message'])
            else:
                statusbar_message = message['message']
                notification_message = message['message']

            QQmlProperty.write(self.status_text, "text", statusbar_message)

            if not self.window.window.isVisible():
                Popen(['notify-send', 'Pext', notification_message])

            self.last_update = current_time

    def add_error(self, module_name: str, message: str) -> None:
        """Add an error message to the queue."""
        self._queue_message(module_name, message, 'error')

    def add_message(self, module_name: str, message: str) -> None:
        """Add a regular message to the queue."""
        self._queue_message(module_name, message, 'message')

    def set_queue_count(self, count: List[int]) -> None:
        """Show the queue size on screen."""
        QQmlProperty.write(self.status_queue, "entriesLeftForeground", count[0])
        QQmlProperty.write(self.status_queue, "entriesLeftBackground", count[1])


class MainLoop():
    """Main application loop.

    The main application loop connects the application, queue and UI events and
    ensures these events get managed without locking up the UI.
    """

    def __init__(self, app: QApplication, window: 'Window', settings: Dict, logger: Logger) -> None:
        """Initialize the main loop."""
        self.app = app
        self.window = window
        self.settings = settings
        self.logger = logger

    def _process_tab_action(self, tab: Dict, active_tab: int) -> None:
        action = tab['queue'].get_nowait()

        if action[0] == Action.critical_error:
            self.logger.add_error(tab['module_name'], action[1])
            tab_id = self.window.tab_bindings.index(tab)
            self.window.module_manager.unload_module(self.window, tab_id)

        elif action[0] == Action.add_message:
            self.logger.add_message(tab['module_name'], action[1])

        elif action[0] == Action.add_error:
            self.logger.add_error(tab['module_name'], action[1])

        elif action[0] == Action.add_entry:
            tab['vm'].entry_list = tab['vm'].entry_list + [action[1]]

        elif action[0] == Action.prepend_entry:
            tab['vm'].entry_list = [action[1]] + tab['vm'].entry_list

        elif action[0] == Action.remove_entry:
            tab['vm'].entry_list.remove(action[1])

        elif action[0] == Action.replace_entry_list:
            tab['vm'].entry_list = action[1]

        elif action[0] == Action.add_command:
            tab['vm'].command_list = tab['vm'].command_list + [action[1]]

        elif action[0] == Action.prepend_command:
            tab['vm'].command_list = [action[1]] + tab['vm'].command_list

        elif action[0] == Action.remove_command:
            tab['vm'].command_list.remove(action[1])

        elif action[0] == Action.replace_command_list:
            tab['vm'].command_list = action[1]

        elif action[0] == Action.set_header:
            if len(action) > 1:
                tab['vm'].set_header(action[1])
            else:
                tab['vm'].set_header("")

        elif action[0] == Action.set_filter:
            QQmlProperty.write(tab['vm'].search_input_model, "text", action[1])

        elif action[0] == Action.ask_question_default_yes:
            answer = QMessageBox.question(
                self.window,
                "Pext",
                action[1],
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes)

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                tab['vm'].module.process_response(
                    True if (answer == QMessageBox.Yes) else False,
                    action[2] if len(action) > 2 else None)
            else:
                tab['vm'].module.process_response(
                    True if (answer == QMessageBox.Yes) else False)

        elif action[0] == Action.ask_question_default_no:
            answer = QMessageBox.question(
                self.window,
                "Pext",
                action[1],
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                tab['vm'].module.process_response(
                    True if (answer == QMessageBox.Yes) else False,
                    action[2] if len(action) > 2 else None)
            else:
                tab['vm'].module.process_response(
                    True if (answer == QMessageBox.Yes) else False)

        elif action[0] == Action.ask_input:
            answer, ok = QInputDialog.getText(
                self.window,
                "Pext",
                action[1])

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                tab['vm'].module.process_response(
                    answer if ok else None,
                    action[2] if len(action) > 2 else None)
            else:
                tab['vm'].module.process_response(
                    answer if ok else None)

        elif action[0] == Action.ask_input_password:
            answer, ok = QInputDialog.getText(
                self.window,
                "Pext",
                action[1],
                QLineEdit.Password)

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                tab['vm'].module.process_response(
                    answer if ok else None,
                    action[2] if len(action) > 2 else None)
            else:
                tab['vm'].module.process_response(
                    answer if ok else None)

        elif action[0] == Action.ask_input_multi_line:
            dialog = InputDialog(
                action[1],
                action[2] if len(action) > 2 else "",
                self.window)

            answer, ok = dialog.show()
            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                tab['vm'].module.process_response(
                    answer if ok else None,
                    action[3] if len(action) > 3 else None)
            else:
                tab['vm'].module.process_response(
                    answer if ok else None)

        elif action[0] == Action.copy_to_clipboard:
            # Copy the given data to the user-chosen clipboard
            if self.settings['clipboard'] == 'selection':
                mode = QClipboard.Selection
            else:
                mode = QClipboard.Clipboard

            self.app.clipboard().setText(str(action[1]), mode)

        elif action[0] == Action.set_selection:
            tab['vm'].selection = action[1]

            tab['vm'].context.setContextProperty(
                "resultListModelDepth", len(tab['vm'].selection))

            tab['vm'].module.selection_made(tab['vm'].selection)

        elif action[0] == Action.close:
            self.window.close()

        else:
            print('WARN: Module requested unknown action {}'.format(action[0]))

        if active_tab and tab['entries_processed'] >= 100:
            tab['vm'].search(new_entries=True)
            tab['entries_processed'] = 0

        self.window.update()
        tab['queue'].task_done()

    def run(self) -> None:
        """Process actions modules put in the queue and keep the window working."""
        while True:
            self.app.sendPostedEvents()
            self.app.processEvents()
            self.logger.show_next_message()

            current_tab = QQmlProperty.read(self.window.tabs, "currentIndex")
            queue_size = [0, 0]

            all_empty = True
            for tab_id, tab in enumerate(self.window.tab_bindings):
                if not tab['init']:
                    continue

                if tab_id == current_tab:
                    queue_size[0] = tab['queue'].qsize()
                    active_tab = True
                    tab['vm'].context.setContextProperty(
                        "resultListModelHasEntries", True if tab['vm'].entry_list or tab['vm'].command_list else False)
                else:
                    queue_size[1] += tab['queue'].qsize()
                    active_tab = False

                try:
                    self._process_tab_action(tab, active_tab)
                    tab['entries_processed'] += 1
                    all_empty = False
                except Empty:
                    if active_tab and tab['entries_processed']:
                        tab['vm'].search(new_entries=True)

                    tab['entries_processed'] = 0
                except Exception as e:
                    print('WARN: Module caused exception {}'.format(e))

            self.logger.set_queue_count(queue_size)

            if all_empty:
                if self.window.window.isVisible():
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)


class ProfileManager():
    """Create, remove, list, load and save to a profile."""

    def __init__(self, config_retriever: ConfigRetriever) -> None:
        """Initialize the profile manager."""
        self.profileDir = os.path.join(config_retriever.get_setting('config_path'), 'profiles')
        self.config_retriever = config_retriever

    def create_profile(self, profile: str) -> None:
        """Create a new empty profile."""
        os.mkdir(os.path.join(self.profileDir, profile))

    def remove_profile(self, profile: str) -> None:
        """Remove a profile and all associated data."""
        rmtree(os.path.join(self.profileDir, profile))

    def list_profiles(self) -> List:
        """List the existing profiles."""
        return os.listdir(self.profileDir)

    def save_modules(self, profile: str, modules: List[Dict]) -> None:
        """Save the list of open modules and their settings to the profile."""
        config = configparser.ConfigParser()
        for number, module in enumerate(modules):
            name = ModuleManager.add_prefix(module['module_name'])
            config['{}_{}'.format(number, name)] = module['settings']

        with open(os.path.join(self.profileDir, profile, 'modules'), 'w') as configfile:
            config.write(configfile)

    def retrieve_modules(self, profile: str) -> List[Dict]:
        """Retrieve the list of modules and their settings from the profile."""
        config = configparser.ConfigParser()
        modules = []

        config.read(os.path.join(self.profileDir, profile, 'modules'))

        for module in config.sections():
            settings = {}

            for key in config[module]:
                settings[key] = config[module][key]

            modules.append(
                {'name': module.split('_', 1)[1], 'settings': settings})

        return modules


class ModuleManager():
    """Install, remove, update and list modules."""

    def __init__(self, config_retriever: ConfigRetriever) -> None:
        """Initialize the module manager."""
        self.config_retriever = config_retriever
        self.module_dir = os.path.join(self.config_retriever.get_setting('config_path'), 'modules')
        self.module_dependencies_dir = os.path.join(self.config_retriever.get_setting('config_path'), 'module_dependencies')
        self.logger = None  # type: Optional[Logger]

    @staticmethod
    def add_prefix(module_name: str) -> str:
        """Ensure the string starts with pext_module_."""
        if not module_name.startswith('pext_module_'):
            return 'pext_module_{}'.format(module_name)

        return module_name

    @staticmethod
    def remove_prefix(module_name: str) -> str:
        """Remove pext_module_ from the start of the string."""
        if module_name.startswith('pext_module_'):
            return module_name[len('pext_module_'):]

        return module_name

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.add_message("", message)
        else:
            print(message)

    def _log_error(self, message: str) -> None:
        if self.logger:
            self.logger.add_error("", message)
        else:
            print(message)

    def _pip_install(self, module_dir_name: str) -> int:
        """Install module dependencies using pip."""
        module_requirements_path = os.path.join(self.module_dir, module_dir_name, 'requirements.txt')
        module_dependencies_path = os.path.join(self.module_dependencies_dir, module_dir_name)

        if not os.path.isfile(module_requirements_path):
            return 0

        try:
            os.mkdir(module_dependencies_path)
        except OSError:
            # Probably already exists, that's okay
            pass

        # Create the pip command
        pip_command = [sys.executable,
                       '-m',
                       'pip',
                       'install']

        # FIXME: Cheap hack to work around Debian's faultily-patched pip
        if os.path.isfile('/etc/debian_version'):
            pip_command += ['--system']

        pip_command += ['--upgrade',
                        '--target',
                        module_dependencies_path,
                        '-r',
                        module_requirements_path]

        returncode = 0

        # FIXME: Cheap macOS workaround, part 1
        # See https://github.com/pypa/pip/pull/4111#issuecomment-280616124
        if platform.system() == "Darwin":
            with open(os.path.expanduser('~/.pydistutils.cfg'), 'w') as macos_workaround:
                macos_workaround.write('[install]\nprefix=')

        # Actually run the pip command
        try:
            check_call(pip_command)
        except CalledProcessError as e:
            returncode = e.returncode

        # FIXME: Cheap macOS workaround, part 2
        if platform.system() == "Darwin":
            os.remove(os.path.expanduser('~/.pydistutils.cfg'))

        return returncode

    def bind_logger(self, logger: Logger) -> str:
        """Connect a logger to the module manager.

        If a logger is connected, the module manager will log all
        messages directly to the logger.
        """
        self.logger = logger

    def load_module(self, window: 'Window', module: Dict, locale: str) -> bool:
        """Load a module and attach it to the main window."""
        # Append modulePath if not yet appendend
        module_path = os.path.join(self.config_retriever.get_setting('config_path'), 'modules')
        if module_path not in sys.path:
            sys.path.append(module_path)

        # Remove pext_module_ from the module name
        module_dir = ModuleManager.add_prefix(module['name']).replace('.', '_')
        module_name = ModuleManager.remove_prefix(module['name'])

        # Append module dependencies path if not yet appended
        module_dependencies_path = os.path.join(self.config_retriever.get_setting('config_path'), 'module_dependencies', module_dir)
        if module_dependencies_path not in sys.path:
            sys.path.append(module_dependencies_path)

        # Prepare viewModel and context
        vm = ViewModel()
        module_context = QQmlContext(window.context)
        module_context.setContextProperty(
            "resultListModel", vm.result_list_model_list)
        module_context.setContextProperty(
            "resultListModelMaxIndex", vm.result_list_model_max_index)
        module_context.setContextProperty(
            "resultListModelHasEntries", False)
        module_context.setContextProperty(
            "resultListModelCommandMode", False)
        module_context.setContextProperty(
            "resultListModelDepth", 0)

        # Prepare module
        try:
            module_import = __import__(module_dir, fromlist=['Module'])
        except ImportError as e1:
            self._log_error(
                "Failed to load module {} from {}: {}".format(module_name, module_dir, e1))

            # Remove module dependencies path
            sys.path.remove(module_dependencies_path)

            return False

        Module = getattr(module_import, 'Module')

        # Ensure the module implements the base
        assert issubclass(Module, ModuleBase)

        # Set up a queue so that the module can communicate with the main
        # thread
        q = Queue()  # type: Queue

        # This will (correctly) fail if the module doesn't implement all necessary
        # functionality
        try:
            module_code = Module()
        except TypeError as e2:
            self._log_error(
                "Failed to load module {} from {}: {}".format(module_name, module_dir, e2))
            return False

        # Check if the required functions have enough parameters
        required_param_lengths = {}

        for name, value in getmembers(ModuleBase, isfunction):
            required_param_lengths[name] = len(signature(value).parameters) - 1 # Python is inconsistent with self

        for name, value in getmembers(module_code, ismethod):
            try:
                required_param_length = required_param_lengths[name]
            except KeyError:
                continue

            param_length = len(signature(value).parameters)

            if param_length != required_param_length:
                if name == 'process_response' and param_length == 1:
                    print("WARN: Module {} uses old process_response signature and will not be able to receive an identifier if requested".format(module_name))
                else:
                    self._log_error(
                        "Failed to load module {} from {}: {} function has {} parameters (excluding self), expected {}"
                        .format(module_name, module_dir, name, param_length, required_param_length))
                    return False

        # Prefill API version and locale
        module['settings']['_api_version'] = [0, 1, 0]
        module['settings']['_locale'] = locale

        # Start the module in the background
        module_thread = ModuleThreadInitializer(
            module_name,
            q,
            target=module_code.init,
            args=(module['settings'], q))
        module_thread.start()

        # Add tab
        tab_data = QQmlComponent(window.engine)
        tab_data.loadUrl(
            QUrl.fromLocalFile(AppFile.get_path(os.path.join('qml', 'ModuleData.qml'))))
        window.engine.setContextForObject(tab_data, module_context)
        window.tabs.addTab(module_name, tab_data)

        # Store tab/viewModel combination
        # tabData is not used but stored to prevent segfaults caused by
        # Python garbage collecting it
        window.tab_bindings.append({'init': False,
                                    'queue': q,
                                    'vm': vm,
                                    'module': module_code,
                                    'module_context': module_context,
                                    'module_import': module_import,
                                    'module_name': module_name,
                                    'tab_data': tab_data,
                                    'settings': module['settings'],
                                    'entries_processed': 0})

        # Open tab to trigger loading
        QQmlProperty.write(
            window.tabs, "currentIndex", QQmlProperty.read(window.tabs, "count") - 1)

        return True

    def unload_module(self, window: 'Window', tab_id: int) -> None:
        """Unload a module by tab ID."""
        window.tab_bindings[tab_id]['module'].stop()

        if QQmlProperty.read(window.tabs, "currentIndex") == tab_id:
            tab_count = QQmlProperty.read(window.tabs, "count")
            if tab_id + 1 < tab_count:
                QQmlProperty.write(window.tabs, "currentIndex", tab_id + 1)
            else:
                QQmlProperty.write(window.tabs, "currentIndex", "0")

        del window.tab_bindings[tab_id]
        window.tabs.removeTab(tab_id)

    def list_modules(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Return a list of modules together with their source."""
        modules = {}

        for directory in os.listdir(self.module_dir):
            if not os.path.isdir(os.path.join(self.module_dir, directory)):
                continue

            name = ModuleManager.remove_prefix(directory)
            try:
                source = check_output(
                    ['git', 'config', '--get', 'remote.origin.url'],
                    cwd=os.path.join(
                        self.module_dir, directory),
                    universal_newlines=True).strip()

            except (CalledProcessError, FileNotFoundError):
                source = "Unknown"

            metadata = {'name': 'Unknown',
                        'developer': 'Unknown',
                        'description': 'Unknown',
                        'homepage': 'Unknown',
                        'license': 'Unknown'}

            try:
                with open(os.path.join(self.module_dir, directory, "metadata.json"), 'r') as metadata_json:
                    metadata = json.load(metadata_json)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                print("Module {} lacks a metadata.json file".format(name))

            if not all(key in metadata for key in ['name', 'developer', 'description', 'homepage', 'license']):
                print("Module {} does override all default keys".format(name))

            modules[name] = {"source": source, "metadata": metadata}

        return modules

    def reload_module(self, window: 'Window', tab_id: int) -> bool:
        """Reload a module by tab ID."""
        # Get currently active tab
        current_index = QQmlProperty.read(window.tabs, "currentIndex")

        # Get the needed info to load the module
        module_data = window.tab_bindings[tab_id]
        module = {
            'name': module_data['module_name'],
            'settings': module_data['settings']
        }

        # Unload the module
        self.unload_module(window, tab_id)

        # Force a reload to make code changes happen
        reload(module_data['module_import'])

        # Load it into the UI
        if not self.load_module(window, module, module_data['settings']['_locale']):
            return False

        # Get new position
        new_tab_id = len(window.tab_bindings) - 1

        # Move to correct position if there is more than 1 tab
        if new_tab_id > 0:
            window.tabs.moveTab(new_tab_id, tab_id)
            window.tab_bindings.insert(tab_id, window.tab_bindings.pop(new_tab_id))

            # Focus on active tab
            QQmlProperty.write(window.tabs, "currentIndex", str(current_index))
        else:
            # Ensure the event gets called if there's only one tab
            window.tabs.currentIndexChanged.emit()

        return True

    def install_module(self, url: str, verbose=False, interactive=True) -> bool:
        """Install a module."""
        module_name = url.split("/")[-1]

        dir_name = ModuleManager.add_prefix(module_name).replace('.', '_')
        module_name = ModuleManager.remove_prefix(module_name)

        if os.path.exists(os.path.join(self.module_dir, dir_name)):
            if verbose:
                self._log_error('{} is already installed'.format(module_name))

            return False

        if verbose:
            self._log('Installing {} from {}'.format(module_name, url))

        try:
            git_env = os.environ.copy()
            git_env['GIT_ASKPASS'] = 'true'
            return_code = Popen(['git', 'clone', url, dir_name],
                                cwd=self.module_dir,
                                env=git_env if not interactive else None).wait()
        except Exception as e:
            self._log_error('Failed to download {}: {}'.format(module_name, e))

            return False

        if return_code != 0:
            if verbose:
                self._log_error('Failed to install {}'.format(module_name))

            try:
                rmtree(os.path.join(self.module_dir, dir_name))
            except FileNotFoundError:
                pass

            return False

        if verbose:
            self._log('Installing dependencies for {}'.format(module_name))

        pip_exit_code = self._pip_install(dir_name)
        if pip_exit_code != 0:
            if verbose:
                self._log_error('Failed to install dependencies for {}, error {}'.format(module_name, pip_exit_code))

            try:
                rmtree(os.path.join(self.module_dir, dir_name))
            except FileNotFoundError:
                pass

            try:
                rmtree(os.path.join(self.module_dependencies_dir, dir_name))
            except FileNotFoundError:
                pass

            return False

        if verbose:
            self._log('Installed {}'.format(module_name))

        return True

    def uninstall_module(self, module_name: str, verbose=False) -> bool:
        """Uninstall a module."""
        dir_name = ModuleManager.add_prefix(module_name)
        module_name = ModuleManager.remove_prefix(module_name)

        if verbose:
            self._log('Uninstalling {}'.format(module_name))

        try:
            rmtree(os.path.join(self.module_dir, dir_name))
        except FileNotFoundError:
            if verbose:
                self._log_error(
                    'Cannot uninstall {}, it is not installed'.format(module_name))

            return False

        try:
            rmtree(os.path.join(self.module_dependencies_dir, dir_name))
        except FileNotFoundError:
            pass

        if verbose:
            self._log('Uninstalled {}'.format(module_name))

        return True

    def update_module(self, module_name: str, verbose=False) -> bool:
        """Update a module."""
        dir_name = ModuleManager.add_prefix(module_name)
        module_name = ModuleManager.remove_prefix(module_name)

        if verbose:
            self._log('Updating {}'.format(module_name))

        try:
            check_call(
                ['git', 'pull'], cwd=os.path.join(self.module_dir, dir_name))
        except Exception as e:
            if verbose:
                self._log_error(
                    'Failed to update {}: {}'.format(module_name, e))

            return False

        if verbose:
            self._log('Updating dependencies for {}'.format(module_name))

        pip_exit_code = self._pip_install(dir_name)
        if pip_exit_code != 0:
            if verbose:
                self._log_error('Failed to update dependencies for {}, error {}'.format(module_name, pip_exit_code))

            return False

        if verbose:
            self._log('Updated {}'.format(module_name))

        return True

    def update_all_modules(self, verbose=False) -> None:
        """Update all modules."""
        for module in self.list_modules().keys():
            self.update_module(module, verbose=verbose)


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
            self.queue.put(
                [Action.critical_error, "Exception thrown: {}".format(e)])


class ViewModel():
    """Manage the communication between user interface and module."""

    def __init__(self) -> None:
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self.command_list = []  # type: List
        self.entry_list = []  # type: List
        self.filtered_entry_list = []  # type: List
        self.filtered_command_list = []  # type: List
        self.result_list_model_list = QStringListModel()
        self.result_list_model_max_index = -1
        self.result_list_model_command_mode = False
        self.selection = []  # type: List[Dict[SelectionType, str]]
        self.last_search = ""

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

    def bind_context(self, queue: Queue, context: QQmlContext, window: 'Window', search_input_model: QObject,
                     header_text: QObject, result_list_model: QObject) -> None:
        """Bind the QML context so we can communicate with the QML front-end."""
        self.queue = queue
        self.context = context
        self.window = window
        self.search_input_model = search_input_model
        self.header_text = header_text
        self.result_list_model = result_list_model

    def bind_module(self, module: ModuleBase) -> None:
        """Bind the module.

        This ensures we can call functions in it.
        """
        self.module = module

    def go_up(self) -> None:
        """Go one level up.

        This means that, if we're currently in the entry content list, we go
        back to the entry list. If we're currently in the entry list, we clear
        the search bar. If we're currently in the entry list and the search bar
        is empty, we tell the window to hide/close itself.
        """
        if QQmlProperty.read(self.search_input_model, "text") != "":
            QQmlProperty.write(self.search_input_model, "text", "")
            return

        if len(self.selection) > 0:
            self.selection.pop()
            self.entry_list = []
            self.command_list = []

            self.context.setContextProperty(
                "resultListModelDepth", len(self.selection))

            self.module.selection_made(self.selection)
        else:
            self.window.close()

    def search(self, new_entries=False) -> None:
        """Filter the entry list.

        Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        search_string = QQmlProperty.read(self.search_input_model, "text").lower()

        # Don't search if nothing changed
        if not new_entries and search_string == self.last_search:
            return

        # If empty, show all
        if len(search_string) == 0 and not new_entries:
            self.filtered_entry_list = self.entry_list
            self.filtered_command_list = self.command_list
            combined_list = self.entry_list + self.command_list
            self.result_list_model_list = QStringListModel(
                [str(entry) for entry in combined_list])
            self.result_list_model_max_index = len(self.entry_list) - 1
            self.context.setContextProperty(
                "resultListModelCommandMode", False)
            self.context.setContextProperty(
                "resultListModelMaxIndex", self.result_list_model_max_index)
            self.context.setContextProperty(
                "resultListModel", self.result_list_model_list)

            # Enable checking for changes next time
            self.last_search = search_string

            return

        search_strings = search_string.split(" ")

        # If longer and no new entries, only filter existing list
        if len(search_string) > len(self.last_search) and not (self.result_list_model_command_mode and
                                                               len(search_strings) == 2 and search_strings[1] == ""):

            filter_entry_list = self.filtered_entry_list
            filter_command_list = self.filtered_command_list
        else:
            filter_entry_list = self.entry_list
            filter_command_list = self.command_list

        self.filtered_entry_list = []
        self.filtered_command_list = []

        self.result_list_model_command_mode = False

        for command in filter_command_list:
            if search_strings[0] in command:
                if search_strings[0] == command.split(" ", 1)[0]:
                    self.result_list_model_command_mode = True

                self.filtered_command_list.append(command)

        if self.result_list_model_command_mode:
            for entry in filter_entry_list:
                if all(search_string in str(entry).lower() for search_string in search_strings[1:]):
                    self.filtered_entry_list.append(entry)

            combined_list = self.filtered_command_list + self.filtered_entry_list
        else:
            for entry in filter_entry_list:
                if all(search_string in str(entry).lower() for search_string in search_strings):
                    self.filtered_entry_list.append(entry)

            combined_list = self.filtered_entry_list + self.filtered_command_list

        self.context.setContextProperty(
            "resultListModelCommandMode", self.result_list_model_command_mode)

        self.result_list_model_max_index = len(self.filtered_entry_list) - 1
        self.context.setContextProperty(
            "resultListModelMaxIndex", self.result_list_model_max_index)

        self.result_list_model_list = QStringListModel(
            [str(entry) for entry in combined_list])
        self.context.setContextProperty(
            "resultListModel", self.result_list_model_list)

        # Enable checking for changes next time
        self.last_search = search_string

    def select(self) -> None:
        """Notify the module of our selection entry."""
        if len(self.filtered_entry_list + self.filtered_command_list) == 0 or self.queue.qsize() > 0:
            return

        self.entry_list = []
        self.command_list = []

        current_index = QQmlProperty.read(self.result_list_model, "currentIndex")

        if self.result_list_model_command_mode or len(self.filtered_entry_list) == 0:
            if self.result_list_model_command_mode:
                selected_command = self.filtered_command_list[current_index]
            else:
                selected_command = self.filtered_command_list[current_index - len(self.filtered_entry_list)]

            selected_command_split = selected_command.split(" ", 1)
            command_typed = QQmlProperty.read(self.search_input_model, "text")
            command_typed_split = command_typed.split(" ", 1)

            try:
                command_typed = selected_command_split[0] + " " + command_typed_split[1]
            except IndexError:
                command_typed = selected_command_split[0]

            self.selection.append(
                {'type': SelectionType.command, 'value': command_typed})

            self.context.setContextProperty(
                "resultListModelDepth", len(self.selection))

            self.module.selection_made(self.selection)

            QQmlProperty.write(self.search_input_model, "text", "")

            return

        if current_index >= len(self.filtered_entry_list):
            entry = self.filtered_command_list[current_index - len(self.filtered_entry_list)]
            self.selection.append({'type': SelectionType.command, 'value': entry})
        else:
            entry = self.filtered_entry_list[current_index]
            self.selection.append({'type': SelectionType.entry, 'value': entry})

        self.context.setContextProperty(
            "resultListModelDepth", len(self.selection))

        self.module.selection_made(self.selection)

        QQmlProperty.write(self.search_input_model, "text", "")

    def set_header(self, content) -> None:
        """Set the header text."""
        QQmlProperty.write(self.header_text, "text", str(content))

    def tab_complete(self) -> None:
        """Tab-complete based on the current seach input.

        This tab-completes the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        current_input = QQmlProperty.read(self.search_input_model, "text")

        start = current_input

        possibles = current_input.split(" ", 1)
        command = self._get_longest_common_string(
            [command.split(" ", 1)[0] for command in self.command_list],
            start=possibles[0])
        # If we didn't complete the command, see if we can complete the text
        if command is None or len(command) == len(possibles[0]):
            if command is None:
                command = ""  # We string concat this later
            else:
                command += " "

            start = possibles[1] if len(possibles) > 1 else ""
            entry = self._get_longest_common_string([list_entry for list_entry in self.filtered_entry_list
                                                     if list_entry not in self.command_list],
                                                    start=start)

            if entry is None or len(entry) <= len(start):
                self.queue.put(
                    [Action.add_error, "No tab completion possible"])
                return
        else:
            entry = " "  # Add an extra space to simplify typing for the user

        QQmlProperty.write(self.search_input_model, "text", command + entry)
        self.search()


class Window(QMainWindow):
    """The main Pext window."""

    def __init__(self, settings: Dict, config_retriever: ConfigRetriever, parent=None) -> None:
        """Initialize the window."""
        super().__init__(parent)

        # Save settings
        self.config_retriever = config_retriever
        self.settings = settings

        self.tab_bindings = []  # type: List[Dict]

        self.engine = QQmlApplicationEngine(self)

        self.context = self.engine.rootContext()
        self.context.setContextProperty(
            "applicationVersion", VersionRetriever.get_version())
        self.context.setContextProperty(
            "modulesPath", os.path.join(self.config_retriever.get_setting('config_path'), 'modules'))

        # Load the main UI
        self.engine.load(QUrl.fromLocalFile(AppFile.get_path(os.path.join('qml', 'main.qml'))))

        self.window = self.engine.rootObjects()[0]

        # Give QML the module info
        self.intro_screen = self.window.findChild(QObject, "introScreen")
        self.module_manager = ModuleManager(self.config_retriever)
        self._update_modules_info_qml()

        # Bind global shortcuts
        self.search_input_model = self.window.findChild(
            QObject, "searchInputModel")
        escape_shortcut = self.window.findChild(QObject, "escapeShortcut")
        back_button = self.window.findChild(QObject, "backButton")
        tab_shortcut = self.window.findChild(QObject, "tabShortcut")

        self.search_input_model.textChanged.connect(self._search)
        self.search_input_model.accepted.connect(self._select)
        escape_shortcut.activated.connect(self._go_up)
        back_button.clicked.connect(self._go_up)
        tab_shortcut.activated.connect(self._tab_complete)

        # Bind menu entries
        menu_reload_active_module_shortcut = self.window.findChild(
            QObject, "menuReloadActiveModule")
        menu_load_module_shortcut = self.window.findChild(
            QObject, "menuLoadModule")
        menu_close_active_module_shortcut = self.window.findChild(
            QObject, "menuCloseActiveModule")
        menu_install_module_shortcut = self.window.findChild(
            QObject, "menuInstallModule")
        menu_manage_modules_shortcut = self.window.findChild(
            QObject, "menuManageModules")
        menu_update_all_modules_shortcut = self.window.findChild(
            QObject, "menuUpdateAllModules")
        menu_quit_shortcut = self.window.findChild(QObject, "menuQuit")
        menu_quit_without_saving_shortcut = self.window.findChild(
            QObject, "menuQuitWithoutSaving")
        menu_homepage_shortcut = self.window.findChild(QObject, "menuHomepage")

        menu_reload_active_module_shortcut.triggered.connect(
            self._reload_active_module)
        menu_load_module_shortcut.loadRequest.connect(self._open_tab)
        menu_close_active_module_shortcut.triggered.connect(self._close_tab)
        menu_install_module_shortcut.installRequest.connect(
            self._menu_install_module)
        menu_manage_modules_shortcut.uninstallRequest.connect(
            self._menu_uninstall_module)
        menu_manage_modules_shortcut.updateRequest.connect(self._menu_update_module)
        menu_update_all_modules_shortcut.updateAllRequest.connect(
            self._menu_update_all_modules)
        menu_quit_shortcut.triggered.connect(self.quit)
        menu_quit_without_saving_shortcut.triggered.connect(
            self.quit_without_saving)
        menu_homepage_shortcut.triggered.connect(self._show_homepage)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self._bind_context)

        # Show the window
        self.show()

    def _bind_context(self) -> None:
        """Bind the context for the module."""
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        element = self.tab_bindings[current_tab]

        # Only initialize once, ensure filter is applied
        if element['init']:
            element['vm'].search(new_entries=True)
            return

        # Get the header
        header_text = self.tabs.getTab(
            current_tab).findChild(QObject, "headerText")

        # Get the list
        result_list_model = self.tabs.getTab(
            current_tab).findChild(QObject, "resultListModel")

        # Enable mouse selection support
        result_list_model.entryClicked.connect(element['vm'].select)

        # Bind it to the viewmodel
        element['vm'].bind_context(element['queue'],
                                   element['module_context'],
                                   self,
                                   self.search_input_model,
                                   header_text,
                                   result_list_model)

        element['vm'].bind_module(element['module'])

        # Done initializing
        element['init'] = True

    def _get_current_element(self) -> Optional[Dict]:
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        try:
            return self.tab_bindings[current_tab]
        except IndexError:
            # No tabs
            return None

    def _go_up(self) -> None:
        try:
            self._get_current_element()['vm'].go_up()
        except TypeError:
            pass

    def _open_tab(self, name: str, settings: str) -> None:
        module_settings = {}
        for setting in settings.split(" "):
            try:
                key, value = setting.split("=", 2)
            except ValueError:
                continue

            module_settings[key] = value

        module = {'name': name, 'settings': module_settings}
        self.module_manager.load_module(self, module, self.settings['locale'])
        # First module? Enforce load
        if len(self.tab_bindings) == 1:
            self.tabs.currentIndexChanged.emit()

    def _close_tab(self) -> None:
        if len(self.tab_bindings) > 0:
            self.module_manager.unload_module(
                self,
                QQmlProperty.read(self.tabs, "currentIndex"))

    def _reload_active_module(self) -> None:
        if len(self.tab_bindings) > 0:
            self.module_manager.reload_module(
                self,
                QQmlProperty.read(self.tabs, "currentIndex"))

    def _menu_install_module(self, module_url: str) -> None:
        functions = [
            {
                'name': self.module_manager.install_module,
                'args': (module_url),
                'kwargs': {'interactive': False, 'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_uninstall_module(self, module_name: str) -> None:
        functions = [
            {
                'name': self.module_manager.uninstall_module,
                'args': (module_name),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_module(self, module_name: str) -> None:
        functions = [
            {
                'name': self.module_manager.update_module,
                'args': (module_name),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_all_modules(self) -> None:
        functions = [
            {
                'name': self.module_manager.update_all_modules,
                'args': (),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _search(self) -> None:
        try:
            self._get_current_element()['vm'].search()
        except TypeError:
            pass

    def _select(self) -> None:
        try:
            self._get_current_element()['vm'].select()
        except TypeError:
            pass

    def _tab_complete(self) -> None:
        try:
            self._get_current_element()['vm'].tab_complete()
        except TypeError:
            pass

    def _update_modules_info_qml(self) -> None:
        modules = self.module_manager.list_modules()
        self.context.setContextProperty(
            "modules", modules)
        QQmlProperty.write(
            self.intro_screen, "modulesInstalledCount", len(modules.keys()))

    def _show_homepage(self) -> None:
        webbrowser.open('https://pext.hackerchick.me/')

    def bind_logger(self, logger: 'Logger') -> None:
        """Bind the logger to the window and further initialize the module."""
        self.module_manager.bind_logger(logger)

        # Now that the logger is bound, we can show messages in the window, so
        # start binding the modules
        if len(self.settings['modules']) > 0:
            for module in self.settings['modules']:
                self.module_manager.load_module(self, module, self.settings['locale'])
        else:
            for module in ProfileManager(self.config_retriever).retrieve_modules(self.settings['profile']):
                self.module_manager.load_module(self, module, self.settings['locale'])

        # If there's only one module passed through the command line, enforce
        # loading it now. Otherwise, switch back to the first module in the
        # list
        if len(self.tab_bindings) == 1:
            self.tabs.currentIndexChanged.emit()
        elif len(self.tab_bindings) > 1:
            QQmlProperty.write(self.tabs, "currentIndex", "0")

    def close(self) -> None:
        """Close the window."""
        self.window.hide()

        need_search = False

        if QQmlProperty.read(self.search_input_model, "text") != "":
            need_search = True
            QQmlProperty.write(self.search_input_model, "text", "")

        for tab in self.tab_bindings:
            if not tab['init']:
                continue

            tab_needs_search = need_search or len(tab['vm'].selection) > 0

            if len(tab['vm'].selection) > 0:
                tab['vm'].selection = []

                tab['vm'].context.setContextProperty(
                    "resultListModelDepth", len(tab['vm'].selection))

                tab['vm'].module.selection_made(tab['vm'].selection)

            if tab_needs_search:
                tab['vm'].search()

    def show(self) -> None:
        """Show the window."""
        self.window.show()
        self.activateWindow()

    def toggle_visibility(self) -> None:
        """Toggle window visibility."""
        if self.window.isVisible():
            self.close()
        else:
            self.show()

    def quit(self) -> None:
        """Quit."""
        sys.exit(0)

    def quit_without_saving(self) -> None:
        """Quit without saving."""
        self.settings['save_settings'] = False
        self.quit()


class SignalHandler():
    """Handle UNIX signals."""

    def __init__(self, window: Window) -> None:
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum: int, frame) -> None:
        """When an UNIX signal gets received, show the window."""
        self.window.show()


class Tray():
    """Handle the system tray."""

    def __init__(self, window: Window, app_icon: str, profile: str) -> None:
        """Initialize the system tray."""
        self.window = window

        self.tray = QSystemTrayIcon(app_icon)
        tray_menu = QMenu()

        tray_menu_open = QAction("Toggle visibility", tray_menu)
        tray_menu_open.triggered.connect(window.toggle_visibility)
        tray_menu.addAction(tray_menu_open)

        tray_menu.addSeparator()

        tray_menu_quit = QAction("Quit", tray_menu)
        tray_menu_quit.triggered.connect(window.quit)
        tray_menu.addAction(tray_menu_quit)
        tray_menu_quit_without_saving = QAction("Quit without saving", tray_menu)
        tray_menu_quit_without_saving.triggered.connect(window.quit_without_saving)
        tray_menu.addAction(tray_menu_quit_without_saving)

        self.tray.activated.connect(self.icon_clicked)
        self.tray.setContextMenu(tray_menu)
        self.tray.setToolTip('Pext ({})'.format(profile))
        self.tray.show()

    def icon_clicked(self, reason: int) -> None:
        """React to a click event."""
        # Only show the window on a left click
        if platform.system() != "Darwin":
            if reason == 3:
                self.window.toggle_visibility()


def _init_persist(profile: str) -> str:
    """Open Pext if an instance is already running.

    Checks if Pext is already running and if so, send it SIGUSR1 to bring it
    to the foreground. If Pext is not already running, saves a PIDfile so that
    another Pext instance can find us.
    """
    pidfile = '/tmp/pext_{}.pid'.format(profile)

    if os.path.isfile(pidfile):
        # Notify the main process
        try:
            os.kill(int(open(pidfile, 'r').read()), signal.SIGUSR1)
            sys.exit(0)
        except ProcessLookupError:
            # Pext closed, but did not clean up its pidfile
            pass

    # We are the only instance, claim our pidfile
    pid = str(os.getpid())
    open(pidfile, 'w').write(pid)

    # Return the filename to delete it later
    return pidfile


def _load_settings(argv: List[str], config_retriever: ConfigRetriever) -> Dict:
    """Load the settings from the command line and set defaults."""
    # Default options
    settings = {'clipboard': 'clipboard',
                'locale': QLocale.system().name(),
                'modules': [],
                'profile': 'default',
                'save_settings': True,
                'tray': True}

    # getopt requires all possible options to be listed, but we do not know
    # more about module-specific options in advance than that they start with
    # module-. Therefore, we go through the argument list and create a new
    # list filled with every entry that starts with module- so that getopt
    # doesn't raise getoptError for these entries.
    module_opts = []
    for arg in argv:
        arg = arg.split("=")[0]
        if arg.startswith("--module-"):
            module_opts.append(arg[2:] + "=")

    try:
        opts, _ = getopt.getopt(argv, "hc:m:p:", ["help",
                                                  "version",
                                                  "exit",
                                                  "locale=",
                                                  "list-styles",
                                                  "style=",
                                                  "clipboard=",
                                                  "module=",
                                                  "install-module=",
                                                  "uninstall-module=",
                                                  "update-module=",
                                                  "update-modules",
                                                  "list-modules",
                                                  "profile=",
                                                  "create-profile=",
                                                  "remove-profile=",
                                                  "list-profiles",
                                                  "no-tray"] + module_opts)

    except getopt.GetoptError as err:
        print("{}\n".format(err))
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        elif opt == "--version":
            print("Pext {}".format(VersionRetriever.get_version()))
        elif opt == "--exit":
            sys.exit(0)
        elif opt == "--locale":
            settings['locale'] = arg
        elif opt == "--list-styles":
            for style in QStyleFactory().keys():
                print(style)
        elif opt == "--style":
            if arg in QStyleFactory().keys():
                settings['style'] = arg
            else:
                # PyQt5 does not have bindings for QQuickStyle yet
                os.environ["QT_QUICK_CONTROLS_STYLE"] = arg
        elif opt in ("-b", "--binary"):
            settings['binary'] = arg
        elif opt in ("-c", "--clipboard"):
            if arg not in ["clipboard", "selection"]:
                print("Invalid clipboard requested")
                sys.exit(2)

            settings['clipboard'] = arg
        elif opt in ("-m", "--module"):
            if not arg.startswith('pext_module_'):
                arg = 'pext_module_' + arg

            settings['modules'].append({'name': arg, 'settings': {}})  # type: ignore
        elif opt.startswith("--module-"):
            settings['modules'][-1]['settings'][opt[9:]] = arg  # type: ignore
        elif opt == "--install-module":
            ModuleManager(config_retriever).install_module(arg, verbose=True)
        elif opt == "--uninstall-module":
            ModuleManager(config_retriever).uninstall_module(arg, verbose=True)
        elif opt == "--update-module":
            ModuleManager(config_retriever).update_module(arg, verbose=True)
        elif opt == "--update-modules":
            ModuleManager(config_retriever).update_all_modules(verbose=True)
        elif opt == "--list-modules":
            for module_name, module_data in ModuleManager(config_retriever).list_modules().items():
                print('{} ({})'.format(module_name, module_data['source']))
        elif opt == "--profile":
            settings['profile'] = arg
            # Create directory for profile if not existant
            try:
                ProfileManager(config_retriever).create_profile(arg)
            except OSError:
                pass
        elif opt == "--create-profile":
            ProfileManager(config_retriever).create_profile(arg)
        elif opt == "--remove-profile":
            ProfileManager(config_retriever).remove_profile(arg)
        elif opt == "--list-profiles":
            for profile in ProfileManager(config_retriever).list_profiles():
                print(profile)
        elif opt == "--no-tray":
            settings['tray'] = False

    return settings


def _shut_down(pidfile: str, profile: str, window: Window, config_retriever: ConfigRetriever) -> None:
    """Clean up."""
    for module in window.tab_bindings:
        module['module'].stop()

    os.unlink(pidfile)
    if window.settings['save_settings']:
        ProfileManager(config_retriever).save_modules(profile, window.tab_bindings)


def usage() -> None:
    """Print usage information."""
    print('''Options:

--clipboard        : choose the clipboard to copy entries to. Acceptable values
                     are "clipboard" for the global system clipboard and
                     "selection" for the global mouse selection.

--help             : show this screen.

--locale           : load Pext with the given locale.

--style            : sets a certain Qt system style for the UI.

--list-styles      : print a list of loadable Qt system styles. Due to PyQt5
                     limitations, loadable QtQuick styles cannot currently be
                     listed.

--install-module   : download and install a module from the given git URL.

--list-modules     : list all installed modules.

--module           : name the module to use. This option may be given multiple
                     times to use multiple modules. When this option is given,
                     the profile module list will be overwritten.

--module-*         : set a module setting for the most recently given module.
                     For example, to set a module-specific setting called
                     binary, use --module-binary=value. Check the module
                     documentation for the supported module-specific settings.

--uninstall-module : uninstall a module by name.

--update-module    : update a module by name.

--update-modules   : update all installed modules.

--profile          : use a specific profile, creating it if it doesn't exist
                     yet. Defaults to "default", use "none" to not save the
                     application state between runs.

--create-profile   : create a new blank profile for later use.

--remove-profile   : remove a profile.

--list-profiles    : list all profiles.

--no-tray          : do not create a tray icon.

--version          : show the current version.

--exit             : exit upon reaching this argument, useful to retrieve
                     information without starting the Pext GUI.''')


def main() -> None:
    """Start the application."""
    # Load configuration
    config_retriever = ConfigRetriever()

    # Ensure our necessary directories exist
    for directory in ['modules', 'module_dependencies', 'profiles', 'profiles/default']:
        try:
            os.makedirs(os.path.join(config_retriever.get_setting('config_path'), directory))
        except OSError:
            # Probably already exists, that's okay
            pass

    settings = _load_settings(sys.argv[1:], config_retriever)

    # Set up persistence
    pidfile = _init_persist(settings['profile'])

    # Load the app icon
    app_icon = QIcon(AppFile.get_path(os.path.join('images', 'scalable', 'pext.svg')))

    # Set up the app
    app = QApplication(['Pext ({})'.format(settings['profile'])])

    translator = QTranslator()
    print('Using locale: {}'.format(settings['locale']))
    print('Localization loaded: ',
        translator.load('pext_' + settings['locale'] + '.qm', os.path.join(AppFile.get_path('i18n'))))

    app.installTranslator(translator)

    app.setWindowIcon(app_icon)
    if 'style' in settings:
        app.setStyle(QStyleFactory().create(settings['style']))

    # Check if clipboard is supported
    if settings['clipboard'] == 'selection' and not app.clipboard().supportsSelection():
        print("Requested clipboard type is not supported")
        sys.exit(3)

    # Get a window
    window = Window(settings, config_retriever)

    # Get a logger
    logger = Logger(window)

    # Give the window a reference to the logger
    window.bind_logger(logger)

    # Clean up on exit
    atexit.register(_shut_down, pidfile, settings['profile'], window, config_retriever)

    # Handle SIGUSR1 UNIX signal
    signal_handler = SignalHandler(window)
    signal.signal(signal.SIGUSR1, signal_handler.handle)

    # Create a main loop
    main_loop = MainLoop(app, window, settings, logger)

    # Create a tray icon
    # This needs to be stored in a variable to prevent the Python garbage collector from removing the Qt tray
    if settings['tray']:
        tray = Tray(window, app_icon, settings['profile'])  # noqa: F841

    # And run...
    main_loop.run()


if __name__ == "__main__":
    main()
