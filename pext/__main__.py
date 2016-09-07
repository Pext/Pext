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

import atexit
import getopt
import os
import signal
import sys
import threading
import time
from importlib import reload
from shutil import rmtree
from subprocess import check_call, check_output, Popen, PIPE, CalledProcessError
from queue import Queue, Empty

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QTextEdit, QVBoxLayout, QDialogButtonBox
from PyQt5.Qt import QObject, QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlProperty, QUrl

# FIXME: See if there is a less ugly hack to ensure pext_base and pext_helpers
# can always be loaded by us and the modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'helpers'))

from pext_base import ModuleBase
from pext_helpers import Action, SelectionType

class VersionRetriever():
    """Retrieve general information."""
    def __init__(self):
        self.version = None

    def getVersion(self):
        """Retrieve the version information and cache it."""
        if not self.version:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')) as version_file:
                self.version = version_file.read().strip()

        return self.version


class RunConseq():
    """A simple helper to run several functions consecutively."""
    def __init__(self, functions):
        for function in functions:
            if len(function['args']) > 0:
                function['name'](function['args'], **function['kwargs'])
            else:
                function['name'](**function['kwargs'])


class InputDialog(QDialog):
    """A simple dialog requesting user input."""
    def __init__(self, question, text, parent=None):
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

    def show(self):
        """Show the dialog."""
        result = self.exec_()
        return (self.textEdit.toPlainText(), result == QDialog.Accepted)


class Logger():
    """Shows events in the main window and, if the main window is not visible,
    as a desktop notification.
    """
    def __init__(self, window):
        """Initialize the logger and add a status bar to the main window."""
        self.window = window
        self.queuedMessages = []

        self.lastUpdate = None
        self.statusText = self.window.window.findChild(QObject, "statusText")
        self.statusQueue = self.window.window.findChild(QObject, "statusQueue")

    def _queueMessage(self, moduleName, message, typeName):
        """Queue a message for display."""
        for formattedMessage in self._formatMessage(moduleName, message):
            self.queuedMessages.append({'message': formattedMessage, 'type': typeName})

    def _formatMessage(self, moduleName, message):
        """Format message for display, including splitting multiline messages.
        """
        messageLines = []
        for line in message.splitlines():
            if not (not line or line.isspace()):
                if moduleName:
                    message = '{}: {}'.format(moduleName, line)
                else:
                    message = line

                messageLines.append(message)

        return messageLines

    def showNextMessage(self):
        """If the status bar has not been updated for 1 second, display the
        next message. If no messages are available, clear the status bar after
        it has been displayed for 5 seconds.
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

    def addError(self, moduleName, message):
        """Add an error message to the queue."""
        self._queueMessage(moduleName, message, 'error')

    def addMessage(self, moduleName, message):
        """Add a regular message to the queue."""
        self._queueMessage(moduleName, message, 'message')

    def setQueueCount(self, count):
        """Show the queue size on screen."""
        if (count[0] == 0 and count[1] == 0):
            QQmlProperty.write(self.statusQueue, "text", "Ready")
        else:
            QQmlProperty.write(self.statusQueue, "text", "Processing: {} ({})".format(count[0], count[1]))


class MainLoop():
    """Main process loop, connects the application and UI events together,
    ensures events get managed without locking up the UI.
    """
    def __init__(self, app, window, settings, logger):
        """Initialize the main loop"""
        self.app = app
        self.window = window
        self.settings = settings
        self.logger = logger

    def _processTabAction(self, tab, activeTab):
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
            answer = QMessageBox.question(self.window, "Pext", action[1], QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            tab['vm'].module.processResponse(True if (answer == QMessageBox.Yes) else False)
        elif action[0] == Action.askQuestionDefaultNo:
            answer = QMessageBox.question(self.window, "Pext", action[1], QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
            tab['vm'].search()
            tab['entriesProcessed'] = 0

        self.window.update()
        tab['queue'].task_done()

    def run(self):
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
                except Empty:
                    if activeTab and tab['entriesProcessed']:
                        tab['vm'].search()

                    tab['entriesProcessed'] = 0
                except Exception as e:
                    print('WARN: Module caused exception {}'.format(e))

            self.logger.setQueueCount(queueSize)

            if allEmpty:
                if self.window.window.isVisible():
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)


class ModuleManager():
    """Install, remove, update and list modules."""
    def __init__(self):
        self.moduleDir = os.path.expanduser('~/.config/pext/modules/')
        self.logger = None

    def _addPrefix(self, moduleName):
        """Ensure the string starts with pext_module_."""
        if not moduleName.startswith('pext_module_'):
            return 'pext_module_{}'.format(moduleName)

        return moduleName

    def _removePrefix(self, moduleName):
        """Remove pext_module_ from the start of the string."""
        if moduleName.startswith('pext_module_'):
            return moduleName[len('pext_module_'):]

        return moduleName

    def _log(self, message):
        if self.logger:
            self.logger.addMessage("", message)
        else:
            print(message)

    def _logError(self, message):
        if self.logger:
            self.logger.addError("", message)
        else:
            print(message)

    def bindLogger(self, logger):
        self.logger = logger

    def loadModule(self, window, module):
        """Load a module and attach it to the main window."""
        # Append modulePath if not yet appendend
        modulePath = os.path.expanduser('~/.config/pext/modules')
        if not modulePath in sys.path:
            sys.path.append(modulePath)

        # Remove pext_module_ from the module name
        moduleDir = self._addPrefix(module['name']).replace('.', '_')
        moduleName = self._removePrefix(module['name'])

        # Prepare viewModel and context
        vm = ViewModel()
        moduleContext = QQmlContext(window.context)
        moduleContext.setContextProperty("resultListModel", vm.resultListModelList)
        moduleContext.setContextProperty("resultListModelMaxIndex", vm.resultListModelMaxIndex)
        moduleContext.setContextProperty("resultListModelCommandMode", False)

        # Prepare module
        try:
            moduleImport = __import__(moduleDir, fromlist=['Module'])
        except ImportError:
            self._logError("Failed to load module {} from {}".format(moduleName, moduleDir))
            return False

        Module = getattr(moduleImport, 'Module')

        # Ensure the module implements the base
        assert issubclass(Module, ModuleBase)

        # Add tab
        tabData = QQmlComponent(window.engine)
        tabData.loadUrl(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/ModuleData.qml"))
        window.engine.setContextForObject(tabData, moduleContext)
        window.tabs.addTab(moduleName, tabData)

        # Set up a queue so that the module can communicate with the main thread
        q = Queue()

        # This will (correctly) fail if the module doesn't implement all necessary
        # functionality
        moduleCode = Module()

        # Start the module in the background
        moduleThread = ModuleThreadInitializer(moduleName, q, target=moduleCode.init, args=(module['settings'], q))
        moduleThread.start()

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

    def unloadModule(self, window, tabId):
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

    def listModules(self, humanReadable=False):
        """Return a list of modules together with their source."""
        modules = []

        for directory in os.listdir(self.moduleDir):
            name = self._removePrefix(directory)
            try:
                source = check_output(['git', 'config', '--get', 'remote.origin.url'], cwd=os.path.join(self.moduleDir, directory), universal_newlines=True).strip()
            except (CalledProcessError, FileNotFoundError):
                source = "Unknown"

            if humanReadable:
                modules.append('{} ({})'.format(name, source))
            else:
                modules.append([name, source])

        return modules

    def reloadModule(self, window, tabId):
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
        self.loadModule(window, module)

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

    def installModule(self, url, verbose=False, interactive=True):
        """Install a module."""
        moduleName = url.split("/")[-1]

        dirName = self._addPrefix(moduleName).replace('.', '_')
        moduleName = self._removePrefix(moduleName)

        if verbose:
            self._log('Installing {} from {}'.format(moduleName, url))

        returnCode = Popen(['git', 'clone', url, dirName], cwd=self.moduleDir, env={'GIT_ASKPASS': 'true'} if not interactive else None).wait()
        if returnCode != 0:
            if verbose:
                self._logError('Failed to install {}'.format(moduleName))

            return False

        if verbose:
            self._log('Installed {}'.format(moduleName))

        return True

    def uninstallModule(self, moduleName, verbose=False):
        """Uninstall a module."""
        dirName = self._addPrefix(moduleName)
        moduleName = self._removePrefix(moduleName)

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

    def updateModule(self, moduleName, verbose=False):
        """Update a module."""
        dirName = self._addPrefix(moduleName)
        moduleName = self._removePrefix(moduleName)

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

    def updateAllModules(self, verbose=False):
        """Update all modules."""
        for module in self.listModules():
            self.updateModule(module[0], verbose=verbose)


class ModuleThreadInitializer(threading.Thread):
    """Initialize a thread for the module."""
    def __init__(self, moduleName, q, target=None, args=()):
        self.moduleName = moduleName
        self.queue = q
        threading.Thread.__init__(self, target=target, args=args)

    """Start the module's thread."""
    def run(self):
        try:
            threading.Thread.run(self)
        except Exception as e:
            self.queue.put([Action.criticalError, "Exception thrown: {}".format(e)])


class ViewModel():
    """Manage the communication between user interface and module."""
    def __init__(self):
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self.commandList = []
        self.entryList = []
        self.filteredList = []
        self.resultListModelList = QStringListModel()
        self.resultListModelMaxIndex = -1
        self.selection = []

    def _getLongestCommonString(self, entries, start=""):
        """Return the longest common string for each entry in the list,
        starting at the start.

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

    def bindContext(self, queue, context, window, searchInputModel, resultListModel):
        """Bind the QML context so we can communicate with the QML front-end."""
        self.queue = queue
        self.context = context
        self.window = window
        self.searchInputModel = searchInputModel
        self.resultListModel = resultListModel

    def bindModule(self, module):
        """Bind the module so we can communicate with it and retrieve the
        commands and entries from it.
        """
        self.module = module

    def goUp(self):
        """Go one level up. This means that, if we're currently in the entry
        content list, we go back to the entry list. If we're currently in the
        entry list, we clear the search bar. If we're currently in the entry
        list and the search bar is empty, we hide the window.
        """
        if QQmlProperty.read(self.searchInputModel, "text") != "":
            QQmlProperty.write(self.searchInputModel, "text", "")
            return

        if len(self.selection) > 0:
            self.selection.pop()
            self.module.selectionMade(self.selection)
        else:
            self.window.close()

    def search(self):
        """Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex == -1 or currentIndex > self.resultListModelMaxIndex:
            currentItem = None
        else:
            currentItem = self.filteredList[currentIndex]

        self.filteredList = []
        commandList = []

        searchStrings = QQmlProperty.read(self.searchInputModel, "text").lower().split(" ")
        for entry in self.entryList:
            if all(searchString in str(entry).lower() for searchString in searchStrings):
                self.filteredList.append(entry)

        self.resultListModelMaxIndex = len(self.filteredList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)

        for command in self.commandList:
            if searchStrings[0] in command:
                commandList.append(command)

        if len(self.filteredList) == 0 and len(commandList) > 0:
            self.filteredList = commandList
            for entry in self.entryList:
                if any(searchString in str(entry).lower() for searchString in searchStrings[1:]):
                    self.filteredList.append(entry)

            self.context.setContextProperty("resultListModelCommandMode", True)
        else:
            self.filteredList += commandList
            self.context.setContextProperty("resultListModelCommandMode", False)

        self.resultListModelList = QStringListModel([str(entry) for entry in self.filteredList])
        self.context.setContextProperty("resultListModel", self.resultListModelList)

        if self.resultListModelMaxIndex == -1:
            currentIndex = -1
        elif currentItem is None:
            currentIndex = 0
        else:
            try:
                currentIndex = self.filteredList.index(currentItem)
            except ValueError:
                currentIndex = 0

        QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex)

    def select(self):
        """Notify the module of our selection entry."""
        if len(self.filteredList) == 0 or self.queue.qsize() > 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")

        if currentIndex == -1 or currentIndex > self.resultListModelMaxIndex:
            commandTyped = QQmlProperty.read(self.searchInputModel, "text")

            self.selection.append({'type': SelectionType.command, 'value': commandTyped})
            result = self.module.selectionMade(self.selection)

            QQmlProperty.write(self.searchInputModel, "text", "")

            return

        entry = self.filteredList[currentIndex]
        self.selection.append({'type': SelectionType.entry, 'value': entry})
        self.module.selectionMade(self.selection)
        QQmlProperty.write(self.searchInputModel, "text", "")

    def tabComplete(self):
        """Tab-complete the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        currentInput = QQmlProperty.read(self.searchInputModel, "text")

        start = currentInput

        possibles = currentInput.split(" ", 1)
        command = self._getLongestCommonString([command.split(" ", 1)[0] for command in self.commandList], start=possibles[0])
        # If we didn't complete the command, see if we can complete the text
        if command is None or len(command) == len(possibles[0]):
            if command is None:
                command = "" # We string concat this later
            else:
                command += " "

            start = possibles[1] if len(possibles) > 1 else ""
            entry = self._getLongestCommonString([listEntry for listEntry in self.filteredList if listEntry not in self.commandList], start=start)

            if entry is None or len(entry) <= len(start):
                self.queue.put([Action.addError, "No tab completion possible"])
                return
        else:
            entry = " " # Add an extra space to simplify typing for the user

        QQmlProperty.write(self.searchInputModel, "text", command + entry)
        self.search()


class Window(QMainWindow):
    """The main Pext window."""
    def __init__(self, settings, parent=None):
        """Initialize the window."""
        super().__init__(parent)

        # Save settings
        self.settings = settings

        self.engine = QQmlApplicationEngine(self)

        self.context = self.engine.rootContext()

        # Load the main UI
        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

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
        menuListModulesShortcut.triggered.connect(self._menuListModules)
        menuInstallModuleShortcut.triggered.connect(self._menuInstallModule)
        menuUninstallModuleShortcut.triggered.connect(self._menuUninstallModule)
        menuUpdateModuleShortcut.triggered.connect(self._menuUpdateModule)
        menuUpdateAllModulesShortcut.triggered.connect(self._menuUpdateAllModules)
        menuAboutShortcut.triggered.connect(self._menuAbout)
        menuQuitShortcut.triggered.connect(self._menuQuit)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self._bindContext)

        # Show the window
        self.show()

    def _bindContext(self):
        """Bind the context for the module."""
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        element = self.tabBindings[currentTab]

        # Only initialize once, ensure filter is applied
        if element['init']:
            element['vm'].search()
            return

        # Get the list
        resultListModel = self.tabs.getTab(currentTab).findChild(QObject, "resultListModel")

        # Enable mouse selection support
        resultListModel.entryClicked.connect(element['vm'].select)

        # Bind it to the viewmodel
        element['vm'].bindContext(element['queue'], element['moduleContext'], self, self.searchInputModel, resultListModel)
        element['vm'].bindModule(element['module'])

        # Done initializing
        element['init'] = True

    def _getCurrentElement(self):
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        try:
            return self.tabBindings[currentTab]
        except IndexError:
            # No tabs
            return None

    def _goUp(self):
        try:
            self._getCurrentElement()['vm'].goUp()
        except TypeError:
            pass

    def _openTab(self):
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

    def _closeTab(self):
        if len(self.tabBindings) > 0:
            self.moduleManager.unloadModule(self, QQmlProperty.read(self.tabs, "currentIndex"))

    def _reloadModule(self):
        if len(self.tabBindings) > 0:
            self.moduleManager.reloadModule(self, QQmlProperty.read(self.tabs, "currentIndex"))

    def _menuListModules(self):
        moduleList = ['Installed modules:', ''] + self.moduleManager.listModules(humanReadable=True)
        QMessageBox.information(self, "Pext", '\n'.join(moduleList))

    def _menuInstallModule(self):
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
            threading.Thread(target=RunConseq, args=(functions,)).start()

    def _menuUninstallModule(self):
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
            threading.Thread(target=RunConseq, args=(functions,)).start()

    def _menuUpdateModule(self):
        moduleList = [module[0] for module in self.moduleManager.listModules()]
        moduleName, ok = QInputDialog.getItem(self, "Pext", "Choose the module to update", moduleList, 0, False)
        if ok:
            threading.Thread(target=self.moduleManager.updateModule, args=(moduleName,), kwargs={'verbose': True}).start()

    def _menuUpdateAllModules(self):
        threading.Thread(target=self.moduleManager.updateAllModules, kwargs={'verbose': True}).start()

    def _menuAbout(self):
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

        QMessageBox.information(self, "About", aboutText.format(VersionRetriever().getVersion()))

    def _menuQuit(self):
        sys.exit(0)

    def _search(self):
        try:
            self._getCurrentElement()['vm'].search()
        except TypeError:
            pass

    def _select(self):
        try:
            self._getCurrentElement()['vm'].select()
        except TypeError:
            pass

    def _tabComplete(self):
        try:
            self._getCurrentElement()['vm'].tabComplete()
        except TypeError:
            pass

    def _updateModulesInstalledCount(self):
        QQmlProperty.write(self.introScreen, "modulesInstalledCount", len(self.moduleManager.listModules()))

    def bindLogger(self, logger):
        self.moduleManager.bindLogger(logger)

        # Now that the logger is bound, we can show messages in the window, so
        # start binding the modules
        self.tabBindings = [];
        for module in self.settings['modules']:
            self.moduleManager.loadModule(self, module)

        # If there's only one module passed through the command line, enforce
        # loading it now. Otherwise, switch back to the first module in the
        # list
        if len(self.tabBindings) == 1:
            self.tabs.currentIndexChanged.emit()
        elif len(self.tabBindings) > 1:
            QQmlProperty.write(self.tabs, "currentIndex", "0")


    def close(self):
        """Close the window. If the user wants us to completely close when
        done, also exit the application.
        """
        if self.settings['closeWhenDone']:
            sys.exit(0)
        else:
            self.window.hide()
            QQmlProperty.write(self.searchInputModel, "text", "")
            for tab in self.tabBindings:
                if not tab['init']:
                    continue

                tab['vm'].selection = []
                tab['vm'].module.selectionMade(tab['vm'].selection)
                tab['vm'].search()

    def show(self):
        """Show the window."""
        self.window.show()
        self.activateWindow()


class SignalHandler():
    """Handle UNIX signals."""
    def __init__(self, window):
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum, frame):
        """When an UNIX signal gets received, show the window."""
        self.window.show()


def _initPersist():
    """Check if Pext is already running and if so, send it SIGUSR1 to bring it
    to the foreground. If Pext is not already running, save a PIDfile so that
    another Pext instance can find us.
    """
    pidfile = "/tmp/pext.pid"

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

def _loadSettings(argv):
    """Load the settings from the command line and set defaults."""
    # Default options
    settings = {'clipboard': 'clipboard',
                'closeWhenDone': False,
                'modules': []}

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
        opts, args = getopt.getopt(argv, "hc:m:", ["help", "version", "clipboard=", "close-when-done", "module=", "install-module=", "uninstall-module=", "update-module=", "update-modules", "list-modules"] + moduleOpts)
    except getopt.GetoptError as err:
        print("{}\n".format(err))
        usage()
        sys.exit(1)

    for opt, args in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt == "--version":
            print("Pext {}".format(VersionRetriever().getVersion))
            sys.exit(0)
        elif opt == "--close-when-done":
            settings['closeWhenDone'] = True
        elif opt in ("-b", "--binary"):
            settings['binary'] = args
        elif opt in ("-c", "--clipboard"):
            if not args in ["primary", "secondary", "clipboard"]:
                print("Invalid clipboard requested")
                sys.exit(3)

            settings['clipboard'] = args
        elif opt in ("-m", "--module"):
            if not args.startswith('pext_module_'):
                args = 'pext_module_' + args

            settings['modules'].append({'name': args, 'settings': {}})
        elif opt.startswith("--module-"):
            settings['modules'][-1]['settings'][opt[9:]] = args
        elif opt == "--install-module":
            ModuleManager().installModule(args, verbose=True)
        elif opt == "--uninstall-module":
            ModuleManager().uninstallModule(args, verbose=True)
        elif opt == "--update-module":
            ModuleManager().updateModule(args, verbose=True)
        elif opt == "--update-modules":
            ModuleManager().updateAllModules(verbose=True)
        elif opt == "--list-modules":
            for module in ModuleManager().listModules(humanReadable=True):
                print(module)

    return settings

def _shutDown(pidfile, window, closeWhenDone):
    """Clean up."""
    for module in window.tabBindings:
        module['module'].stop()

    if not closeWhenDone:
        os.unlink(pidfile)

def usage():
    """Print usage information."""
    print('''Options:

--clipboard        : choose the clipboard to copy entries to. Acceptable values
                     are "primary", "secondary" or "clipboard". See the xclip
                     documentation for more information. Defaults to
                     "clipboard".

--close-when-done  : close after completing an action such as copying
                     a password or closing the application (through
                     escape or (on most systems) Alt+F4) instead of
                     staying in memory. This also allows multiple
                     instances to be ran at once.

--help             : show this screen and exit.

--install-module   : download and install a module from the given git URL.

--list-modules     : list all installed modules.

--module           : name the module to use. This option may be given multiple
                     times to use multiple modules.

--module-*         : set a module setting for the most recently given module.
                     For example, to set a module-specific setting called
                     binary, use --module-binary=value. Check the module
                     documentation for the supported module-specific settings.

--uninstall-module : uninstall a module by name.

--update-module    : update a module by name.

--update-modules   : update all installed modules.

--version          : show the current version and exit.''')

def main():
    # Ensure our necessary directories exist
    try:
        os.mkdir(os.path.expanduser('~/.config/pext'))
        os.mkdir(os.path.expanduser('~/.config/pext/modules'))
    except OSError:
        # Probably already exists, that's okay
        pass

    settings = _loadSettings(sys.argv[1:])

    # Get an app instance
    app = QApplication(["Pext"])

    # Set up persistence
    if settings['closeWhenDone']:
        pidfile = None
    else:
        pidfile = _initPersist()

    # Get a window
    window = Window(settings)

    # Get a logger
    logger = Logger(window)

    # Give the window a reference to the logger
    window.bindLogger(logger)

    # Clean up on exit
    atexit.register(_shutDown, pidfile, window, settings['closeWhenDone'])

    # Handle SIGUSR1 UNIX signal
    signalHandler = SignalHandler(window)
    signal.signal(signal.SIGUSR1, signalHandler.handle)

    # Create a main loop
    mainLoop = MainLoop(app, window, settings, logger)

    # And run...
    mainLoop.run()

if __name__ == "__main__":
    main()
