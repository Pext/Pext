#!/usr/bin/env python3

# Copyright (c) 2015 - 2019 Sylvia van Os <sylvia@hackerchick.me>
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
import webbrowser
import tempfile
import psutil

from datetime import datetime
from distutils.util import strtobool
from enum import IntEnum
from functools import partial
from importlib import reload  # type: ignore
from inspect import getmembers, isfunction, ismethod, signature
from pkg_resources import parse_version
from shutil import copytree, rmtree
from subprocess import check_output, CalledProcessError, Popen
try:
    from typing import Any, Callable, Dict, List, Optional, Set, Union
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional, Set, Union  # type: ignore  # noqa: F401
from urllib.parse import quote_plus
from queue import Queue, Empty

import requests

from dulwich import client, porcelain
from dulwich.repo import Repo
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor

from PyQt5.QtCore import QStringListModel, QLocale, QTranslator, Qt
from PyQt5.QtWidgets import QApplication, QAction, QMenu, QStyleFactory, QSystemTrayIcon
from PyQt5.Qt import QClipboard, QIcon, QObject, QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlProperty, QUrl
from PyQt5.QtGui import QPalette, QColor, QWindow
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

client.get_ssh_vendor = ParamikoSSHVendor
pyautogui_error = None
if platform.system() == 'Darwin':
    # https://github.com/moses-palmer/pynput/issues/83#issuecomment-410264758
    try:
        from pyautogui import hotkey, typewrite
    except Exception:
        pyautogui_error = traceback.format_exc()
        traceback.print_exc()

pynput_error = None
try:
    from pynput import keyboard
except Exception:
    pynput_error = traceback.format_exc()
    traceback.print_exc()

# FIXME: Workaround for https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826
warn_no_openGL_linux = False
if platform.system() == "Linux":
    try:
        from OpenGL import GL  # NOQA
    except ImportError:
        warn_no_openGL_linux = True
    except Exception as e:
        print('Could not import OpenGL module: {}'.format(e))
        traceback.print_exc()

# Windows doesn't support getuid
if platform.system() == 'Windows':
    import getpass  # NOQA


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
from pext_helpers import Action, SelectionType  # noqa: E402

from constants import USE_INTERNAL_UPDATER  # noqa: E402


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
    def bind(window: 'Window', module_manager: 'ModuleManager', theme_manager: 'ThemeManager') -> None:
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

        for tab_id, tab in enumerate(InternalCallProcessor.window.tab_bindings):
            if tab['metadata']['id'] == arguments[0]:
                module_data = InternalCallProcessor.module_manager.reload_step_unload(
                    InternalCallProcessor.window,
                    tab_id
                )
                InternalCallProcessor.temp_module_datas.append(module_data)
                functions.append({
                    'name': InternalCallProcessor.enqueue,
                    'args': ("pext:finalize-module:{}:{}".format(
                        tab_id, len(InternalCallProcessor.temp_module_datas) - 1),),
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
            InternalCallProcessor.window,
            int(arguments[0]),
            InternalCallProcessor.temp_module_datas[int(arguments[1])]
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
    status_text = None  # type: QObject

    @staticmethod
    def bind_window(window: 'Window') -> None:
        """Give the logger the ability to log info to the main window."""
        Logger.window = window
        Logger.status_text = window.window.findChild(QObject, "statusText")

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
                if tab['metadata']['id'] == identifier:
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
                    quote_plus(detailed_message)
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
                QQmlProperty.write(Logger.status_text, "text", "")
                Logger.last_update = None
        else:
            message = Logger.queued_messages.pop(0)

            if message['type'] == 'error':
                statusbar_message = "<font color='red'>⚠ {}</color>".format(message['message'])
                icon = QSystemTrayIcon.Warning
            else:
                statusbar_message = message['message']
                icon = QSystemTrayIcon.Information

            QQmlProperty.write(Logger.status_text, "text", statusbar_message)

            if Logger.window.tray:
                Logger.window.tray.tray.showMessage('Pext', message['message'], icon)

            Logger.last_update = current_time


class PextFileSystemEventHandler(FileSystemEventHandler):
    """Watches the file system to ensure state changes when relevant."""

    def __init__(self, window: 'Window', modules_path: str):
        """Initialize filesystem event handler."""
        self.window = window
        self.modules_path = modules_path

    def on_deleted(self, event):
        """Unload modules on deletion."""
        if not event.is_directory:
            return

        if event.src_path.startswith(self.modules_path):
            for tab_id, tab in enumerate(self.window.tab_bindings):
                if event.src_path == os.path.join(self.modules_path, tab['metadata']['id'].replace('.', '_')):
                    print("Module {} was removed, sending unload event".format(tab['metadata']['id']))
                    self.window.module_manager.unload(self.window, tab_id)


class Translation():
    """Retrieves translations for Python code.

    This works by reading values from QML.
    """

    __window = None

    @staticmethod
    def bind_window(window: 'Window') -> None:
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

    def __init__(self, app: QApplication, window: 'Window', main_loop_queue: Queue) -> None:
        """Initialize the main loop."""
        self.app = app
        self.window = window
        self.main_loop_queue = main_loop_queue

    def _process_tab_action(self, tab: Dict, active_tab: int) -> None:
        action = tab['queue'].get_nowait()

        if action[0] == Action.critical_error:
            # Stop the module
            tab_id = self.window.tab_bindings.index(tab)
            self.window.module_manager.stop(self.window, tab_id)

            # Disable with reason: crash
            self.window.disable_module(tab_id, 1)

            if len(action) > 2:
                self.window.update_state(tab_id, action[2])

            # Log critical error
            Logger.log_critical(
                tab['metadata']['name'],
                str(action[1]),
                str(action[2]) if len(action) > 2 else None,
                tab['metadata']
            )
        elif action[0] == Action.add_message:
            Logger.log(tab['metadata']['name'], str(action[1]))

        elif action[0] == Action.add_error:
            Logger.log_error(tab['metadata']['name'], str(action[1]))

        elif action[0] == Action.add_entry:
            tab['vm'].entry_list = tab['vm'].entry_list + [action[1]]

        elif action[0] == Action.prepend_entry:
            tab['vm'].entry_list = [action[1]] + tab['vm'].entry_list

        elif action[0] == Action.remove_entry:
            tab['vm'].entry_list.remove(action[1])

        elif action[0] == Action.replace_entry_list:
            if len(action) > 1:
                tab['vm'].entry_list = action[1]
            else:
                tab['vm'].entry_list = []

        elif action[0] == Action.add_command:
            tab['vm'].command_list = tab['vm'].command_list + [action[1]]

        elif action[0] == Action.prepend_command:
            tab['vm'].command_list = [action[1]] + tab['vm'].command_list

        elif action[0] == Action.remove_command:
            tab['vm'].command_list.remove(action[1])

        elif action[0] == Action.replace_command_list:
            if len(action) > 1:
                tab['vm'].command_list = action[1]
            else:
                tab['vm'].command_list = []

        elif action[0] == Action.set_header:
            if len(action) > 1:
                tab['vm'].set_header(str(action[1]))
            else:
                tab['vm'].set_header("")

        elif action[0] == Action.set_filter:
            if len(action) > 1:
                QQmlProperty.write(tab['vm'].search_input_model, "text", str(action[1]))
            else:
                QQmlProperty.write(tab['vm'].search_input_model, "text", "")

        elif action[0] in [Action.ask_question, Action.ask_question_default_yes, Action.ask_question_default_no]:
            question_dialog = self.window.window.findChild(QObject, "questionDialog")
            # Disconnect possibly existing handlers
            try:
                question_dialog.questionAccepted.disconnect()
            except TypeError:
                pass
            try:
                question_dialog.questionRejected.disconnect()
            except TypeError:
                pass

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                question_dialog.questionAccepted.connect(partial(
                    lambda arg: tab['vm'].module.process_response(True, arg),
                    arg=(action[2] if len(action) > 2 else None)))
                question_dialog.questionRejected.connect(partial(
                    lambda arg: tab['vm'].module.process_response(False, arg),
                    arg=(action[2] if len(action) > 2 else None)))
            else:
                question_dialog.questionAccepted.connect(
                    lambda: tab['vm'].module.process_response(True))
                question_dialog.questionRejected.connect(
                    lambda: tab['vm'].module.process_response(False))

            question_dialog.showQuestionDialog.emit(tab['metadata']['name'], action[1])

        elif action[0] == Action.ask_choice:
            choice_dialog = self.window.window.findChild(QObject, "choiceDialog")
            # Disconnect possibly existing handlers
            try:
                choice_dialog.choiceAccepted.disconnect()
            except TypeError:
                pass
            try:
                choice_dialog.choiceRejected.disconnect()
            except TypeError:
                pass

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                choice_dialog.choiceAccepted.connect(partial(
                    lambda userinput, arg: tab['vm'].module.process_response(userinput, arg),
                    arg=(action[3] if len(action) > 3 else None)))
                choice_dialog.choiceRejected.connect(partial(
                    lambda arg: tab['vm'].module.process_response(None, arg),
                    arg=(action[3] if len(action) > 3 else None)))
            else:
                choice_dialog.choiceAccepted.connect(
                    lambda userinput: tab['vm'].module.process_response(userinput))
                choice_dialog.choiceRejected.connect(
                    lambda: tab['vm'].module.process_response(None))

            choice_dialog.showChoiceDialog.emit(tab['metadata']['name'], action[1], action[2])

        elif action[0] == Action.ask_input:
            input_request = self.window.window.findChild(QObject, "inputRequests")
            # Disconnect possibly existing handlers
            try:
                input_request.inputRequestAccepted.disconnect()
            except TypeError:
                pass
            try:
                input_request.inputRequestRejected.disconnect()
            except TypeError:
                pass

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                input_request.inputRequestAccepted.connect(partial(
                    lambda userinput, arg: tab['vm'].module.process_response(userinput, arg),
                    arg=(action[3] if len(action) > 3 else None)))
                input_request.inputRequestRejected.connect(partial(
                    lambda arg: tab['vm'].module.process_response(None, arg),
                    arg=(action[3] if len(action) > 3 else None)))
            else:
                input_request.inputRequestAccepted.connect(
                    lambda userinput: tab['vm'].module.process_response(userinput))
                input_request.inputRequestRejected.connect(
                    lambda: tab['vm'].module.process_response(None))

            input_request.inputRequest.emit(tab['metadata']['name'], action[1], False, False,
                                            action[2] if len(action) > 2 else "")

        elif action[0] == Action.ask_input_password:
            input_request = self.window.window.findChild(QObject, "inputRequests")
            # Disconnect possibly existing handlers
            try:
                input_request.inputRequestAccepted.disconnect()
            except TypeError:
                pass
            try:
                input_request.inputRequestRejected.disconnect()
            except TypeError:
                pass

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                input_request.inputRequestAccepted.connect(partial(
                    lambda userinput, arg: tab['vm'].module.process_response(userinput, arg),
                    arg=(action[3] if len(action) > 3 else None)))
                input_request.inputRequestRejected.connect(partial(
                    lambda arg: tab['vm'].module.process_response(None, arg),
                    arg=(action[3] if len(action) > 3 else None)))
            else:
                input_request.inputRequestAccepted.connect(
                    lambda userinput: tab['vm'].module.process_response(userinput))
                input_request.inputRequestRejected.connect(
                    lambda: tab['vm'].module.process_response(None))

            input_request.inputRequest.emit(tab['metadata']['name'], action[1], True, False,
                                            action[2] if len(action) > 2 else "")

        elif action[0] == Action.ask_input_multi_line:
            input_request = self.window.window.findChild(QObject, "inputRequests")
            # Disconnect possibly existing handlers
            try:
                input_request.inputRequestAccepted.disconnect()
            except TypeError:
                pass
            try:
                input_request.inputRequestRejected.disconnect()
            except TypeError:
                pass

            if len(signature(tab['vm'].module.process_response).parameters) == 2:
                input_request.inputRequestAccepted.connect(partial(
                    lambda userinput, arg: tab['vm'].module.process_response(userinput, arg),
                    arg=(action[3] if len(action) > 3 else None)))
                input_request.inputRequestRejected.connect(partial(
                    lambda arg: tab['vm'].module.process_response(None, arg),
                    arg=(action[3] if len(action) > 3 else None)))
            else:
                input_request.inputRequestAccepted.connect(
                    lambda userinput: tab['vm'].module.process_response(userinput))
                input_request.inputRequestRejected.connect(
                    lambda: tab['vm'].module.process_response(None))

            input_request.inputRequest.emit(tab['metadata']['name'], action[1], False, True,
                                            action[2] if len(action) > 2 else "")

        elif action[0] == Action.copy_to_clipboard:
            # Copy the given data to the user-chosen clipboard
            self.window.output_queue.append(str(action[1]))
            if Settings.get('output_mode') == OutputMode.AutoType:
                Logger.log(tab['metadata']['name'], Translation.get("data_queued_for_typing"))
            else:
                Logger.log(tab['metadata']['name'], Translation.get("data_queued_for_clipboard"))

        elif action[0] == Action.set_selection:
            if len(action) > 1:
                tab['vm'].selection = action[1]
            else:
                tab['vm'].selection = []

            tab['vm'].context.setContextProperty(
                "resultListModelTree", tab['vm'].selection)

            if tab['vm'].selection_thread:
                tab['vm'].selection_thread.join()

            tab['vm'].make_selection()

        elif action[0] == Action.close:
            # Don't close and stay on the same depth if the user explicitly requested to not close after last input
            if not tab['vm'].minimize_disabled:
                self.window.close()

                selection = []  # type: List[Dict[SelectionType, str]]
            else:
                selection = tab['vm'].selection[:-1]

            tab['vm'].minimize_disabled = False

            tab['vm'].queue.put([Action.set_selection, selection])

        elif action[0] == Action.set_entry_info:
            if len(action) > 2:
                tab['vm'].extra_info_entries[str(action[1])] = str(action[2])
            else:
                try:
                    del tab['vm'].extra_info_entries[str(action[1])]
                except KeyError:
                    pass

            tab['vm'].update_context_info_panel(request_update=False)

        elif action[0] == Action.replace_entry_info_dict:
            if len(action) > 1:
                tab['vm'].extra_info_entries = action[1]
            else:
                tab['vm'].extra_info_entries = {}

            tab['vm'].update_context_info_panel(request_update=False)

        elif action[0] == Action.set_command_info:
            if len(action) > 2:
                tab['vm'].extra_info_commands[str(action[1])] = str(action[2])
            else:
                try:
                    del tab['vm'].extra_info_commands[str(action[1])]
                except KeyError:
                    pass

            tab['vm'].update_context_info_panel(request_update=False)

        elif action[0] == Action.replace_command_info_dict:
            if len(action) > 1:
                tab['vm'].extra_info_commands = action[1]
            else:
                tab['vm'].extra_info_commands = {}

            tab['vm'].update_context_info_panel(request_update=False)

        elif action[0] == Action.set_base_info:
            if len(action) > 1:
                tab['vm'].update_base_info_panel(action[1])
            else:
                tab['vm'].update_base_info_panel("")

        elif action[0] == Action.set_entry_context:
            if len(action) > 2:
                tab['vm'].context_menu_entries[str(action[1])] = action[2]
            else:
                try:
                    del tab['vm'].context_menu_entries[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_entry_context_dict:
            if len(action) > 1:
                tab['vm'].context_menu_entries = action[1]
            else:
                tab['vm'].context_menu_entries = {}

        elif action[0] == Action.set_command_context:
            if len(action) > 2:
                tab['vm'].context_menu_commands[str(action[1])] = action[2]
            else:
                try:
                    del tab['vm'].context_menu_commands[str(action[1])]
                except KeyError:
                    pass

        elif action[0] == Action.replace_command_context_dict:
            if len(action) > 1:
                tab['vm'].context_menu_commands = action[1]
            else:
                tab['vm'].context_menu_commands = {}

        elif action[0] == Action.set_base_context:
            if len(action) > 1:
                tab['vm'].context_menu_base = action[1]
            else:
                tab['vm'].context_menu_base = []

            tab['vm'].context_menu_model_base_list.setStringList(str(entry) for entry in tab['vm'].context_menu_base)

        else:
            print('WARN: Module requested unknown action {}'.format(action[0]))

        if active_tab and tab['entries_processed'] >= 100:
            tab['vm'].search(new_entries=True)
            tab['entries_processed'] = 0

        tab['queue'].task_done()

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

            current_tab = QQmlProperty.read(self.window.tabs, "currentIndex")

            all_empty = True
            for tab_id, tab in enumerate(self.window.tab_bindings):
                if not tab['init']:
                    continue

                tab['vm'].context.setContextProperty(
                    "unprocessedCount", tab['queue'].qsize())
                if tab_id == current_tab:
                    active_tab = True
                    tab['vm'].context.setContextProperty(
                        "resultListModelHasEntries", True if tab['vm'].entry_list or tab['vm'].command_list else False)
                else:
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
                    print('WARN: Module {} caused exception {}'.format(tab['metadata']['name'], e))
                    traceback.print_exc()

            if all_empty:
                if self.window.window.isVisible():
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)


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

    def save_modules(self, profile: str, modules: List[Dict]) -> None:
        """Save the list of open modules and their settings to the profile."""
        config = configparser.ConfigParser()
        for number, module in enumerate(modules):
            settings = {}
            for setting in module['settings']:
                # Only save non-internal variables
                if setting[0] != "_":
                    value = module['settings'][setting]
                    settings[setting] = str(value) if value is not None else ''

            # Append Pext state variables
            for setting in module['vm'].settings:
                try:
                    value = module['vm'].settings[setting].name
                except KeyError:
                    value = module['vm'].settings[setting]

                settings[setting] = str(value) if value is not None else ''

            config['{}_{}'.format(number, module['metadata']['id'])] = settings

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

        # FIXME: Cheap hack to work around Debian's faultily-patched pip
        # We try to prevent false positives by checking for (mini)conda or a venv
        if ("conda" not in sys.version and os.path.isfile('/etc/issue.net') and
                'Debian' in open('/etc/issue.net', 'r').read() and
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

    def load(self, window: 'Window', module: Dict[str, Any]) -> bool:
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

        # Prepare viewModel and context
        vm = ViewModel(view_settings)
        module_context = QQmlContext(window.context)
        module_context.setContextProperty(
            "sortMode", vm.sort_mode)
        module_context.setContextProperty(
            "resultListModel", vm.result_list_model_list)
        module_context.setContextProperty(
            "resultListModelNormalEntries", len(vm.filtered_entry_list))
        module_context.setContextProperty(
            "resultListModelCommandEntries", len(vm.filtered_command_list))
        module_context.setContextProperty(
            "resultListModelHasEntries", False)
        module_context.setContextProperty(
            "resultListModelCommandMode", False)
        module_context.setContextProperty(
            "resultListModelTree", [])
        module_context.setContextProperty(
            "unprocessedCount", 0)
        module_context.setContextProperty(
            "contextMenuModel", vm.context_menu_model_list)
        module_context.setContextProperty(
            "contextMenuModelFull", vm.context_menu_model_list_full)
        module_context.setContextProperty(
            "contextMenuModelEntrySpecificCount", 0)
        module_context.setContextProperty(
            "contextMenuEnabled", False)
        module_context.setContextProperty(
            "searchInputFieldEmpty", True)

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

        module['settings']['_api_version'] = [0, 12, 0]
        module['settings']['_locale'] = locale
        module['settings']['_portable'] = Settings.get('_portable')

        # Start the module in the background
        module_thread = ModuleThreadInitializer(
            module['metadata']['name'],
            q,
            target=module_code.init,
            args=(module['settings'], q))
        module_thread.start()

        # Add tab
        tab_data = QQmlComponent(window.engine)
        tab_data.loadUrl(
            QUrl.fromLocalFile(os.path.join(AppFile.get_path(), 'qml', 'ModuleData.qml')))
        window.engine.setContextForObject(tab_data, module_context)
        window.tabs.addTab(module['metadata']['name'], tab_data)

        # Store tab/viewModel combination
        # tabData is not used but stored to prevent segfaults caused by
        # Python garbage collecting it
        window.tab_bindings.append({'init': False,
                                    'queue': q,
                                    'vm': vm,
                                    'module': module_code,
                                    'module_context': module_context,
                                    'module_import': module_import,
                                    'metadata': module['metadata'],
                                    'tab_data': tab_data,
                                    'settings': module['settings'],
                                    'entries_processed': 0})

        # Open tab to trigger loading
        QQmlProperty.write(
            window.tabs, "currentIndex", QQmlProperty.read(window.tabs, "count") - 1)

        # Save active modules
        ProfileManager().save_modules(Settings.get('profile'), window.tab_bindings)

        # First module? Enforce load
        if len(window.tab_bindings) == 1:
            window.tabs.currentIndexChanged.emit()

        return True

    def stop(self, window: 'Window', tab_id: int) -> None:
        """Call a module's stop function by ID."""
        try:
            window.tab_bindings[tab_id]['vm'].stop()
        except Exception as e:
            print('WARN: Module {} caused exception {} on unload'
                  .format(window.tab_bindings[tab_id]['metadata']['name'], e))
            traceback.print_exc()

    def unload(self, window: 'Window', tab_id: int) -> None:
        """Unload a module by tab ID."""
        if QQmlProperty.read(window.tabs, "currentIndex") == tab_id:
            tab_count = QQmlProperty.read(window.tabs, "count")
            if tab_count == 1:
                QQmlProperty.write(window.tabs, "currentIndex", "-1")
            elif tab_id + 1 < tab_count:
                QQmlProperty.write(window.tabs, "currentIndex", tab_id + 1)
            else:
                QQmlProperty.write(window.tabs, "currentIndex", "0")

        window.tabs.removeRequest.emit(tab_id)
        del window.tab_bindings[tab_id]

        # Save active modules
        ProfileManager().save_modules(Settings.get('profile'), window.tab_bindings)

        # Ensure a proper refresh on the UI side
        window.tabs.currentIndexChanged.emit()

    def get_info(self, module_id: str) -> Optional[Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return the metadata and source of one single module."""
        return ObjectManager().list_object(os.path.join(self.module_dir, module_id.replace('.', '_')))

    def list(self) -> Dict[str, Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return a list of modules together with their source."""
        return ObjectManager().list_objects(self.module_dir)

    def reload_step_unload(self, window: 'Window', tab_id: int) -> Dict[str, str]:
        """Reload a module by tab ID: Unload step."""
        # Get the needed info to load the module
        module_data = window.tab_bindings[tab_id]
        module = {
            'metadata': module_data['metadata'],
            'settings': module_data['settings'],
            'module_import': module_data['module_import']
        }

        # Stop the module
        self.stop(window, tab_id)

        # Disable with reason: update
        window.disable_module(tab_id, 2)

        return module

    def reload_step_load(self, window: 'Window', tab_id: int, module_data: Dict[str, Any]) -> bool:
        """Reload a module by tab ID: Load step."""
        # Get currently active tab
        current_index = QQmlProperty.read(window.tabs, "currentIndex")

        # Unload the module
        self.unload(window, tab_id)

        # Force a reload to make code changes happen
        reload(module_data['module_import'])

        # Load it into the UI
        module = {
            'metadata': module_data['metadata'],
            'settings': module_data['settings']
        }

        if not self.load(window, module):
            return False

        # Get new position
        new_tab_id = len(window.tab_bindings) - 1

        # Move to correct position if there is more than 1 tab
        if new_tab_id > 0:
            window.tabs.moveTab(new_tab_id, tab_id)
            window.tab_bindings.insert(tab_id, window.tab_bindings.pop(new_tab_id))

            # Focus on active tab
            QQmlProperty.write(window.tabs, "currentIndex", str(current_index))

        # Ensure a proper refresh on the UI side
        window.tabs.currentIndexChanged.emit()

        return True

    def install(self, url: str, identifier: str, name: str, verbose=False, interactive=True) -> bool:
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
            porcelain.clone(UpdateManager.fix_git_url_for_dulwich(url), module_path)
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
    def get_remote_url(directory: str) -> str:
        """Get the url of the given remote for the specified git-managed directory."""
        with UpdateManager._path_to_repo(directory) as repo:
            config = repo.get_config()
            return config.get(("remote".encode(), "origin".encode()), "url".encode()).decode()

    @staticmethod
    def has_update(directory: str, branch=b'refs/heads/master') -> bool:
        """Check if an update is available for the git-managed directory."""
        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
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
            porcelain.pull(repo, remote_url)

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
        self.command_list = []  # type: List
        self.entry_list = []  # type: List
        self.filtered_entry_list = []  # type: List
        self.filtered_command_list = []  # type: List
        self.result_list_model_list = QStringListModel()
        self.result_list_model_max_index = -1
        self.selection = []  # type: List[Dict[SelectionType, str]]
        self.last_search = ""
        self.context_menu_model_list = QStringListModel()
        self.context_menu_model_base_list = QStringListModel()
        self.context_menu_model_list_full = QStringListModel()
        self.extra_info_entries = {}  # type: Dict[str, str]
        self.extra_info_commands = {}  # type: Dict[str, str]
        self.context_menu_entries = {}  # type: Dict[str, List[str]]
        self.context_menu_commands = {}  # type: Dict[str, List[str]]
        self.context_menu_base = []  # type: List[str]
        self.extra_info_last_entry = ""
        self.extra_info_last_entry_type = None
        self.selection_thread = None  # type: Optional[threading.Thread]
        self.minimize_disabled = False

        self.settings = view_settings

        self.stopped = False

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
        try:
            self.context.setContextProperty("sortMode", self.sort_mode)
            # Force a resort
            self.search(new_entries=True)
        except AttributeError:
            pass

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

    def _clear_queue(self) -> None:
        while True:
            try:
                self.queue.get_nowait()
            except Empty:
                return
            self.queue.task_done()

    def bind_context(self, queue: Queue, context: QQmlContext, window: 'Window', search_input_model: QObject,
                     header_text: QObject, result_list_model: QObject, context_menu_model: QObject,
                     base_info_panel: QObject, context_info_panel: QObject) -> None:
        """Bind the QML context so we can communicate with the QML front-end."""
        self.queue = queue
        self.context = context
        self.window = window
        self.search_input_model = search_input_model
        self.header_text = header_text
        self.result_list_model = result_list_model
        self.context_menu_model = context_menu_model
        self.base_info_panel = base_info_panel
        self.context_info_panel = context_info_panel

        # Force propagation of settings values to QML
        self.settings = self._settings

    def bind_module(self, module: ModuleBase) -> None:
        """Bind the module.

        This ensures we can call functions in it.
        """
        self.module = module

    def go_up(self, to_base=False) -> None:
        """Go one level up.

        This means that, if we're currently in the entry content list, we go
        back to the entry list. If we're currently in the entry list, we clear
        the search bar. If we're currently in the entry list and the search bar
        is empty, we tell the window to hide/close itself.
        """
        if self.context.contextProperty("contextMenuEnabled"):
            self.hide_context()
            if not to_base:
                return

        if QQmlProperty.read(self.search_input_model, "text") != "":
            QQmlProperty.write(self.search_input_model, "text", "")
            self.context.setContextProperty("searchInputFieldEmpty", True)
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

            self.context.setContextProperty(
                "resultListModelTree", self.selection)

            self._clear_queue()

            self.make_selection()
        else:
            self.window.close(manual=True)

    def search(self, new_entries=False, manual=False) -> None:
        """Filter the entry list.

        Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        if self.stopped:
            return

        search_string = QQmlProperty.read(self.search_input_model, "text")
        self.context.setContextProperty("searchInputFieldEmpty", not search_string)

        # Don't search if nothing changed
        if not new_entries and search_string == self.last_search:
            return

        # Enable checking for changes next time
        self.last_search = search_string

        current_match = None
        current_index = 0

        # If context menu is open, search in context menu
        if self.context.contextProperty("contextMenuEnabled"):
            current_entry = self._get_entry()
            try:
                if current_entry['type'] == SelectionType.entry:
                    entry_list = [str(entry) for entry in self.context_menu_entries[current_entry['value']]]
                else:
                    entry_list = [str(entry) for entry in self.context_menu_commands[current_entry['value']]]
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
                current_match = self.context_menu_model_list_full.stringList()[
                        QQmlProperty.read(self.context_menu_model, "currentIndex")]
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
                current_match = self.result_list_model_list.stringList()[QQmlProperty.read(self.result_list_model,
                                                                                           "currentIndex")]
            except IndexError:
                pass

        # If empty, show all
        if not search_string and not new_entries:
            if self.context.contextProperty("contextMenuEnabled"):
                self.filtered_context_list = entry_list
                self.filtered_context_base_list = self.context_menu_base
                self.sorted_filtered_context_list = self.sorted_context_list
                self.sorted_filtered_context_base_list = self.sorted_context_base_list

                combined_list = self.sorted_filtered_context_list + self.sorted_filtered_context_base_list

                self.context_menu_model_list.setStringList(str(entry) for entry in self.sorted_filtered_context_list)
                self.context_menu_model_list_full.setStringList(str(entry) for entry in combined_list)
                self.context.setContextProperty(
                    "contextMenuModelEntrySpecificCount", len(self.sorted_filtered_context_list))
            else:
                self.filtered_entry_list = self.entry_list
                self.filtered_command_list = self.command_list
                self.sorted_filtered_entry_list = self.sorted_entry_list
                self.sorted_filtered_command_list = self.sorted_command_list

                combined_list = self.sorted_filtered_entry_list + self.sorted_filtered_command_list

                self.result_list_model_list.setStringList(str(entry) for entry in combined_list)

                self.context.setContextProperty(
                    "resultListModelNormalEntries", len(self.sorted_filtered_entry_list))
                self.context.setContextProperty(
                    "resultListModelCommandEntries", len(self.sorted_filtered_command_list))

            # Keep existing selection, otherwise ensure something is selected
            if current_match:
                try:
                    current_index = combined_list.index(current_match)
                except ValueError:
                    current_index = 0

            if self.context.contextProperty("contextMenuEnabled"):
                QQmlProperty.write(self.context_menu_model, "currentIndex", current_index)
            else:
                QQmlProperty.write(self.result_list_model, "currentIndex", current_index)

                self.update_context_info_panel()

            return

        if self.context.contextProperty("contextMenuEnabled"):
            self.filtered_context_list = []
            self.filtered_context_base_list = []
        else:
            self.filtered_entry_list = []
            self.filtered_command_list = []

        # String matching logic
        list_match = search_string.lower().split(' ')

        def check_list_match(entries, string_list) -> List[str]:
            return_list = []  # type: List[str]
            for entry in entries:
                lower_entry = entry.lower()
                for search_string_part in string_list:
                    if search_string_part not in lower_entry:
                        break
                else:
                    # If exact match, put on top
                    if len(string_list) == 1 and string_list[0] == entry.lower():
                        return_list.insert(0, entry)
                    # otherwise, put on bottom
                    else:
                        return_list.append(entry)

            return return_list

        if self.context.contextProperty("contextMenuEnabled"):
            self.filtered_context_list = check_list_match(self.sorted_context_list, list_match)
            self.filtered_context_base_list = check_list_match(self.sorted_context_base_list, list_match)
        else:
            self.filtered_entry_list = check_list_match(self.sorted_entry_list, list_match)
            self.filtered_command_list = check_list_match(self.sorted_command_list, list_match)

        if self.context.contextProperty("contextMenuEnabled"):
            combined_list = self.filtered_context_list + self.filtered_context_base_list
        else:
            combined_list = self.filtered_entry_list + self.filtered_command_list

            self.context.setContextProperty(
                "resultListModelNormalEntries", len(self.filtered_entry_list))
            self.context.setContextProperty(
                "resultListModelCommandEntries", len(self.filtered_command_list))

        if self.context.contextProperty("contextMenuEnabled"):
            self.context_menu_model_list.setStringList(str(entry) for entry in self.filtered_context_list)
            self.context_menu_model_list_full.setStringList(str(entry) for entry in combined_list)
            self.context.setContextProperty("contextMenuModelEntrySpecificCount", len(self.filtered_context_list))
        else:
            self.result_list_model_list.setStringList(str(entry) for entry in combined_list)

        # See if we have an exact match
        if combined_list and len(list_match) == 1 and combined_list[0].lower() == list_match[0]:
            current_index = 0
        # Otherwise, keep existing selection
        elif current_match:
            try:
                current_index = combined_list.index(current_match)
            # As fallback, ensure something is selected
            except ValueError:
                current_index = 0

        if self.context.contextProperty("contextMenuEnabled"):
            QQmlProperty.write(self.context_menu_model, "currentIndex", current_index)
        else:
            QQmlProperty.write(self.result_list_model, "currentIndex", current_index)

            self.update_context_info_panel()

        # Turbo mode: Select entry if only entry left
        if Settings.get('turbo_mode') and len(combined_list) == 1 and self.queue.empty() and search_string:
            self.select(force_args=True)

    def _get_entry(self, include_context=False) -> Dict:
        """Get info on the entry that's currently focused."""
        if include_context and self.context.contextProperty("contextMenuEnabled"):
            current_index = QQmlProperty.read(self.context_menu_model, "currentIndex")

            selected_entry = self._get_entry()

            # Return entry-specific option if selected, otherwise base option
            if current_index >= len(self.filtered_context_list):
                # Selection is a base entry
                return {'type': SelectionType.none,
                        'value': None,
                        'context_option': self.filtered_context_base_list[
                            current_index - len(self.filtered_context_list)]
                        }
            else:
                selected_entry['context_option'] = self.filtered_context_list[current_index]

            return selected_entry

        current_index = QQmlProperty.read(self.result_list_model, "currentIndex")

        if current_index >= len(self.filtered_entry_list):
            # Selection is a command
            selection_type = SelectionType.command
            entry = self.filtered_command_list[current_index - len(self.filtered_entry_list)]
        else:
            selection_type = SelectionType.entry
            entry = self.filtered_entry_list[current_index]

        return {'type': selection_type, 'value': entry, 'context_option': None}

    def select(self, command_args="", force_args=False, disable_minimize=False) -> None:
        """Notify the module of our selection entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        selection = self._get_entry(include_context=True)
        if selection['type'] == SelectionType.command:
            if force_args or selection['context_option'] == Translation.get("enter_arguments"):
                self.input_args()
                return

        selection["args"] = command_args
        self.selection.append(selection)

        self.context.setContextProperty(
            "contextMenuEnabled", False)
        self.context.setContextProperty(
            "resultListModelTree", self.selection)

        self.entry_list = []
        self.command_list = []
        self.extra_info_entries = {}
        self.extra_info_commands = {}
        self.context_menu_entries = {}
        self.context_menu_commands = {}

        QQmlProperty.write(self.search_input_model, "text", "")
        self.context.setContextProperty("searchInputFieldEmpty", True)
        self.search(new_entries=True, manual=True)
        self._clear_queue()

        self.make_selection(disable_minimize=disable_minimize)

    def show_context(self) -> None:
        """Show the context menu of the selected entry."""
        if self.stopped:
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

        QQmlProperty.write(self.context_menu_model, "currentIndex", 0)
        self.context.setContextProperty(
            "contextMenuEnabled", True)

        if QQmlProperty.read(self.search_input_model, "text") != "":
            QQmlProperty.write(self.search_input_model, "text", "")
            self.context.setContextProperty("searchInputFieldEmpty", True)
        self.search(new_entries=True)

    def hide_context(self) -> None:
        """Hide the context menu."""
        if self.stopped:
            return

        self.context.setContextProperty(
            "contextMenuEnabled", False)

        if QQmlProperty.read(self.search_input_model, "text") != "":
            QQmlProperty.write(self.search_input_model, "text", "")
            self.context.setContextProperty("searchInputFieldEmpty", True)
        self.search()

    def update_context_info_panel(self, request_update=True) -> None:
        """Update the context info panel with the info panel data of the currently selected entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            QQmlProperty.write(self.context_info_panel, "text", "")
            self.extra_info_last_entry_type = None
            return

        current_entry = self._get_entry()

        # Prevent updating the list unnecessarily often
        if (current_entry['value'] == self.extra_info_last_entry
                and current_entry['type'] == self.extra_info_last_entry_type):
            return

        self.extra_info_last_entry = current_entry['value']
        self.extra_info_last_entry_type = current_entry['type']

        if request_update:
            info_selection = self.selection[:]
            new_selection_entry = current_entry
            info_selection.append(new_selection_entry)

            threading.Thread(target=self.module.extra_info_request, args=(info_selection,)).start()

        try:
            if current_entry['type'] == SelectionType.entry:
                QQmlProperty.write(self.context_info_panel, "text", self.extra_info_entries[current_entry['value']])
            else:
                QQmlProperty.write(self.context_info_panel, "text", self.extra_info_commands[current_entry['value']])
        except KeyError:
            QQmlProperty.write(self.context_info_panel, "text", "")

    def update_base_info_panel(self, base_info: str) -> None:
        """Update the base info panel based on the current module state."""
        QQmlProperty.write(self.base_info_panel, "text", str(base_info))

    def set_header(self, content) -> None:
        """Set the header text."""
        QQmlProperty.write(self.header_text, "text", str(content))

    def tab_complete(self) -> None:
        """Tab-complete based on the current seach input.

        This tab-completes the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        if self.stopped:
            return

        current_input = QQmlProperty.read(self.search_input_model, "text")
        combined_list = self.filtered_entry_list + self.filtered_command_list

        entry = self._get_longest_common_string(
                [entry.lower() for entry in combined_list],
                start=current_input.lower())
        if entry is None or len(entry) <= len(current_input):
            self.queue.put(
                [Action.add_error, Translation.get("no_tab_completion_possible")])
            return

        QQmlProperty.write(self.search_input_model, "text", entry)
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
        if not self.context.contextProperty("contextMenuEnabled") and selected_entry["type"] != SelectionType.command:
            if len(self.filtered_command_list) > 0:
                # Jump to the first command in case the current selection
                # is not a command
                QQmlProperty.write(self.result_list_model, "currentIndex",
                                   len(self.filtered_entry_list))
                selected_entry = self._get_entry(include_context=True)
            else:
                self.queue.put(
                    [Action.add_error, Translation.get("no_command_available_for_current_filter")])
                return

        args_request = self.window.window.findChild(QObject, "commandArgsDialog")
        args_request.commandArgsRequestAccepted.connect(
            lambda args: self.select(args))

        args_request.showCommandArgsDialog.emit(selected_entry["value"])


class Window():
    """The main Pext window."""

    def __init__(self, app: QApplication, locale_manager: LocaleManager, module_manager: ModuleManager,
                 theme_manager: 'ThemeManager', parent=None) -> None:
        """Initialize the window."""
        # Actionable items to show in the UI
        self.actionables = []  # type: List[Dict]

        # Text to type on close if needed
        self.output_queue = []  # type: List[str]

        # Save settings
        self.locale_manager = locale_manager

        self.tab_bindings = []  # type: List[Dict]
        self.tray = None  # type: Optional[Tray]

        self.app = app
        self.engine = QQmlApplicationEngine(None)

        # Set QML variables
        self.context = self.engine.rootContext()
        self.context.setContextProperty(
            "FORCE_FULLSCREEN", self.app.platformName() in ['webgl', 'vnc'])
        self.context.setContextProperty(
            "USE_INTERNAL_UPDATER", USE_INTERNAL_UPDATER)
        self.context.setContextProperty(
            "applicationVersion", UpdateManager().get_core_version())
        self.context.setContextProperty(
            "systemPlatform", platform.system())

        self.context.setContextProperty(
            "modulesPath", os.path.join(ConfigRetriever.get_path(), 'modules'))
        self.context.setContextProperty(
            "themesPath", os.path.join(ConfigRetriever.get_path(), 'themes'))

        self.context.setContextProperty("currentTheme", Settings.get('theme'))
        self.context.setContextProperty("defaultProfile", ProfileManager.default_profile_name())
        self.context.setContextProperty("currentProfile", Settings.get('profile'))
        self.context.setContextProperty("currentLocale", self.locale_manager.get_current_locale(system_if_unset=False))
        self.context.setContextProperty("currentLocaleCode",
                                        LocaleManager.find_best_locale(Settings.get('locale')).name())
        self.context.setContextProperty("locales", self.locale_manager.get_locales())

        # Load the main UI
        self.engine.load(QUrl.fromLocalFile(os.path.join(AppFile.get_path(), 'qml', 'main.qml')))

        self.window = self.engine.rootObjects()[0]

        # Give the translator a reference to the window
        Translation.bind_window(self)

        # Some hacks to make Qt WebGL streaming work
        if self.app.platformName() == 'webgl':
            self.parent_window = QWindow()
            self.parent_window.setVisibility(QWindow.FullScreen)
            self.window.setParent(self.parent_window)

        # Override quit and minimize
        self.window.confirmedClose.connect(self.quit)
        self.window.windowStateChanged.connect(self._process_window_state)

        # Give QML the module info
        self.intro_screen = self.window.findChild(QObject, "introScreen")
        self.module_manager = module_manager
        self._update_modules_info_qml()

        # Give QML the theme info
        self.theme_manager = theme_manager
        self._update_themes_info_qml()

        # Give QML the profile info
        self.profile_manager = ProfileManager()
        self._update_profiles_info_qml()

        # Bind global shortcuts
        self.search_input_model = self.window.findChild(
            QObject, "searchInputModel")
        escape_shortcut = self.window.findChild(QObject, "escapeShortcut")
        shift_escape_shortcut = self.window.findChild(QObject, "shiftEscapeShortcut")
        back_button = self.window.findChild(QObject, "backButton")
        tab_shortcut = self.window.findChild(QObject, "tabShortcut")
        args_shortcut = self.window.findChild(QObject, "argsShortcut")

        self.search_input_model.textChanged.connect(self._search)
        self.search_input_model.accepted.connect(self._select)
        escape_shortcut.activated.connect(self._go_up)
        shift_escape_shortcut.activated.connect(self._go_up_to_base_and_minimize)
        back_button.clicked.connect(self._go_up)
        tab_shortcut.activated.connect(self._tab_complete)
        args_shortcut.activated.connect(self._input_args)

        # Bind internal calls
        self.window.internalCall.connect(InternalCallProcessor.enqueue)

        # Bind actionable remove
        actionable_repeater = self.window.findChild(
            QObject, "actionableRepeater")
        actionable_repeater.removeActionable.connect(self._remove_actionable)

        # Find menu entries
        menu_reload_active_module_shortcut = self.window.findChild(
            QObject, "menuReloadActiveModule")
        self.menu_load_module_shortcut = self.window.findChild(
            QObject, "menuLoadModule")
        menu_close_active_module_shortcut = self.window.findChild(
            QObject, "menuCloseActiveModule")
        menu_install_module_shortcut = self.window.findChild(
            QObject, "menuInstallModule")
        menu_manage_modules_shortcut = self.window.findChild(
            QObject, "menuManageModules")

        menu_load_theme_shortcut = self.window.findChild(
            QObject, "menuLoadTheme")
        menu_install_theme_shortcut = self.window.findChild(
            QObject, "menuInstallTheme")
        menu_manage_themes_shortcut = self.window.findChild(
            QObject, "menuManageThemes")

        menu_load_profile_shortcut = self.window.findChild(
            QObject, "menuLoadProfile")
        menu_manage_profiles_shortcut = self.window.findChild(
            QObject, "menuManageProfiles")

        menu_turbo_mode_shortcut = self.window.findChild(
            QObject, "menuTurboMode")

        menu_change_language_shortcut = self.window.findChild(
            QObject, "menuChangeLanguage")

        self.menu_output_default_clipboard = self.window.findChild(
            QObject, "menuOutputDefaultClipboard")
        menu_output_selection_clipboard = self.window.findChild(
            QObject, "menuOutputSelectionClipboard")
        menu_output_find_buffer = self.window.findChild(
            QObject, "menuOutputFindBuffer")
        self.menu_output_auto_type = self.window.findChild(
            QObject, "menuOutputAutoType")

        menu_output_separator_none = self.window.findChild(
            QObject, "menuOutputSeparatorNone")
        menu_output_separator_enter = self.window.findChild(
            QObject, "menuOutputSeparatorEnter")
        menu_output_separator_tab = self.window.findChild(
            QObject, "menuOutputSeparatorTab")

        menu_minimize_normally_shortcut = self.window.findChild(
            QObject, "menuMinimizeNormally")
        menu_minimize_to_tray_shortcut = self.window.findChild(
            QObject, "menuMinimizeToTray")
        menu_minimize_normally_manually_shortcut = self.window.findChild(
            QObject, "menuMinimizeNormallyManually")
        menu_minimize_to_tray_manually_shortcut = self.window.findChild(
            QObject, "menuMinimizeToTrayManually")
        self.menu_enable_global_hotkey_shortcut = self.window.findChild(
            QObject, "menuEnableGlobalHotkey")
        menu_show_tray_icon_shortcut = self.window.findChild(
            QObject, "menuShowTrayIcon")
        menu_install_quick_action_service = self.window.findChild(
            QObject, "menuInstallQuickActionService")
        self.menu_enable_update_check_shortcut = self.window.findChild(
            QObject, "menuEnableUpdateCheck")
        self.menu_enable_object_update_check_shortcut = self.window.findChild(
            QObject, "menuEnableObjectUpdateCheck")
        self.menu_enable_object_update_install_shortcut = self.window.findChild(
            QObject, "menuEnableObjectUpdateInstall")

        menu_quit_shortcut = self.window.findChild(QObject, "menuQuit")
        menu_check_for_updates_shortcut = self.window.findChild(QObject, "menuCheckForUpdates")
        menu_homepage_shortcut = self.window.findChild(QObject, "menuHomepage")

        # Bind menu entries
        menu_reload_active_module_shortcut.triggered.connect(
            self._reload_active_module)
        self.menu_load_module_shortcut.loadModuleRequest.connect(self._open_tab)
        menu_close_active_module_shortcut.triggered.connect(self._close_tab)
        menu_install_module_shortcut.installModuleRequest.connect(
            self._menu_install_module)
        menu_manage_modules_shortcut.uninstallModuleRequest.connect(
            self._menu_uninstall_module)
        menu_manage_modules_shortcut.updateModuleRequest.connect(self._menu_update_module)

        menu_load_theme_shortcut.loadThemeRequest.connect(self._menu_switch_theme)
        menu_install_theme_shortcut.installThemeRequest.connect(
            self._menu_install_theme)
        menu_manage_themes_shortcut.uninstallThemeRequest.connect(
            self._menu_uninstall_theme)
        menu_manage_themes_shortcut.updateThemeRequest.connect(self._menu_update_theme)

        menu_load_profile_shortcut.loadProfileRequest.connect(self._menu_switch_profile)
        menu_manage_profiles_shortcut.createProfileRequest.connect(self._menu_create_profile)
        menu_manage_profiles_shortcut.renameProfileRequest.connect(self._menu_rename_profile)
        menu_manage_profiles_shortcut.removeProfileRequest.connect(self._menu_remove_profile)

        menu_turbo_mode_shortcut.toggled.connect(self._menu_toggle_turbo_mode)

        menu_change_language_shortcut.changeLanguage.connect(self._menu_change_language)

        self.menu_output_default_clipboard.toggled.connect(self._menu_output_default_clipboard)
        menu_output_selection_clipboard.toggled.connect(self._menu_output_selection_clipboard)
        menu_output_find_buffer.toggled.connect(self._menu_output_find_buffer)
        self.menu_output_auto_type.toggled.connect(self._menu_output_auto_type)

        menu_output_separator_none.toggled.connect(self._menu_output_separator_none)
        menu_output_separator_enter.toggled.connect(self._menu_output_separator_enter)
        menu_output_separator_tab.toggled.connect(self._menu_output_separator_tab)

        menu_minimize_normally_shortcut.toggled.connect(self._menu_minimize_normally)
        menu_minimize_to_tray_shortcut.toggled.connect(self._menu_minimize_to_tray)
        menu_minimize_normally_manually_shortcut.toggled.connect(self._menu_minimize_normally_manually)
        menu_minimize_to_tray_manually_shortcut.toggled.connect(self._menu_minimize_to_tray_manually)
        self.menu_enable_global_hotkey_shortcut.toggled.connect(self._menu_enable_global_hotkey_shortcut)
        menu_show_tray_icon_shortcut.toggled.connect(self._menu_toggle_tray_icon)
        menu_install_quick_action_service.triggered.connect(self._menu_install_quick_action_service)
        self.menu_enable_object_update_check_shortcut.toggled.connect(self._menu_toggle_object_update_check)
        self.menu_enable_object_update_install_shortcut.toggled.connect(self._menu_toggle_object_update_install)

        menu_quit_shortcut.triggered.connect(self.quit)
        menu_check_for_updates_shortcut.triggered.connect(self._menu_check_updates)
        menu_homepage_shortcut.triggered.connect(self._show_homepage)

        # Set entry states
        QQmlProperty.write(menu_turbo_mode_shortcut,
                           "checked",
                           Settings.get('turbo_mode'))

        QQmlProperty.write(self.menu_output_default_clipboard,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.DefaultClipboard)
        QQmlProperty.write(menu_output_selection_clipboard,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.SelectionClipboard)
        QQmlProperty.write(menu_output_find_buffer,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.FindBuffer)
        QQmlProperty.write(self.menu_output_auto_type,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.AutoType)

        QQmlProperty.write(menu_output_separator_none,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.None_)
        QQmlProperty.write(menu_output_separator_enter,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.Enter)
        QQmlProperty.write(menu_output_separator_tab,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.Tab)

        QQmlProperty.write(menu_minimize_normally_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.Normal)
        QQmlProperty.write(menu_minimize_to_tray_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.Tray)
        QQmlProperty.write(menu_minimize_normally_manually_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.NormalManualOnly)
        QQmlProperty.write(menu_minimize_to_tray_manually_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.TrayManualOnly)

        QQmlProperty.write(self.menu_enable_global_hotkey_shortcut,
                           "checked",
                           Settings.get('global_hotkey_enabled'))
        QQmlProperty.write(menu_show_tray_icon_shortcut,
                           "checked",
                           Settings.get('tray'))
        QQmlProperty.write(self.menu_enable_update_check_shortcut,
                           "checked",
                           Settings.get('update_check'))
        QQmlProperty.write(self.menu_enable_object_update_check_shortcut,
                           "checked",
                           Settings.get('object_update_check'))
        QQmlProperty.write(self.menu_enable_object_update_install_shortcut,
                           "checked",
                           Settings.get('object_update_check') and Settings.get('object_update_install'))

        # We bind the update check after writing the initial value to prevent
        # instantly triggering the update check
        self.menu_enable_update_check_shortcut.toggled.connect(self._menu_toggle_update_check)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self._bind_context)

        # Show the window if not --background
        if platform.system() == 'Darwin' and Settings.get('background'):
            # workaround for https://github.com/Pext/Pext/issues/20
            # First, we showMinimized to prevent Pext from being unrestorable
            self.window.showMinimized()
            # Then, we tell macOS to give the focus back to the last app
            self._macos_focus_workaround()
        elif not Settings.get('background'):
            self.show()

            if Settings.get('update_check') is None and USE_INTERNAL_UPDATER:
                # Tell the user automatic updating is enabled but set the last
                # check to right now so the user can disable it before the first
                # check
                Settings.set('last_update_check', time.time())
                self.add_actionable("update_check_enabled", Translation.get("actionable_update_check_enabled"))

                self._menu_toggle_object_update_check(True)
                self._menu_toggle_object_update_install(True)
                self._menu_toggle_update_check(True)

        # Set remembered geometry
        if not self.app.platformName() in ['webgl', 'vnc']:
            geometry = Settings.get('_window_geometry')
            try:
                self.window.setGeometry(*[int(geopoint) for geopoint in geometry.split(';')])
            except Exception as e:
                if geometry:
                    print("Invalid geometry: {}".format(e))
                screen_size = self.window.screen().size()
                self.window.setGeometry((screen_size.width() - 800) / 2, (screen_size.height() - 600) / 2, 800, 600)

        # Start binding the modules
        if len(Settings.get('modules')) > 0:
            for module in Settings.get('modules'):
                self.module_manager.load(self, module)
        else:
            for module in ProfileManager().retrieve_modules(Settings.get('profile')):
                self.module_manager.load(self, module)

        # If there's only one module passed through the command line, enforce
        # loading it now. Otherwise, switch back to the first module in the
        # list
        if len(self.tab_bindings) == 1:
            self.tabs.currentIndexChanged.emit()
        elif len(self.tab_bindings) > 1:
            QQmlProperty.write(self.tabs, "currentIndex", "0")

    def _macos_focus_workaround(self) -> None:
        """Set the focus correctly after minimizing Pext on macOS."""
        if platform.system() != 'Darwin' or pyautogui_error:
            return

        hotkey('command', 'tab')

    def _bind_context(self) -> None:
        """Bind the context for the module."""
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        if current_tab < 0:
            return

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

        # Get the info panels
        base_info_panel = self.tabs.getTab(
            current_tab).findChild(QObject, "baseInfoPanel")
        context_info_panel = self.tabs.getTab(
            current_tab).findChild(QObject, "contextInfoPanel")

        # Get the context menu
        context_menu_model = self.tabs.getTab(
            current_tab).findChild(QObject, "contextMenuModel")

        # Enable mouse selection support
        result_list_model.entryClicked.connect(element['vm'].select)
        result_list_model.selectExplicitNoMinimize.connect(
                    lambda: element['vm'].select(disable_minimize=True))
        result_list_model.openContextMenu.connect(element['vm'].show_context)
        result_list_model.openArgumentsInput.connect(element['vm'].input_args)
        context_menu_model.entryClicked.connect(element['vm'].select)
        context_menu_model.selectExplicitNoMinimize.connect(
                    lambda: element['vm'].select(disable_minimize=True))
        context_menu_model.openArgumentsInput.connect(element['vm'].input_args)
        context_menu_model.closeContextMenu.connect(element['vm'].hide_context)

        # Enable changing sort mode
        result_list_model.sortModeChanged.connect(element['vm'].next_sort_mode)

        # Enable info pane
        result_list_model.currentIndexChanged.connect(element['vm'].update_context_info_panel)

        # Bind it to the viewmodel
        element['vm'].bind_context(element['queue'],
                                   element['module_context'],
                                   self,
                                   self.search_input_model,
                                   header_text,
                                   result_list_model,
                                   context_menu_model,
                                   base_info_panel,
                                   context_info_panel)

        element['vm'].bind_module(element['module'])

        # Done initializing
        element['init'] = True

    def _process_window_state(self, event) -> None:
        if event & Qt.WindowMinimized:
            if Settings.get('minimize_mode') in [MinimizeMode.Tray, MinimizeMode.TrayManualOnly]:
                self.close(manual=True, force_tray=True)

    def _get_current_element(self) -> Optional[Dict]:
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        try:
            return self.tab_bindings[current_tab]
        except IndexError:
            # No tabs
            return None

    def _go_up(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].go_up()
            except TypeError:
                pass

    def _go_up_to_base_and_minimize(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].go_up(True)
            except TypeError:
                pass

        self.close(manual=True)

    def open_load_tab(self) -> None:
        """Open the tab to load a new module."""
        # TODO: Support giving the module name
        self.menu_load_module_shortcut.trigger()

    def _open_tab(self, identifier: str, name: str, settings: str) -> None:
        module_settings = {}
        for setting in settings.split(" "):
            try:
                key, value = setting.split("=", 2)
            except ValueError:
                continue

            module_settings[key] = value

        metadata = ModuleManager().get_info(identifier)['metadata']  # type: ignore
        module = {'metadata': metadata, 'settings': module_settings}
        self.module_manager.load(self, module)

    def _close_tab(self) -> None:
        if len(self.tab_bindings) > 0:
            tab_id = QQmlProperty.read(self.tabs, "currentIndex")
            self.module_manager.stop(self, tab_id)
            self.module_manager.unload(self, tab_id)

    def _reload_active_module(self) -> None:
        if len(self.tab_bindings) > 0:
            tab_id = QQmlProperty.read(self.tabs, "currentIndex")
            module_data = self.module_manager.reload_step_unload(self, tab_id)
            self.module_manager.reload_step_load(self, tab_id, module_data)

    def _menu_install_module(self, module_url: str, identifier: str, name: str) -> None:
        functions = [
            {
                'name': self.module_manager.install,
                'args': (module_url, identifier, name,),
                'kwargs': {'interactive': False, 'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }, {
                'name': InternalCallProcessor.enqueue,
                'args': ("pext:open_load_tab:{}".format(identifier),),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_uninstall_module(self, identifier: str) -> None:
        functions = [
            {
                'name': self.module_manager.uninstall,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_module(self, identifier: str) -> None:
        if not self.module_manager.has_update(identifier):
            return

        for tab in self.tab_bindings:
            if tab['metadata']['id'] == identifier:
                data = self.module_manager.get_info(identifier)
                self.add_actionable(
                    "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                    Translation.get("actionable_object_update_available_in_use").format(
                        data['metadata']['name']),  # type: ignore
                    Translation.get("actionable_object_update_available_in_use_button"),
                    "pext:update-module-in-use:{}".format(identifier)
                )
                return

        functions = [
            {
                'name': self.module_manager.update,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_restart_pext(self, extra_args=None) -> None:
        # Call _shut_down manually because it isn't called when using os.execv
        _shut_down(self)

        args = sys.argv[:]
        if extra_args:
            args.extend(extra_args)

        args.insert(0, sys.executable)
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]

        os.chdir(os.getcwd())
        os.execv(sys.executable, args)

    def _menu_switch_theme(self, theme_identifier: Optional[str]) -> None:
        Settings.set('theme', theme_identifier)

        self._menu_restart_pext()

    def _menu_switch_profile(self, profile_name: str, new_instance=bool) -> None:
        extra_args = ['--profile={}'.format(profile_name)]
        if not new_instance:
            self._menu_restart_pext(extra_args)
        else:
            args = sys.argv[:]
            args.extend(extra_args)
            args.insert(0, sys.executable)

            Popen(args)

    def _menu_create_profile(self, profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.create_profile,
                'args': (profile_name,),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_rename_profile(self, old_profile_name: str, new_profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.rename_profile,
                'args': (old_profile_name, new_profile_name),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_remove_profile(self, profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.remove_profile,
                'args': (profile_name,),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_install_theme(self, theme_url: str, identifier: str, name: str) -> None:
        functions = [
            {
                'name': self.theme_manager.install,
                'args': (theme_url, identifier, name,),
                'kwargs': {'interactive': False, 'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_uninstall_theme(self, identifier: str) -> None:
        functions = [
            {
                'name': self.theme_manager.uninstall,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_theme(self, identifier: str) -> None:
        functions = [
            {
                'name': self.theme_manager.update,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_all_themes(self, verbose=False) -> None:
        functions = [
            {
                'name': self.theme_manager.update_all,
                'args': (),
                'kwargs': {'verbose': False}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_toggle_turbo_mode(self, enabled: bool) -> None:
        Settings.set('turbo_mode', enabled)
        if enabled:
            for tab in self.tab_bindings:
                tab['vm'].search(new_entries=True)

    def _menu_change_language(self, lang_code: str) -> None:
        Settings.set('locale', lang_code)
        self._menu_restart_pext()

    def _menu_output_default_clipboard(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.DefaultClipboard)

    def _menu_output_selection_clipboard(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.SelectionClipboard)

    def _menu_output_find_buffer(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.FindBuffer)

    def _menu_output_auto_type(self, enabled: bool) -> None:
        if enabled:
            if platform.system() == 'Darwin' and pyautogui_error:
                Logger.log_critical(None, Translation.get("pyautogui_is_unavailable"), pyautogui_error)
                QQmlProperty.write(self.menu_output_auto_type, "checked", False)
                QQmlProperty.write(self.menu_output_default_clipboard, "checked", True)
                return

            if platform.system() != 'Darwin' and pynput_error:
                Logger.log_critical(None, Translation.get("pynput_is_unavailable"), pynput_error)
                QQmlProperty.write(self.menu_output_auto_type, "checked", False)
                QQmlProperty.write(self.menu_output_default_clipboard, "checked", True)
                return

            Settings.set('output_mode', OutputMode.AutoType)

    def _menu_output_separator_none(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.None_)

    def _menu_output_separator_enter(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.Enter)

    def _menu_output_separator_tab(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.Tab)

    def _menu_minimize_normally(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.Normal)

    def _menu_minimize_to_tray(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.Tray)

    def _menu_minimize_normally_manually(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.NormalManualOnly)

    def _menu_minimize_to_tray_manually(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.TrayManualOnly)

    def _menu_enable_global_hotkey_shortcut(self, enabled: bool) -> None:
        if enabled and pynput_error:
            Logger.log_critical(None, Translation.get("pynput_is_unavailable"), pynput_error)
            QQmlProperty.write(self.menu_enable_global_hotkey_shortcut, "checked", False)
            return

        Settings.set('global_hotkey_enabled', enabled)

    def _menu_toggle_tray_icon(self, enabled: bool) -> None:
        Settings.set('tray', enabled)
        try:
            self.tray.show() if enabled else self.tray.hide()  # type: ignore
        except AttributeError:
            pass

    def _menu_install_quick_action_service(self) -> None:
        new_path = os.path.join(ConfigRetriever.get_temp_path(), 'Pext.workflow')
        try:
            rmtree(new_path)
        except IOError:
            pass
        copytree(os.path.join(AppFile.get_path(), 'Pext.workflow'), new_path)
        Popen(['open', new_path])

    def _menu_toggle_update_check(self, enabled: bool) -> None:
        Settings.set('update_check', enabled)
        QQmlProperty.write(self.menu_enable_update_check_shortcut,
                           "checked",
                           Settings.get('update_check'))

        # Check for updates immediately after toggling true
        self._menu_check_updates(verbose=False, manual=False)

    def _menu_toggle_object_update_check(self, enabled: bool) -> None:
        Settings.set('object_update_check', enabled)
        QQmlProperty.write(self.menu_enable_object_update_check_shortcut,
                           "checked",
                           Settings.get('object_update_check'))
        if not enabled:
            self._menu_toggle_object_update_install(False)

    def _menu_toggle_object_update_install(self, enabled: bool) -> None:
        Settings.set('object_update_install', enabled)
        QQmlProperty.write(self.menu_enable_object_update_install_shortcut,
                           "checked",
                           Settings.get('object_update_install'))

    def _search(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].search(manual=True)
            except TypeError:
                pass

    def _select(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].select()
            except TypeError:
                pass

    def _tab_complete(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].tab_complete()
            except TypeError:
                pass

    def _input_args(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element['vm'].input_args()
            except TypeError:
                pass

    def _update_modules_info_qml(self) -> None:
        modules = self.module_manager.list()
        self.context.setContextProperty(
            "modules", modules)
        QQmlProperty.write(
            self.intro_screen, "modulesInstalledCount", len(modules.keys()))

    def _update_themes_info_qml(self) -> None:
        themes = self.theme_manager.list()
        self.context.setContextProperty(
            "themes", themes)

    def _update_profiles_info_qml(self) -> None:
        profiles = self.profile_manager.list_profiles()
        self.context.setContextProperty(
            "profiles", profiles)

    def _menu_check_updates_actually_check(self, verbose=True) -> None:
        if verbose:
            Logger.log(None, Translation.get("checking_for_pext_updates"))

        try:
            new_version = UpdateManager().check_core_update()
        except Exception as e:
            Logger.log_error(None, Translation.get("failed_to_check_for_pext_updates").format(e))
            traceback.print_exc()

            return

        if new_version:
            self.add_actionable(
                "pext_update_available",
                Translation.get("actionable_update_available").format(new_version, UpdateManager().get_core_version()),
                Translation.get("actionable_update_available_button"),
                "https://pext.io/download/")
        else:
            if verbose:
                Logger.log(None, Translation.get("pext_is_already_up_to_date"))

    def _menu_check_updates(self, verbose=True, manual=True) -> None:
        # Set a timer to run this function again in an hour
        if not manual:
            t = threading.Timer(3600, self._menu_check_updates, None, {'verbose': False, 'manual': False})
            t.daemon = True
            t.start()

        # Check if it's been over 24 hours or this is a manual/first check
        last_update_check = Settings.get('last_update_check')

        if manual or last_update_check is None or (time.time() - float(last_update_check) > 86400):
            if USE_INTERNAL_UPDATER:
                if manual or Settings.get('update_check'):
                    threading.Thread(target=self._menu_check_updates_actually_check, args=(verbose,)).start()

            if manual or Settings.get('object_update_check'):
                if Settings.get('object_update_install'):
                    for module_id, data in self.module_manager.list().items():
                        self._menu_update_module(module_id)

                    self._menu_update_all_themes(verbose)
                else:
                    for module_id, data in self.module_manager.list().items():
                        if self.module_manager.has_update(module_id):
                            self.add_actionable(
                                "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                                Translation.get("actionable_object_update_available").format(
                                    data['metadata']['name']),  # type: ignore
                                Translation.get("actionable_object_update_available_button"),
                                "pext:update-module-in-use:{}".format(module_id)
                            )
                    for theme_id, data in self.theme_manager.list().items():
                        if self.theme_manager.has_update(theme_id):
                            self.add_actionable(
                                "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                                Translation.get("actionable_object_update_available").format(
                                    data['metadata']['name']),  # type: ignore
                                Translation.get("actionable_object_update_available_button"),
                                "pext:update-theme:{}".format(module_id)
                            )

            Settings.set('last_update_check', time.time())

    def _show_homepage(self) -> None:
        webbrowser.open('https://pext.io/')

    def _remove_actionable(self, index: int) -> None:
        self.actionables.pop(index)
        QQmlProperty.write(self.window, 'actionables', self.actionables)

    def disable_module(self, tab_id: int, reason: int) -> None:
        """Disable a module by tab ID.

        Valid reasons:
        1: Crash
        2: Update
        """
        self.tabs.disableRequest.emit(tab_id, reason)

    def update_state(self, tab_id: int, state: str) -> None:
        """Update a module's state by tab ID.

        This adds an entry to display in the module's disabled screen.

        Used for showing installation, update progress or module crashes.
        """
        self.tabs.updateStateRequest.emit(tab_id, state)

    def add_actionable(self, identifier: str, text: str, button_text=None, button_url=None, urgency="medium") -> None:
        """Add an action to show in the UI."""
        new_actionable = {
            'identifier': identifier,
            'text': text,
            'buttonText': button_text if button_text else "",
            'buttonUrl': button_url if button_url else "",
            'urgency': urgency
        }

        for index, actionable in enumerate(self.actionables):
            if actionable['identifier'] == identifier:
                self.actionables[index] = new_actionable
                break
        else:
            self.actionables.insert(0, new_actionable)

        QQmlProperty.write(self.window, 'actionables', self.actionables)

    def bind_tray(self, tray: 'Tray') -> None:
        """Bind the tray to the window."""
        self.tray = tray

        if Settings.get('tray'):
            tray.show()

    def close(self, manual=False, force_tray=False) -> None:
        """Close the window."""
        if self.app.platformName() in ['webgl', 'vnc']:
            return

        if force_tray:
            if self.tray:
                self.tray.show()

            self.window.hide()
        else:
            if (not manual
                    and Settings.get('minimize_mode') in [MinimizeMode.NormalManualOnly, MinimizeMode.TrayManualOnly]):
                return

            if Settings.get('minimize_mode') in [MinimizeMode.Normal, MinimizeMode.NormalManualOnly]:
                self.window.showMinimized()
            else:
                self.window.hide()

        self._macos_focus_workaround()

        if self.output_queue:
            output_mode = Settings.get('output_mode')
            if output_mode == OutputMode.AutoType:
                time.sleep(0.5)
                keyboard_device = keyboard.Controller()

                while True:
                    try:
                        output = self.output_queue.pop(0)
                    except IndexError:
                        Logger.log(None, Translation.get("queued_data_typed"))
                        break

                    if platform.system() == "Darwin":
                        # https://github.com/moses-palmer/pynput/issues/83#issuecomment-410264758
                        typewrite(output)
                    else:
                        keyboard_device.type(output)

                    if self.output_queue:
                        separator_key = Settings.get('output_separator')
                        if separator_key == OutputSeparator.None_:
                            continue

                        if platform.system() == "Darwin":
                            if separator_key == OutputSeparator.Tab:
                                hotkey('tab')
                            elif separator_key == OutputSeparator.Enter:
                                hotkey('return')
                        else:
                            if separator_key == OutputSeparator.Tab:
                                key = keyboard.Key.tab
                            elif separator_key == OutputSeparator.Enter:
                                key = keyboard.Key.enter

                            keyboard_device.press(key)
                            keyboard_device.release(key)
            else:
                if output_mode == OutputMode.SelectionClipboard:
                    mode = QClipboard.Selection
                elif output_mode == OutputMode.FindBuffer:
                    mode = QClipboard.FindBuffer
                else:
                    mode = QClipboard.Clipboard

                separator_key = Settings.get('output_separator')
                if separator_key == OutputSeparator.Tab:
                    join_string = "\t"
                elif separator_key == OutputSeparator.Enter:
                    join_string = os.linesep
                else:
                    join_string = ""

                self.app.clipboard().setText(str(join_string.join(self.output_queue)), mode)

                Logger.log(None, Translation.get("data_copied_to_clipboard"))

                self.output_queue = []

    def show(self) -> None:
        """Show the window."""
        if self.tray:
            if Settings.get('tray'):
                self.tray.show()
            else:
                self.tray.hide()

        if self.window.windowState() == Qt.WindowMinimized:
            self.window.showNormal()
        else:
            self.window.show()

        self.window.raise_()

    def switch_tab(self, tab_id) -> None:
        """Switch the active tab."""
        QQmlProperty.write(self.tabs, "currentIndex", tab_id)

    def toggle_visibility(self, force_tray=False) -> None:
        """Toggle window visibility."""
        if self.window.windowState() == Qt.WindowMinimized or not self.window.isVisible():
            self.show()
        else:
            self.close(force_tray=force_tray)

    def quit(self) -> None:
        """Quit."""
        geometry = self.window.geometry()
        Settings.set('_window_geometry',
                     "{};{};{};{}".format(geometry.x(), geometry.y(), geometry.width(), geometry.height()))
        sys.exit(0)


class SignalHandler():
    """Handle UNIX signals."""

    def __init__(self, window: Window) -> None:
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum: int, frame) -> None:
        """When an UNIX signal gets received, show the window."""
        self.window.show()


class ThemeManager():
    """Manages the theme."""

    def __init__(self) -> None:
        """Initialize the module manager."""
        self.theme_dir = os.path.join(ConfigRetriever.get_path(), 'themes')

    def _get_palette_mappings(self) -> Dict[str, Dict[str, str]]:
        mapping = {'colour_roles': {}, 'colour_groups': {}}  # type: Dict[str, Dict[str, str]]
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

    def install(self, url: str, identifier: str, name: str, verbose=False, interactive=True) -> bool:
        """Install a theme."""
        theme_path = os.path.join(self.theme_dir, identifier.replace('.', '_'))

        if os.path.exists(theme_path):
            if verbose:
                Logger.log(None, Translation.get("already_installed").format(name))

            return False

        if verbose:
            Logger.log(None, Translation.get("downloading_from_url").format(name, url))

        try:
            porcelain.clone(UpdateManager.fix_git_url_for_dulwich(url), theme_path)
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
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(theme_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
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
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
            name = identifier

        try:
            with open(os.path.join(theme_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                name = json.load(metadata_json_i18n)['name']
        except (FileNotFoundError, IndexError, json.decoder.JSONDecodeError):
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


class Tray():
    """Handle the system tray."""

    def __init__(self, window: Window, app_icon: str) -> None:
        """Initialize the system tray."""
        self.window = window

        self.tray = QSystemTrayIcon(app_icon)
        self.tray.activated.connect(self.icon_clicked)
        self.tray.setToolTip(QQmlProperty.read(self.window.window, "title"))

        self.window.tabs.currentIndexChanged.connect(self._update_context_menu)
        self._update_context_menu()

    def _update_context_menu(self) -> None:
        """Update the context menu to list the loaded modules."""
        tray_menu = QMenu()
        tray_menu_item = QAction(QQmlProperty.read(self.window.window, "title"), tray_menu)
        tray_menu_item.triggered.connect(self.window.show)
        tray_menu.addAction(tray_menu_item)
        if len(self.window.tab_bindings) > 0:
            tray_menu.addSeparator()

        for tab_id, tab in enumerate(self.window.tab_bindings):
            tray_menu_item = QAction(tab['metadata']['name'], tray_menu)
            tray_menu_item.triggered.connect(partial(
                lambda tab_id: [self.window.switch_tab(tab_id), self.window.show()], tab_id=tab_id))  # type: ignore
            tray_menu.addAction(tray_menu_item)

        self.tray.setContextMenu(tray_menu)

    def icon_clicked(self, reason: int) -> None:
        """Toggle window visibility on left click."""
        if reason == 3 and platform.system() != "Darwin":
            self.window.toggle_visibility(force_tray=True)

    def show(self) -> None:
        """Show the tray icon."""
        self.tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        self.tray.hide()


class HotkeyHandler():
    """Handles global hotkey presses."""

    def __init__(self, main_loop_queue: Queue, window: Window) -> None:
        """Initialize the global hotkey handler."""
        self.window = window
        self.modifiers = set()  # type: Set[Union[keyboard.Key, keyboard.KeyCode]]
        self.backtick = keyboard.KeyCode(char='`')
        self.main_loop_queue = main_loop_queue

        self.modifier_keys = [
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.Key.alt,
            keyboard.Key.cmd
        ]

        if not pynput_error:
            listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            listener.start()

    def on_press(self, key) -> bool:
        """Executed when a key is pressed."""
        if key is None:
            return True

        if key in self.modifier_keys:
            self.modifiers.add(key)
        elif (key == self.backtick and
              len(self.modifiers) == 1 and
              keyboard.Key.ctrl in self.modifiers and
              Settings.get('global_hotkey_enabled')):
            self.main_loop_queue.put(self.window.show)

        return True

    def on_release(self, key) -> bool:
        """Executed when a key is released."""
        try:
            self.modifiers.remove(key)
        except KeyError:
            pass

        return True


class Settings():
    """A globally accessible class that stores all Pext's settings."""

    __settings = {
        '_launch_app': True,  # Keep track if launching is normal
        '_window_geometry': None,
        '_portable': False,
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


def _shut_down(window: Window) -> None:
    """Clean up."""
    profile = Settings.get('profile')
    ProfileManager().save_modules(profile, window.tab_bindings)

    for module in window.tab_bindings:
        try:
            module['vm'].stop()
        except Exception as e:
            print("Failed to cleanly stop module {}: {}".format(module['metadata']['name'], e))
            traceback.print_exc()

    ProfileManager.unlock_profile(profile)


def main() -> None:
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

    # Warn if we may get UI issues
    if warn_no_openGL_linux:
        print("python3-opengl is not installed. If Pext fails to render, please try installing it. "
              "See https://github.com/Pext/Pext/issues/11.")

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

    app.setWindowIcon(app_icon)

    if Settings.get('style') is not None:
        app.setStyle(QStyleFactory().create(Settings.get('style')))

    # Qt5's default style for macOS seems to have sizing bugs for buttons, so
    # we force the Fusion theme instead
    if platform.system() == 'Darwin':
        app.setStyle(QStyleFactory().create('Fusion'))

    # Create managers
    module_manager = ModuleManager()
    theme_manager = ThemeManager()

    theme_identifier = Settings.get('theme')
    if theme_identifier is not None:
        # Qt5's default style for Windows, windowsvista, does not support palettes properly
        # If the user doesn't explicitly chose a style, but wants theming, we force
        # it to use Fusion, which gets themed properly
        if platform.system() == 'Windows' and Settings.get('style') is None:
            app.setStyle(QStyleFactory().create('Fusion'))

        theme = theme_manager.load(theme_identifier)
        theme_manager.apply(theme, app)

    # Get a window
    window = Window(app, locale_manager, module_manager, theme_manager)

    # Prepare InternalCallProcessor
    InternalCallProcessor.bind(window, module_manager, theme_manager)

    # Give the logger a reference to the window
    Logger.bind_window(window)

    # Clean up on exit
    atexit.register(_shut_down, window)

    # Handle SIGUSR1 UNIX signal
    signal_handler = SignalHandler(window)
    if not platform.system() == 'Windows':
        signal.signal(signal.SIGUSR1, signal_handler.handle)

    # Start handling the global hotkey
    main_loop_queue = Queue()  # type: Queue[Callable[[], None]]
    HotkeyHandler(main_loop_queue, window)

    # Create a main loop
    main_loop = MainLoop(app, window, main_loop_queue)

    # Create a tray icon
    # This needs to be stored in a variable to prevent the Python garbage collector from removing the Qt tray
    tray = Tray(window, app_icon)  # noqa: F841

    # Give the window a reference to the tray
    window.bind_tray(tray)

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
    main()
