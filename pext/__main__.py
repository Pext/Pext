#!/usr/bin/env python3

# Copyright (c) 2016 Sylvia van Os <iamsylvie@openmailbox.org>
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
import configparser
import getopt
import os
import signal
import sys
import threading
import time
from importlib import reload  # type: ignore
from shutil import rmtree
from subprocess import check_call, check_output, CalledProcessError, Popen, PIPE
from typing import Dict, List, Optional, Tuple
from queue import Queue, Empty

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QTextEdit, QVBoxLayout)
from PyQt5.Qt import QObject, QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlProperty, QUrl


class AppFile():
    """Get access to application-specific files."""

    @staticmethod
    def getPath(name: str) -> str:
        """Return the absolute path by file or directory name."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(AppFile.getPath('helpers'))

from pext_base import ModuleBase  # noqa: E402
from pext_helpers import Action, SelectionType  # noqa: E402


class VersionRetriever():
    """Retrieve general information."""

    @staticmethod
    def getVersion() -> str:
        """Return the version information and cache it."""
        with open(AppFile.getPath('VERSION')) as version_file:
            return version_file.read().strip()


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
        self.textEdit = QTextEdit(self)
        self.textEdit.setPlainText(text)
        layout.addWidget(self.textEdit)
        button = QDialogButtonBox(QDialogButtonBox.Ok)
        button.accepted.connect(self.accept)
        layout.addWidget(button)

    def show(self) -> Tuple[str, bool]:
        """Show the dialog."""
        result = self.exec_()
        return (self.textEdit.toPlainText(), result == QDialog.Accepted)


class Logger():
    """Log events to the appropriate location.

    Shows events in the main window and, if the main window is not visible,
    as a desktop notification.
    """

    def __init__(self, window: 'Window') -> None:
        """Initialize the logger and add a status bar to the main window."""
        self.window = window
        self.queuedMessages = []  # type: List[Dict[str, str]]

        self.lastUpdate = None  # type: Optional[float]
        self.statusText = self.window.window.findChild(QObject, "statusText")
        self.statusQueue = self.window.window.findChild(QObject, "statusQueue")

    def _queueMessage(self, moduleName: str, message: str, typeName: str) -> None:
        """Queue a message for display."""
        for formattedMessage in self._formatMessage(moduleName, message):
            self.queuedMessages.append({'message': formattedMessage, 'type': typeName})

    def _formatMessage(self, moduleName: str, message: str) -> List[str]:
        """Format message for display, including splitting multiline messages."""
        messageLines = []
        for line in message.splitlines():
            if not (not line or line.isspace()):
                if moduleName:
                    message = '{}: {}'.format(moduleName, line)
                else:
                    message = line

                messageLines.append(message)

        return messageLines

    def showNextMessage(self) -> None:
        """Show next statusbar message.

        If the status bar has not been updated for 1 second, display the next
        message. If no messages are available, clear the status bar after it
        has been displayed for 5 seconds.
        """
        currentTime = time.time()
        timeDiff = 5 if len(self.queuedMessages) < 1 else 1
        if self.lastUpdate and currentTime - timeDiff < self.lastUpdate:
            return

        if len(self.queuedMessages) == 0:
            QQmlProperty.write(self.statusText, "text", "")
            self.lastUpdate = None
        else:
            message = self.queuedMessages.pop(0)

            if message['type'] == 'error':
                statusBarMessage = "<font color='red'>{}</color>".format(message['message'])
                notificationMessage = 'error: {}'.format(message['message'])
            else:
                statusBarMessage = message['message']
                notificationMessage = message['message']

            QQmlProperty.write(self.statusText, "text", statusBarMessage)

            if not self.window.window.isVisible():
                Popen(['notify-send', 'Pext', notificationMessage])

            self.lastUpdate = currentTime

    def addError(self, moduleName: str, message: str) -> None:
        """Add an error message to the queue."""
        self._queueMessage(moduleName, message, 'error')

    def addMessage(self, moduleName: str, message: str) -> None:
        """Add a regular message to the queue."""
        self._queueMessage(moduleName, message, 'message')

    def setQueueCount(self, count: List[int]) -> None:
        """Show the queue size on screen."""
        if (count[0] == 0 and count[1] == 0):
            QQmlProperty.write(self.statusQueue, "text", "Ready")
        else:
            QQmlProperty.write(self.statusQueue, "text", "Processing: {} ({})".format(count[0], count[1]))


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

    def _processTabAction(self, tab: Dict, activeTab: int) -> None:
        action = tab['queue'].get_nowait()

        if action[0] == Action.criticalError:
            self.logger.addError(tab['moduleName'], action[1])
            tabId = self.window.tabBindings.index(tab)
            self.window.moduleManager.unloadModule(self.window, tabId)
        elif action[0] == Action.addMessage:
            self.logger.addMessage(tab['moduleName'], action[1])
        elif action[0] == Action.addError:
            self.logger.addError(tab['moduleName'], action[1])
        elif action[0] == Action.addEntry:
            tab['vm'].entryList = tab['vm'].entryList + [action[1]]
        elif action[0] == Action.prependEntry:
            tab['vm'].entryList = [action[1]] + tab['vm'].entryList
        elif action[0] == Action.removeEntry:
            tab['vm'].entryList.remove(action[1])
        elif action[0] == Action.replaceEntryList:
            tab['vm'].entryList = action[1]
        elif action[0] == Action.addCommand:
            tab['vm'].commandList = tab['vm'].commandList + [action[1]]
        elif action[0] == Action.prependCommand:
            tab['vm'].commandList = [action[1]] + tab['vm'].commandList
        elif action[0] == Action.removeCommand:
            tab['vm'].commandList.remove(action[1])
        elif action[0] == Action.replaceCommandList:
            tab['vm'].commandList = action[1]
        elif action[0] == Action.setFilter:
            QQmlProperty.write(tab['vm'].searchInputModel, "text", action[1])
        elif action[0] == Action.askQuestionDefaultYes:
            answer = QMessageBox.question(self.window, "Pext", action[1],
                                          QMessageBox.Yes | QMessageBox.No,
                                          QMessageBox.Yes)
            tab['vm'].module.processResponse(True if (answer == QMessageBox.Yes) else False)
        elif action[0] == Action.askQuestionDefaultNo:
            answer = QMessageBox.question(self.window, "Pext", action[1],
                                          QMessageBox.Yes | QMessageBox.No,
                                          QMessageBox.No)
            tab['vm'].module.processResponse(True if (answer == QMessageBox.Yes) else False)
        elif action[0] == Action.askInput:
            answer, ok = QInputDialog.getText(self.window, "Pext", action[1])
            tab['vm'].module.processResponse(answer if ok else None)
        elif action[0] == Action.askInputPassword:
            answer, ok = QInputDialog.getText(self.window, "Pext", action[1], QLineEdit.Password)
            tab['vm'].module.processResponse(answer if ok else None)
        elif action[0] == Action.askInputMultiLine:
            dialog = InputDialog(action[1], action[2] if action[2] else "", self.window)
            answer, ok = dialog.show()
            tab['vm'].module.processResponse(answer if ok else None)
        elif action[0] == Action.copyToClipboard:
            """Copy the given data to the user-chosen clipboard."""
            proc = Popen(["xclip", "-selection", self.settings["clipboard"]], stdin=PIPE)
            proc.communicate(action[1].encode('utf-8'))
        elif action[0] == Action.setSelection:
            tab['vm'].selection = action[1]
            tab['vm'].module.selectionMade(tab['vm'].selection)
        elif action[0] == Action.notifyMessage:
            self.logger.addMessage(tab['moduleName'], action[1])
        elif action[0] == Action.notifyError:
            self.logger.addError(tab['moduleName'], action[1])
        elif action[0] == Action.close:
            self.window.close()
        else:
            print('WARN: Module requested unknown action {}'.format(action[0]))

        if activeTab and tab['entriesProcessed'] >= 100:
            tab['vm'].search(newEntries=True)
            tab['entriesProcessed'] = 0

        self.window.update()
        tab['queue'].task_done()

    def run(self) -> None:
        """Process actions modules put in the queue and keep the window working."""
        while True:
            self.app.sendPostedEvents()
            self.app.processEvents()
            self.logger.showNextMessage()

            currentTab = QQmlProperty.read(self.window.tabs, "currentIndex")
            queueSize = [0, 0]

            allEmpty = True
            for tabId, tab in enumerate(self.window.tabBindings):
                if not tab['init']:
                    continue

                if tabId == currentTab:
                    queueSize[0] = tab['queue'].qsize()
                    activeTab = True
                else:
                    queueSize[1] += tab['queue'].qsize()
                    activeTab = False

                try:
                    self._processTabAction(tab, activeTab)
                    tab['entriesProcessed'] += 1
                    allEmpty = False
                except Empty:  # type: ignore
                    if activeTab and tab['entriesProcessed']:
                        tab['vm'].search(newEntries=True)

                    tab['entriesProcessed'] = 0
                except Exception as e:
                    print('WARN: Module caused exception {}'.format(e))

            self.logger.setQueueCount(queueSize)

            if allEmpty:
                if self.window.window.isVisible():
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)

class ProfileManager():
    """Create, remove, list, load and save to a profile."""

    def __init__(self) -> None:
        """Initialize the profile manager."""
        self.profileDir = os.path.expanduser('~/.config/pext/profiles/')

    def createProfile(self, profile: str) -> None:
        os.mkdir('{}/{}'.format(self.profileDir, profile))

    def removeProfile(self, profile: str) -> None:
        rmtree('{}/{}'.format(self.profileDir, profile))

    def listProfiles(self) -> List:
        return os.listdir(os.path.expanduser('~/.config/pext/profiles/'))

    def saveModules(self, profile: str, modules: List[Dict]) -> None:
        config = configparser.ConfigParser()
        for number, module in enumerate(modules):
            name = ModuleManager.addPrefix(module['moduleName'])
            config['{}_{}'.format(number, name)] = module['settings']

        with open('{}/{}/modules'.format(self.profileDir, profile), 'w') as configfile:
            config.write(configfile)

    def retrieveModules(self, profile: str) -> List[Dict]:
        config = configparser.ConfigParser()
        modules = []

        config.read('{}/{}/modules'.format(self.profileDir, profile))

        for module in config.sections():
            settings = {}

            for key in config[module]:
                settings[key] = config[module][key]

            modules.append({'name': module.split('_', 1)[1], 'settings': settings})

        return modules

class ModuleManager():
    """Install, remove, update and list modules."""

    def __init__(self) -> None:
        """Initialize the module manager."""
        self.moduleDir = os.path.expanduser('~/.config/pext/modules/')
        self.logger = None  # type: Optional[Logger]

    @staticmethod
    def addPrefix(moduleName: str) -> str:
        """Ensure the string starts with pext_module_."""
        if not moduleName.startswith('pext_module_'):
            return 'pext_module_{}'.format(moduleName)

        return moduleName

    @staticmethod
    def removePrefix(moduleName: str) -> str:
        """Remove pext_module_ from the start of the string."""
        if moduleName.startswith('pext_module_'):
            return moduleName[len('pext_module_'):]

        return moduleName

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.addMessage("", message)
        else:
            print(message)

    def _logError(self, message: str) -> None:
        if self.logger:
            self.logger.addError("", message)
        else:
            print(message)

    def bindLogger(self, logger: Logger) -> str:
        """Connect a logger to the module manager.

        If a logger is connected, the module manager will log all
        messages directly to the logger.
        """
        self.logger = logger

    def loadModule(self, window: 'Window', module: Dict) -> bool:
        """Load a module and attach it to the main window."""
        # Append modulePath if not yet appendend
        modulePath = os.path.expanduser('~/.config/pext/modules')
        if modulePath not in sys.path:
            sys.path.append(modulePath)

        # Remove pext_module_ from the module name
        moduleDir = ModuleManager.addPrefix(module['name']).replace('.', '_')
        moduleName = ModuleManager.removePrefix(module['name'])

        # Prepare viewModel and context
        vm = ViewModel()
        moduleContext = QQmlContext(window.context)
        moduleContext.setContextProperty("resultListModel", vm.resultListModelList)
        moduleContext.setContextProperty("resultListModelMaxIndex", vm.resultListModelMaxIndex)
        moduleContext.setContextProperty("resultListModelCommandMode", False)

        # Prepare module
        try:
            moduleImport = __import__(moduleDir, fromlist=['Module'])
        except ImportError as e1:
            self._logError("Failed to load module {} from {}: {}".format(moduleName, moduleDir, e1))
            return False

        Module = getattr(moduleImport, 'Module')

        # Ensure the module implements the base
        assert issubclass(Module, ModuleBase)

        # Set up a queue so that the module can communicate with the main thread
        q = Queue()  # type: Queue

        # This will (correctly) fail if the module doesn't implement all necessary
        # functionality
        try:
            moduleCode = Module()
        except TypeError as e2:
            self._logError("Failed to load module {} from {}: {}".format(moduleName, moduleDir, e2))
            return False

        # Start the module in the background
        moduleThread = ModuleThreadInitializer(moduleName, q, target=moduleCode.init, args=(module['settings'], q))
        moduleThread.start()

        # Add tab
        tabData = QQmlComponent(window.engine)
        tabData.loadUrl(QUrl.fromLocalFile(AppFile.getPath('ModuleData.qml')))
        window.engine.setContextForObject(tabData, moduleContext)
        window.tabs.addTab(moduleName, tabData)

        # Store tab/viewModel combination
        # tabData is not used but stored to prevent segfaults caused by
        # Python garbage collecting it
        window.tabBindings.append({'init': False,
                                   'queue': q,
                                   'vm': vm,
                                   'module': moduleCode,
                                   'moduleContext': moduleContext,
                                   'moduleImport': moduleImport,
                                   'moduleName': moduleName,
                                   'tabData': tabData,
                                   'settings': module['settings'],
                                   'entriesProcessed': 0})

        # Open tab to trigger loading
        QQmlProperty.write(window.tabs, "currentIndex", QQmlProperty.read(window.tabs, "count") - 1)

        return True

    def unloadModule(self, window: 'Window', tabId: int) -> None:
        """Unload a module by tab ID."""
        window.tabBindings[tabId]['module'].stop()

        if QQmlProperty.read(window.tabs, "currentIndex") == tabId:
            tabCount = QQmlProperty.read(window.tabs, "count")
            if tabId + 1 < tabCount:
                QQmlProperty.write(window.tabs, "currentIndex", tabId + 1)
            else:
                QQmlProperty.write(window.tabs, "currentIndex", "0")

        del window.tabBindings[tabId]
        window.tabs.removeTab(tabId)

    def listModules(self) -> List[List[str]]:
        """Return a list of modules together with their source."""
        modules = []

        for directory in os.listdir(self.moduleDir):
            name = ModuleManager.removePrefix(directory)
            try:
                source = check_output(['git', 'config', '--get', 'remote.origin.url'],
                                      cwd=os.path.join(self.moduleDir, directory),
                                      universal_newlines=True).strip()

            except (CalledProcessError, FileNotFoundError):
                source = "Unknown"

            modules.append([name, source])

        return modules

    def reloadModule(self, window: 'Window', tabId: int) -> bool:
        """Reload a module by tab ID."""
        # Get currently active tab
        currentIndex = QQmlProperty.read(window.tabs, "currentIndex")

        # Get the needed info to load the module
        moduleData = window.tabBindings[tabId]
        module = {'name': moduleData['moduleName'], 'settings': moduleData['settings']}

        # Unload the module
        self.unloadModule(window, tabId)

        # Force a reload to make code changes happen
        reload(moduleData['moduleImport'])

        # Load it into the UI
        if not self.loadModule(window, module):
            return False

        # Get new position
        newTabId = len(window.tabBindings) - 1

        # Move to correct position if there is more than 1 tab
        if newTabId > 0:
            window.tabs.moveTab(newTabId, tabId)
            window.tabBindings.insert(tabId, window.tabBindings.pop(newTabId))

            # Focus on active tab
            QQmlProperty.write(window.tabs, "currentIndex", str(currentIndex))
        else:
            # Ensure the event gets called if there's only one tab
            window.tabs.currentIndexChanged.emit()

        return True

    def installModule(self, url: str, verbose=False, interactive=True) -> bool:
        """Install a module."""
        moduleName = url.split("/")[-1]

        dirName = ModuleManager.addPrefix(moduleName).replace('.', '_')
        moduleName = ModuleManager.removePrefix(moduleName)

        if verbose:
            self._log('Installing {} from {}'.format(moduleName, url))

        returnCode = Popen(['git', 'clone', url, dirName],
                           cwd=self.moduleDir,
                           env={'GIT_ASKPASS': 'true'} if not interactive else None).wait()

        if returnCode != 0:
            if verbose:
                self._logError('Failed to install {}'.format(moduleName))

            return False

        if verbose:
            self._log('Installed {}'.format(moduleName))

        return True

    def uninstallModule(self, moduleName: str, verbose=False) -> bool:
        """Uninstall a module."""
        dirName = ModuleManager.addPrefix(moduleName)
        moduleName = ModuleManager.removePrefix(moduleName)

        if verbose:
            self._log('Removing {}'.format(moduleName))

        try:
            rmtree(os.path.join(self.moduleDir, dirName))
        except FileNotFoundError:
            if verbose:
                self._logError('Cannot remove {}, it is not installed'.format(moduleName))

            return False

        if verbose:
            self._log('Uninstalled {}'.format(moduleName))

        return True

    def updateModule(self, moduleName: str, verbose=False) -> bool:
        """Update a module."""
        dirName = ModuleManager.addPrefix(moduleName)
        moduleName = ModuleManager.removePrefix(moduleName)

        if verbose:
            self._log('Updating {}'.format(moduleName))

        try:
            check_call(['git', 'pull'], cwd=os.path.join(self.moduleDir, dirName))
        except Exception as e:
            if verbose:
                self._logError('Failed to update {}: {}'.format(moduleName, e))

            return False

        if verbose:
            self._log('Updated {}'.format(moduleName))

        return True

    def updateAllModules(self, verbose=False) -> None:
        """Update all modules."""
        for module in self.listModules():
            self.updateModule(module[0], verbose=verbose)


class ModuleThreadInitializer(threading.Thread):
    """Initialize a thread for the module."""

    def __init__(self, moduleName: str, q: Queue, target=None, args=()) -> None:
        """Initialize the module thread initializer."""
        self.moduleName = moduleName
        self.queue = q
        threading.Thread.__init__(self, target=target, args=args)

    def run(self) -> None:
        """Start the module's thread.

        The thread will run forever, until an exception is thrown. If an
        exception is thrown, an Action.criticalError is appended to the
        queue.
        """
        try:
            threading.Thread.run(self)
        except Exception as e:
            self.queue.put([Action.criticalError, "Exception thrown: {}".format(e)])


class ViewModel():
    """Manage the communication between user interface and module."""

    def __init__(self) -> None:
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self.commandList = []  # type: List
        self.entryList = []  # type: List
        self.filteredEntryList = []  # type: List
        self.filteredCommandList = []  # type: List
        self.resultListModelList = QStringListModel()
        self.resultListModelMaxIndex = -1
        self.resultListModelCommandMode = False
        self.selection = []  # type: List[Dict[SelectionType, str]]
        self.lastSearch = ""

    def _getLongestCommonString(self, entries: List[str], start="") -> Optional[str]:
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
        entryList = []
        for entry in entries:
            if entry.startswith(start):
                entryList.append(entry)

        commonChars = list(start)

        try:
            while True:
                commonChar = None
                for entry in entryList:
                    if commonChar is None:
                        commonChar = entry[len(commonChars)]
                    elif commonChar != entry[len(commonChars)]:
                        return ''.join(commonChars)

                if commonChar is None:
                    return None

                commonChars.append(commonChar)
        except IndexError:
            # We fully match a string
            return ''.join(commonChars)

    def bindContext(self, queue: Queue, context: QQmlContext, window: 'Window', searchInputModel: QObject, resultListModel: QObject) -> None:  # noqa: E646
        """Bind the QML context so we can communicate with the QML front-end."""
        self.queue = queue
        self.context = context
        self.window = window
        self.searchInputModel = searchInputModel
        self.resultListModel = resultListModel

    def bindModule(self, module: ModuleBase) -> None:
        """Bind the module.

        This ensures we can call functions in it.
        """
        self.module = module

    def goUp(self) -> None:
        """Go one level up.

        This means that, if we're currently in the entry content list, we go
        back to the entry list. If we're currently in the entry list, we clear
        the search bar. If we're currently in the entry list and the search bar
        is empty, we tell the window to hide/close itself.
        """
        if QQmlProperty.read(self.searchInputModel, "text") != "":
            QQmlProperty.write(self.searchInputModel, "text", "")
            return

        if len(self.selection) > 0:
            self.selection.pop()
            self.module.selectionMade(self.selection)
        else:
            self.window.close()

    def search(self, newEntries=False) -> None:
        """Filter the entry list.

        Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        searchString = QQmlProperty.read(self.searchInputModel, "text").lower()

        # Don't search if nothing changed
        if not newEntries and searchString == self.lastSearch:
            return

        # If empty, show all
        if len(searchString) == 0 and not newEntries:
            self.filteredEntryList = self.entryList
            combinedList = self.entryList + self.commandList
            self.resultListModelList = QStringListModel([str(entry) for entry in combinedList])
            self.resultListModelMaxIndex = len(self.entryList) - 1
            self.context.setContextProperty("resultListModelCommandMode", False)
            self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)
            self.context.setContextProperty("resultListModel", self.resultListModelList)

            # Enable checking for changes next time
            self.lastSearch = searchString

            return

        searchStrings = searchString.split(" ")

        # If longer and no new entries, only filter existing list
        if len(searchString) > len(self.lastSearch) and not (self.resultListModelCommandMode and
                                                             len(searchStrings) == 2 and searchStrings[1] == ""):

            filterEntryList = self.filteredEntryList
            filterCommandList = self.filteredCommandList
        else:
            filterEntryList = self.entryList
            filterCommandList = self.commandList

        self.filteredEntryList = []
        self.filteredCommandList = []

        self.resultListModelCommandMode = False

        for command in filterCommandList:
            if searchStrings[0] in command:
                if searchStrings[0] == command.split(" ", 1)[0]:
                    self.resultListModelCommandMode = True

                self.filteredCommandList.append(command)

        if self.resultListModelCommandMode:
            for entry in filterEntryList:
                if all(searchString in str(entry).lower() for searchString in searchStrings[1:]):
                    self.filteredEntryList.append(entry)

            combinedList = self.filteredCommandList + self.filteredEntryList
        else:
            for entry in filterEntryList:
                if all(searchString in str(entry).lower() for searchString in searchStrings):
                    self.filteredEntryList.append(entry)

            combinedList = self.filteredEntryList + self.filteredCommandList

        self.context.setContextProperty("resultListModelCommandMode", self.resultListModelCommandMode)

        self.resultListModelMaxIndex = len(self.filteredEntryList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)

        self.resultListModelList = QStringListModel([str(entry) for entry in combinedList])
        self.context.setContextProperty("resultListModel", self.resultListModelList)

        # Enable checking for changes next time
        self.lastSearch = searchString

    def select(self) -> None:
        """Notify the module of our selection entry."""
        if len(self.filteredEntryList + self.filteredCommandList) == 0 or self.queue.qsize() > 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")

        if self.resultListModelCommandMode or len(self.filteredEntryList) == 0:
            commandTyped = QQmlProperty.read(self.searchInputModel, "text")

            self.selection.append({'type': SelectionType.command, 'value': commandTyped})
            self.module.selectionMade(self.selection)

            QQmlProperty.write(self.searchInputModel, "text", "")

            return

        entry = self.filteredEntryList[currentIndex]
        self.selection.append({'type': SelectionType.entry, 'value': entry})
        self.module.selectionMade(self.selection)
        QQmlProperty.write(self.searchInputModel, "text", "")

    def tabComplete(self) -> None:
        """Tab-complete based on the current seach input.

        This tab-completes the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        currentInput = QQmlProperty.read(self.searchInputModel, "text")

        start = currentInput

        possibles = currentInput.split(" ", 1)
        command = self._getLongestCommonString([command.split(" ", 1)[0] for command in self.commandList],
                                               start=possibles[0])
        # If we didn't complete the command, see if we can complete the text
        if command is None or len(command) == len(possibles[0]):
            if command is None:
                command = ""  # We string concat this later
            else:
                command += " "

            start = possibles[1] if len(possibles) > 1 else ""
            entry = self._getLongestCommonString([listEntry for listEntry in self.filteredEntryList
                                                  if listEntry not in self.commandList],
                                                 start=start)

            if entry is None or len(entry) <= len(start):
                self.queue.put([Action.addError, "No tab completion possible"])
                return
        else:
            entry = " "  # Add an extra space to simplify typing for the user

        QQmlProperty.write(self.searchInputModel, "text", command + entry)
        self.search()


class Window(QMainWindow):
    """The main Pext window."""

    def __init__(self, settings: Dict, parent=None) -> None:
        """Initialize the window."""
        super().__init__(parent)

        # Save settings
        self.settings = settings

        self.tabBindings = []  # type: List[Dict]

        self.engine = QQmlApplicationEngine(self)

        self.context = self.engine.rootContext()

        # Load the main UI
        self.engine.load(QUrl.fromLocalFile(AppFile.getPath('main.qml')))

        self.window = self.engine.rootObjects()[0]

        # Give intro screen the module count
        self.introScreen = self.window.findChild(QObject, "introScreen")
        self.moduleManager = ModuleManager()
        self._updateModulesInstalledCount()

        # Bind global shortcuts
        self.searchInputModel = self.window.findChild(QObject, "searchInputModel")
        escapeShortcut = self.window.findChild(QObject, "escapeShortcut")
        tabShortcut = self.window.findChild(QObject, "tabShortcut")
        openTabShortcut = self.window.findChild(QObject, "openTabShortcut")
        closeTabShortcut = self.window.findChild(QObject, "closeTabShortcut")
        reloadModuleShortcut = self.window.findChild(QObject, "reloadModuleShortcut")

        self.searchInputModel.textChanged.connect(self._search)
        self.searchInputModel.accepted.connect(self._select)
        escapeShortcut.activated.connect(self._goUp)
        tabShortcut.activated.connect(self._tabComplete)
        openTabShortcut.activated.connect(self._openTab)
        closeTabShortcut.activated.connect(self._closeTab)
        reloadModuleShortcut.activated.connect(self._reloadModule)

        # Bind menu entries
        menuListModulesShortcut = self.window.findChild(QObject, "menuListModules")
        menuInstallModuleShortcut = self.window.findChild(QObject, "menuInstallModule")
        menuUninstallModuleShortcut = self.window.findChild(QObject, "menuUninstallModule")
        menuUpdateModuleShortcut = self.window.findChild(QObject, "menuUpdateModule")
        menuUpdateAllModulesShortcut = self.window.findChild(QObject, "menuUpdateAllModules")
        menuAboutShortcut = self.window.findChild(QObject, "menuAbout")
        menuQuitShortcut = self.window.findChild(QObject, "menuQuit")
        menuQuitWithoutSavingShortcut = self.window.findChild(QObject, "menuQuitWithoutSaving")

        menuListModulesShortcut.triggered.connect(self._menuListModules)
        menuInstallModuleShortcut.triggered.connect(self._menuInstallModule)
        menuUninstallModuleShortcut.triggered.connect(self._menuUninstallModule)
        menuUpdateModuleShortcut.triggered.connect(self._menuUpdateModule)
        menuUpdateAllModulesShortcut.triggered.connect(self._menuUpdateAllModules)
        menuAboutShortcut.triggered.connect(self._menuAbout)
        menuQuitShortcut.triggered.connect(self._menuQuit)
        menuQuitWithoutSavingShortcut.triggered.connect(self._menuQuitWithoutSaving)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self._bindContext)

        # Show the window
        self.show()

    def _bindContext(self) -> None:
        """Bind the context for the module."""
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        element = self.tabBindings[currentTab]

        # Only initialize once, ensure filter is applied
        if element['init']:
            element['vm'].search(newEntries=True)
            return

        # Get the list
        resultListModel = self.tabs.getTab(currentTab).findChild(QObject, "resultListModel")

        # Enable mouse selection support
        resultListModel.entryClicked.connect(element['vm'].select)

        # Bind it to the viewmodel
        element['vm'].bindContext(element['queue'],
                                  element['moduleContext'],
                                  self,
                                  self.searchInputModel,
                                  resultListModel)

        element['vm'].bindModule(element['module'])

        # Done initializing
        element['init'] = True

    def _getCurrentElement(self) -> Optional[Dict]:
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        try:
            return self.tabBindings[currentTab]
        except IndexError:
            # No tabs
            return None

    def _goUp(self) -> None:
        try:
            self._getCurrentElement()['vm'].goUp()
        except TypeError:
            pass

    def _openTab(self) -> None:
        moduleList = [module[0] for module in self.moduleManager.listModules()]
        moduleName, ok = QInputDialog.getItem(self, "Pext", "Choose the module to load", moduleList, 0, False)
        if ok:
            givenSettings, ok = QInputDialog.getText(self, "Pext", "Enter module settings (leave blank for defaults)")
            if ok:
                moduleSettings = {}
                for setting in givenSettings.split(" "):
                    try:
                        key, value = setting.split("=", 2)
                    except ValueError:
                        continue

                    moduleSettings[key] = value

                module = {'name': moduleName, 'settings': moduleSettings}
                self.moduleManager.loadModule(self, module)
                # First module? Enforce load
                if len(self.tabBindings) == 1:
                    self.tabs.currentIndexChanged.emit()

    def _closeTab(self) -> None:
        if len(self.tabBindings) > 0:
            self.moduleManager.unloadModule(self, QQmlProperty.read(self.tabs, "currentIndex"))

    def _reloadModule(self) -> None:
        if len(self.tabBindings) > 0:
            self.moduleManager.reloadModule(self, QQmlProperty.read(self.tabs, "currentIndex"))

    def _menuListModules(self) -> None:
        moduleList = []  # type: List[str]
        for module in self.moduleManager.listModules():
            moduleList.append('{} ({})'.format(module[0], module[1]))
        QMessageBox.information(self, "Pext", '\n'.join(['Installed modules:'] + moduleList))

    def _menuInstallModule(self) -> None:
        moduleURI, ok = QInputDialog.getText(self, "Pext", "Enter the git URL of the module to install")
        if ok:
            functions = [
                            {
                                'name': self.moduleManager.installModule,
                                'args': (moduleURI),
                                'kwargs': {'interactive': False, 'verbose': True}
                            }, {
                                'name': self._updateModulesInstalledCount,
                                'args': (),
                                'kwargs': {}
                            }
                        ]
            threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menuUninstallModule(self) -> None:
        moduleList = [module[0] for module in self.moduleManager.listModules()]
        moduleName, ok = QInputDialog.getItem(self, "Pext", "Choose the module to uninstall", moduleList, 0, False)
        if ok:
            functions = [
                            {
                                'name': self.moduleManager.uninstallModule,
                                'args': (moduleName),
                                'kwargs': {'verbose': True}
                            }, {
                                'name': self._updateModulesInstalledCount,
                                'args': (),
                                'kwargs': {}
                            }
                        ]
            threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menuUpdateModule(self) -> None:
        moduleList = [module[0] for module in self.moduleManager.listModules()]
        moduleName, ok = QInputDialog.getItem(self, "Pext", "Choose the module to update", moduleList, 0, False)
        if ok:
            threading.Thread(target=self.moduleManager.updateModule,  # type: ignore
                             args=(moduleName,),
                             kwargs={'verbose': True}).start()

    def _menuUpdateAllModules(self) -> None:
        threading.Thread(target=self.moduleManager.updateAllModules, kwargs={'verbose': True}).start()

    def _menuAbout(self) -> None:
        aboutText = "Pext {}<br/><br/>" + \
            "Copyright &copy; 2016 Sylvia van Os<br/><br/>" + \
            "This program is free software: you can redistribute it and/or modify " + \
            "it under the terms of the GNU General Public License as published by " + \
            "the Free Software Foundation, either version 3 of the License, or " + \
            "(at your option) any later version.<br/><br/>" + \
            "This program is distributed in the hope that it will be useful, " + \
            "but WITHOUT ANY WARRANTY; without even the implied warranty of " + \
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the " + \
            "GNU General Public License for more details.<br/><br/>" + \
            "You should have received a copy of the GNU General Public License " + \
            "along with this program.  If not, see " + \
            "<a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses/</a>."

        QMessageBox.information(self, "About", aboutText.format(VersionRetriever.getVersion()))

    def _menuQuit(self) -> None:
        sys.exit(0)

    def _menuQuitWithoutSaving(self) -> None:
        self.settings['saveSettings'] = False
        self._menuQuit()

    def _search(self) -> None:
        try:
            self._getCurrentElement()['vm'].search()
        except TypeError:
            pass

    def _select(self) -> None:
        try:
            self._getCurrentElement()['vm'].select()
        except TypeError:
            pass

    def _tabComplete(self) -> None:
        try:
            self._getCurrentElement()['vm'].tabComplete()
        except TypeError:
            pass

    def _updateModulesInstalledCount(self) -> None:
        QQmlProperty.write(self.introScreen, "modulesInstalledCount", len(self.moduleManager.listModules()))

    def bindLogger(self, logger: 'Logger') -> None:
        """Bind the logger to the window and further initialize the module."""
        self.moduleManager.bindLogger(logger)

        # Now that the logger is bound, we can show messages in the window, so
        # start binding the modules
        if len(self.settings['modules']) > 0:
            for module in self.settings['modules']:
                self.moduleManager.loadModule(self, module)
        else:
            for module in ProfileManager().retrieveModules(self.settings['profile']):
                self.moduleManager.loadModule(self, module)

        # If there's only one module passed through the command line, enforce
        # loading it now. Otherwise, switch back to the first module in the
        # list
        if len(self.tabBindings) == 1:
            self.tabs.currentIndexChanged.emit()
        elif len(self.tabBindings) > 1:
            QQmlProperty.write(self.tabs, "currentIndex", "0")

    def close(self) -> None:
        """Close the window."""
        self.window.hide()
        QQmlProperty.write(self.searchInputModel, "text", "")
        for tab in self.tabBindings:
            if not tab['init']:
                continue

            tab['vm'].selection = []
            tab['vm'].module.selectionMade(tab['vm'].selection)
            tab['vm'].search()

    def show(self) -> None:
        """Show the window."""
        self.window.show()
        self.activateWindow()


class SignalHandler():
    """Handle UNIX signals."""

    def __init__(self, window: Window) -> None:
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum: int, frame) -> None:
        """When an UNIX signal gets received, show the window."""
        self.window.show()


def _initPersist(profile: str) -> str:
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


def _loadSettings(argv: List[str]) -> Dict:
    """Load the settings from the command line and set defaults."""
    # Default options
    settings = {'clipboard': 'clipboard',
                'modules': [],
                'profile': 'default',
                'saveSettings': True}

    # getopt requires all possible options to be listed, but we do not know
    # more about module-specific options in advance than that they start with
    # module-. Therefore, we go through the argument list and create a new
    # list filled with every entry that starts with module- so that getopt
    # doesn't raise getoptError for these entries.
    moduleOpts = []
    for arg in argv:
        arg = arg.split("=")[0]
        if arg.startswith("--module-"):
            moduleOpts.append(arg[2:] + "=")

    try:
        opts, args = getopt.getopt(argv, "hc:m:p:", ["help",
                                                     "version",
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
                                                     "list-profiles"] + moduleOpts)

    except getopt.GetoptError as err:
        print("{}\n".format(err))
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt == "--version":
            print("Pext {}".format(VersionRetriever.getVersion()))
            sys.exit(0)
        elif opt in ("-b", "--binary"):
            settings['binary'] = arg
        elif opt in ("-c", "--clipboard"):
            if arg not in ["primary", "secondary", "clipboard"]:
                print("Invalid clipboard requested")
                sys.exit(3)

            settings['clipboard'] = arg
        elif opt in ("-m", "--module"):
            if not arg.startswith('pext_module_'):
                arg = 'pext_module_' + arg

            settings['modules'].append({'name': arg, 'settings': {}})  # type: ignore
        elif opt.startswith("--module-"):
            settings['modules'][-1]['settings'][opt[9:]] = arg  # type: ignore
        elif opt == "--install-module":
            ModuleManager().installModule(arg, verbose=True)
        elif opt == "--uninstall-module":
            ModuleManager().uninstallModule(arg, verbose=True)
        elif opt == "--update-module":
            ModuleManager().updateModule(arg, verbose=True)
        elif opt == "--update-modules":
            ModuleManager().updateAllModules(verbose=True)
        elif opt == "--list-modules":
            for module in ModuleManager().listModules():
                print('{} ({})'.format(module[0], module[1]))
        elif opt == "--profile":
            settings['profile'] = arg
            # Create directory for profile if not existant
            try:
                ProfileManager().createProfile(arg)
            except OSError:
                pass
        elif opt == "--create-profile":
            ProfileManager().createProfile(arg)
        elif opt == "--remove-profile":
            ProfileManager().removeProfile(arg)
        elif opt == "--list-profiles":
            for profile in ProfileManager().listProfiles():
                print(profile)

    currentProfiles = ProfileManager().listProfiles()

    return settings


def _shutDown(pidfile: str, profile: str, window: Window) -> None:
    """Clean up."""
    for module in window.tabBindings:
        module['module'].stop()

    os.unlink(pidfile)
    if window.settings['saveSettings']:
        ProfileManager().saveModules(profile, window.tabBindings)


def usage() -> None:
    """Print usage information."""
    print('''Options:

--clipboard        : choose the clipboard to copy entries to. Acceptable values
                     are "primary", "secondary" or "clipboard". See the xclip
                     documentation for more information. Defaults to
                     "clipboard".

--help             : show this screen and exit.

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

--version          : show the current version and exit.''')


def main() -> None:
    """Start the application."""
    # Ensure our necessary directories exist
    for directory in ['', 'modules', 'profiles', 'profiles/default']:
        try:
            os.mkdir(os.path.expanduser('~/.config/pext/{}'.format(directory)))
        except OSError:
            # Probably already exists, that's okay
            pass

    settings = _loadSettings(sys.argv[1:])

    # Get an app instance
    app = QApplication(['Pext ({})'.format(settings['profile'])])

    # Set up persistence
    pidfile = _initPersist(settings['profile'])

    # Get a window
    window = Window(settings)

    # Get a logger
    logger = Logger(window)

    # Give the window a reference to the logger
    window.bindLogger(logger)

    # Clean up on exit
    atexit.register(_shutDown, pidfile, settings['profile'], window)

    # Handle SIGUSR1 UNIX signal
    signalHandler = SignalHandler(window)
    signal.signal(signal.SIGUSR1, signalHandler.handle)

    # Create a main loop
    mainLoop = MainLoop(app, window, settings, logger)

    # And run...
    mainLoop.run()

if __name__ == "__main__":
    main()
