#!/usr/bin/env python3

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
import re
import threading
import time
from shutil import rmtree
from subprocess import call, Popen, PIPE
from queue import Queue, Empty

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QLabel, QLineEdit, QMessageBox, QTextEdit, QVBoxLayout, QDialogButtonBox
from PyQt5.Qt import QObject, QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlProperty, QUrl

from pext_base import ModuleBase
from pext_helpers import Action

class SignalHandler():
    """Handle UNIX signals."""
    def __init__(self, window):
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum, frame):
        """When an UNIX signal gets received, show the window."""
        self.window.show()

class ModuleInitializer(threading.Thread):
    """Initialize a module."""
    def __init__(self, moduleName, q, target=None, args=()):
        self.moduleName = moduleName
        self.queue = q
        threading.Thread.__init__(self, target=target, args=args)

    def run(self):
        try:
            threading.Thread.run(self)
        except Exception as e:
            self.queue.put([Action.criticalError, "Exception thrown: {}".format(e)])

class ViewModel():
    """Manage the communication between user interface and module."""
    def __init__(self, settings):
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self.commandList = []
        self.entryList = []
        self.filteredList = []
        self.resultListModelList = QStringListModel()
        self.resultListModelMaxIndex = -1
        self.chosenEntry = None
        self.chosenEntryList = []

        self.settings = settings

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

        self.search()

    def getElementsFromList(self, pythonList, element):
        """Return the chosen element for each entry in the list.

        Keyword arguments:
        pythonList -- the list of entries, with each entry being a list
        element -- the requested element number

        For example, if element is 1, and pythonList is [["a", "b"]], this
        function returns ["b"].
        """
        return [entry[element] for entry in pythonList]

    def getLongestCommonString(self, entries, start=""):
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

    def copyToClipboard(self, data):
        """Copy the given data to the user-chosen clipboard."""
        proc = Popen(["xclip", "-selection", self.settings["clipboard"]], stdin=PIPE)
        proc.communicate(data.encode('utf-8'))

    def goUp(self):
        """Go one level up. This means that, if we're currently in the entry
        content list, we go back to the entry list. If we're currently in the
        entry list, we clear the search bar. If we're currently in the entry
        list and the search bar is empty, we hide the window.
        """
        if QQmlProperty.read(self.searchInputModel, "text") != "":
            QQmlProperty.write(self.searchInputModel, "text", "")
            return

        if self.chosenEntry is None:
            self.window.close()
            return

        self.chosenEntry = None
        self.search()

    def tabComplete(self):
        """Tab-complete the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        currentInput = QQmlProperty.read(self.searchInputModel, "text")

        start = currentInput
        searchableCommands = [listEntry[0] for listEntry in self.commandList]

        possibles = currentInput.split(" ", 1)
        command = self.getLongestCommonString(searchableCommands, start=possibles[0])
        # If we didn't complete the command, see if we can complete the text
        if command is None or len(command) == len(possibles[0]):
            if command is None:
                command = "" # We string concat this later
            else:
                command += " "

            start = possibles[1] if len(possibles) > 1 else ""
            entry = self.getLongestCommonString([listEntry[1] for listEntry in self.filteredList if listEntry[1] not in searchableCommands], start=start)

            if entry is None or len(entry) <= len(start):
                self.queue.put([Action.addError, "No tab completion possible"])
                return
        else:
            entry = " " # Add an extra space to simplify typing for the user

        QQmlProperty.write(self.searchInputModel, "text", command + entry)
        self.search()

    def moveUp(self):
        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex > 0:
            QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex - 1)

    def moveDown(self):
        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex < QQmlProperty.read(self.resultListModel, "maximumIndex"):
            QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex + 1)

    def search(self):
        """Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        if self.chosenEntry is not None:
            self.searchChosenEntry()
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex == -1 or len(self.filteredList) < currentIndex + 1:
            currentItem = None
        else:
            currentItem = self.filteredList[currentIndex]

        self.filteredList = []
        commandList = []

        searchStrings = QQmlProperty.read(self.searchInputModel, "text").lower().split(" ")
        for entry in self.entryList:
            if all(searchString in entry[1].lower() for searchString in searchStrings):
                self.filteredList.append(entry)

        self.resultListModelMaxIndex = len(self.filteredList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)

        for command in self.commandList:
            if searchStrings[0] in command[1]:
                commandList.append(command)

        if len(self.filteredList) == 0 and len(commandList) > 0:
            self.filteredList = commandList
            for entry in self.entryList:
                if any(searchString in entry[1].lower() for searchString in searchStrings[1:]):
                    self.filteredList.append(entry)

            self.context.setContextProperty("resultListModelCommandMode", True)
        else:
            self.filteredList += commandList
            self.context.setContextProperty("resultListModelCommandMode", False)

        self.resultListModelList = QStringListModel(self.getElementsFromList(self.filteredList, 1))
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

    def searchChosenEntry(self):
        """Search the content within a single entry."""
        # Ensure this entry still exists
        if self.chosenEntry not in self.entryList:
            self.queue.put([Action.addError, self.chosenEntry + " is no longer available"])
            self.chosenEntry = None
            QQmlProperty.write(self.searchInputModel, "text", "")
            self.search()
            return

        if len(self.filteredList) == 0:
            currentItem = None
        else:
            currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
            currentItem = self.filteredList[currentIndex]

        searchStrings = QQmlProperty.read(self.searchInputModel, "text").lower().split(" ")

        self.filteredList = []

        for entry in self.chosenEntryList:
            if any(searchString in entry[1].lower() for searchString in searchStrings):
                self.filteredList.append(entry)

        try:
            currentIndex = self.filteredList.index(currentItem)
        except ValueError:
            currentIndex = 0

        self.resultListModelList = QStringListModel(self.getElementsFromList(self.filteredList, 1))
        self.context.setContextProperty("resultListModel", self.resultListModelList)

        QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex)

    def select(self):
        """Select an entry or an entry in the content of an entry. If we're
        already in an entry, get the content list. If the content list is zero
        or one entries, copy the entry or single line of content to the
        clipboard.
        """
        if self.chosenEntry is not None:
            self.selectField()
            return

        if len(self.filteredList) == 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")

        if currentIndex == -1:
            commandTyped = QQmlProperty.read(self.searchInputModel, "text").split(" ")
            if commandTyped[0] not in [entry[0] for entry in self.commandList]:
                return

            result = self.module.runCommand(commandTyped, printOnSuccess=True)

            if result is not None:
                QQmlProperty.write(self.searchInputModel, "text", "")

            return

        self.chosenEntry = self.filteredList[currentIndex]
        try:
            entryContent = self.module.getAllEntryFields(self.chosenEntry[0])
        except:
            self.queue.put([Action.addError, "A module error occured while retrieving the entry list"])
            self.chosenEntry = None
            return

        if len(entryContent) == 0:
            # If there is no content, copy the entry itself
            self.copyToClipboard(self.chosenEntry[1])
            self.window.close()
            return
        elif len(entryContent) == 1:
            # If there is only one entry, copy that entry
            self.copyToClipboard(entryContent[0][0])
            self.window.close()
            return

        # If the entry has more than one line, fill the result list with all
        # lines, so the user can choose the line they want to copy to the
        # clipboard
        self.chosenEntryList = entryContent
        self.filteredList = entryContent

        self.resultListModelList = QStringListModel(self.getElementsFromList(self.filteredList, 1))
        self.context.setContextProperty("resultListModel", self.resultListModelList)
        self.resultListModelMaxIndex = len(self.filteredList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)
        QQmlProperty.write(self.resultListModel, "currentIndex", 0)
        QQmlProperty.write(self.searchInputModel, "text", "")

    def selectField(self):
        """Select a field in the entry content and copy it to the clipboard."""
        if len(self.filteredList) == 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")

        self.copyToClipboard(self.filteredList[currentIndex][0])
        self.window.close()
        return


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


class Window(QDialog):
    """The main Pext window."""
    def __init__(self, settings, pidfile, parent=None):
        """Initialize the window."""
        super().__init__(parent)

        # Clean up when Pext exits
        atexit.register(shutDown, pidfile, self)

        self.messageList = []
        self.messageListModelList = QStringListModel()

        self.engine = QQmlApplicationEngine(self)

        self.tabBindings = []

        self.context = self.engine.rootContext()

        # Fill context with temp values so the UI can load
        # This needs a viewModel to prevent Python from garbage-collecting it
        vm = ViewModel(settings)
        self.context.setContextProperty("messageListModelList", self.messageListModelList)

        # Load the main UI
        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        # Bind global shortcuts
        escapeShortcut = self.window.findChild(QObject, "escapeShortcut")
        tabShortcut = self.window.findChild(QObject, "tabShortcut")
        upShortcut = self.window.findChild(QObject, "upShortcut")
        upShortcutAlt = self.window.findChild(QObject, "upShortcutAlt")
        downShortcut = self.window.findChild(QObject, "downShortcut")
        downShortcutAlt = self.window.findChild(QObject, "downShortcutAlt")
        self.searchInputModel = self.window.findChild(QObject, "searchInputModel")
        clearOldMessagesTimer = self.window.findChild(QObject, "clearOldMessagesTimer")

        escapeShortcut.activated.connect(self.goUp)
        tabShortcut.activated.connect(self.tabComplete)
        upShortcut.activated.connect(self.moveUp)
        upShortcutAlt.activated.connect(self.moveUp)
        downShortcut.activated.connect(self.moveDown)
        downShortcutAlt.activated.connect(self.moveDown)
        self.searchInputModel.textChanged.connect(self.search)
        self.searchInputModel.accepted.connect(self.select)
        clearOldMessagesTimer.triggered.connect(self.clearOldMessages)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self.bindContext)

        # Show the window
        self.show()

        # Prepare loading modules
        sys.path.append(os.path.expanduser('~/.config/pext/modules'))

        for module in settings['modules']:
            # Remove pext_module_ from the module name
            moduleName = module[len('pext_module_'):]

            # Prepare viewModel and context
            vm = ViewModel(settings)
            moduleContext = QQmlContext(self.context)
            moduleContext.setContextProperty("resultListModel", vm.resultListModelList)
            moduleContext.setContextProperty("resultListModelMaxIndex", vm.resultListModelMaxIndex)
            moduleContext.setContextProperty("resultListModelCommandMode", False)

            # Add tab
            tabData = QQmlComponent(self.engine)
            tabData.loadUrl(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/ModuleData.qml"))
            self.engine.setContextForObject(tabData, moduleContext)
            self.tabs.addTab(moduleName, tabData)

            # Prepare module
            moduleImport = __import__(module.replace('.', '_'), fromlist=['Module'])

            Module = getattr(moduleImport, 'Module')

            # Ensure the module implements the base
            assert issubclass(Module, ModuleBase)

            # Set up a queue so that the module can communicate with the main thread
            q = Queue()

            # This will (correctly) fail if the module doesn't implement all necessary
            # functionality
            module = Module()

            # Start the module in the background
            moduleThread = ModuleInitializer(moduleName, q, target=module.init, args=(settings['binary'], q))
            moduleThread.start()

            # Store tab/viewModel combination
            self.tabBindings.append({'init': False,
                                     'queue': q,
                                     'vm': vm,
                                     'module': module,
                                     'moduleContext': moduleContext,
                                     'moduleName': moduleName})

        # Handle signal
        signalHandler = SignalHandler(self)
        signal.signal(signal.SIGUSR1, signalHandler.handle)

        # Trigger the first context bind
        self.bindContext()

        # Start processing data
        mainLoop(app, self.tabBindings, self)

    def addError(self, moduleName, message):
        """Add an error message to the window and show the message list."""
        for line in message.splitlines():
            if not (not line or line.isspace()):
                self.messageList.append(["<font color='red'>{}: {}</color>".format(moduleName, line), time.time()])

        self.showMessages()

    def addMessage(self, moduleName, message):
        """Add a message to the window and show the message list."""
        for line in message.splitlines():
            if not (not line or line.isspace()):
                self.messageList.append(["{}: {}".format(moduleName, line), time.time()])

        self.showMessages()

    def showMessages(self):
        """Show the list of messages in the window."""
        messageListForModel = [message[0] for message in self.messageList]
        self.messageListModelList = QStringListModel(messageListForModel)
        self.context.setContextProperty("messageListModelList", self.messageListModelList)

    def clearOldMessages(self):
        """Remove all messages older than 3 seconds and show the list of
        messages in the window.
        """
        if len(self.messageList) == 0:
            return

        currentTime = time.time()
        self.messageList = [message for message in self.messageList if currentTime - message[1] < 3]
        self.showMessages()


    def getCurrentElement(self):
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        return self.tabBindings[currentTab]

    def goUp(self):
        self.getCurrentElement()['vm'].goUp()

    def tabComplete(self):
        self.getCurrentElement()['vm'].tabComplete()

    def moveUp(self):
        self.getCurrentElement()['vm'].moveUp()

    def moveDown(self):
        self.getCurrentElement()['vm'].moveDown()

    def search(self):
        self.getCurrentElement()['vm'].search()

    def select(self):
        self.getCurrentElement()['vm'].select()

    def bindContext(self):
        """Bind the context for the module."""
        currentTab = QQmlProperty.read(self.tabs, "currentIndex")
        element = self.tabBindings[currentTab]

        # Only initialize one
        if element['init']:
            return;

        # Get the list
        resultListModel = self.tabs.getTab(currentTab).findChild(QObject, "resultListModel")

        # Enable mouse selection support
        resultListModel.entryClicked.connect(element['vm'].select)

        # Bind it to the viewmodel
        element['vm'].bindContext(element['queue'], element['moduleContext'], self, self.searchInputModel, resultListModel)
        element['vm'].bindModule(element['module'])

        # Done initializing
        element['init'] = True

    def show(self):
        """Show the window."""
        self.window.show()
        self.activateWindow()

    def close(self):
        """Close the window. If the user wants us to completely close when
        done, also exit the application.
        """
        if not settings['closeWhenDone']:
            self.window.hide()
            QQmlProperty.write(self.searchInputModel, "text", "")
            for tab in self.tabBindings:
                if not tab['init']:
                    continue

                tab['vm'].chosenEntry = None
                tab['vm'].search()
        else:
            sys.exit(0)


def loadSettings(argv):
    """Load the settings from the command line and set defaults."""
    # Default options
    settings = {'binary': None,
                'clipboard': 'clipboard',
                'closeWhenDone': False,
                'modules': [],
                'installModules': [],
                'uninstallModules': [],
                'listModules': False,
                'updateModules': False}

    try:
        opts, args = getopt.getopt(argv, "hb:c:m:", ["help", "binary=", "clipboard=", "close-when-done", "module=", "install-module=", "uninstall-module=", "list-modules", "update-modules"])
    except getopt.GetoptError as err:
        print("{}\n".format(err))
        usage()
        sys.exit(1)

    for opt, args in opts:
        if opt in ("-h", "--help"):
            usage()
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

            settings['modules'].append(args)
        elif opt == "--install-module":
            settings['installModules'].append(args)
        elif opt == "--uninstall-module":
            settings['uninstallModules'].append(args)
        elif opt == "--list-modules":
            settings['listModules'] = True
        elif opt == "--update-modules":
            settings['updateModules'] = True

    return settings


def usage():
    """Print usage information."""
    print('''Options:

--binary           : choose the name of the binary to use. Defaults to 'pass' for
                     the pass module and todo.sh for the todo.sh module. Paths
                     are allowed.

--clipboard        : choose the clipboard to copy entries to. Acceptable values
                     are "primary", "secondary" or "clipboard". See the xclip
                     documentation for more information. Defaults to
                     "clipboard".

--close-when-done  : close after completing an action such as copying
                     a password or closing the application (through
                     escape or (on most systems) Alt+F4) instead of
                     staying in memory. This also allows multiple
                     instances to be ran at once.

--module           : name the module to use. This option may be given multiple
                     times to use multiple modules.

--install-module   : download and install a module from the given git URL.

--uninstall-module : uninstall a module by name.

--list-modules     : list all installed modules.

--update-modules   : update all installed modules using git pull.''')


def initPersist(modules):
    """Check if Pext is already running and if so, send it SIGUSR1 to bring it
    to the foreground. If Pext is not already running, save a PIDfile so that
    another Pext instance can find us.
    """
    pidfile = "/tmp/pext-" + "_".join(modules) + ".pid"

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

def shutDown(pidfile, window):
    """Clean up."""
    for module in window.tabBindings:
        module['module'].stop()

    if not settings['closeWhenDone']:
        os.unlink(pidfile)

def mainLoop(app, tabs, window):
    """Process actions modules put in the queue and keep the window working."""
    while True:
        for tab in tabs:

            try:
                action = tab['queue'].get_nowait()
                if action[0] == Action.criticalError:
                    window.addError(tab['moduleName'], action[1])
                    tabId = tabs.index(tab)
                    # FIXME: If the first module in the list crashes and we're
                    # running 3 or more modules, we still segfault.
                    if QQmlProperty.read(window.tabs, "currentIndex") == tabId:
                        tabCount = QQmlProperty.read(window.tabs, "count")
                        if tabId + 1 < tabCount:
                            QQmlProperty.write(window.tabs, "currentIndex", tabId + 1)
                        else:
                            if tabId > 0:
                                QQmlProperty.write(window.tabs, "currentIndex", "0")
                            else:
                                return

                    del window.tabBindings[tabId]
                    window.tabs.removeTab(tabId)
                elif action[0] == Action.addMessage:
                    window.addMessage(tab['moduleName'], action[1])
                elif action[0] == Action.addError:
                    window.addError(tab['moduleName'], action[1])
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
                    answer = QMessageBox.question(window, "Pext", action[1], QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                    tab['vm'].module.processResponse(True if (answer == QMessageBox.Yes) else False)
                elif action[0] == Action.askQuestionDefaultNo:
                    answer = QMessageBox.question(window, "Pext", action[1], QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    tab['vm'].module.processResponse(True if (answer == QMessageBox.Yes) else False)
                elif action[0] == Action.askInput:
                    answer, ok = QInputDialog.getText(window, "Pext", action[1])
                    tab['vm'].module.processResponse(answer if ok else None)
                elif action[0] == Action.askInputPassword:
                    answer, ok = QInputDialog.getText(window, "Pext", action[1], QLineEdit.Password)
                    tab['vm'].module.processResponse(answer if ok else None)
                elif action[0] == Action.askInputMultiLine:
                    dialog = InputDialog(action[1], action[2] if action[2] else "", window)
                    answer, ok = dialog.show()
                    tab['vm'].module.processResponse(answer if ok else None)
                else:
                    print('WARN: Module requested unknown action {}'.format(action[0]))

                tab['vm'].search()
                window.update()
                tab['queue'].task_done()
            except Empty:
                app.processEvents()
                time.sleep(0.01)
                continue
            except Exception as e:
                # It's normal for exceptions to be thrown until the module is
                # initialized.
                if tab['init']:
                    print('WARN: Module caused exception {}'.format(e))

                app.processEvents()
                time.sleep(0.01)

if __name__ == "__main__":
    # Ensure our necessary directories exist
    try:
        os.mkdir(os.path.expanduser('~/.config/pext'))
        os.mkdir(os.path.expanduser('~/.config/pext/modules'))
    except OSError:
        # Probably already exists, that's okay
        pass

    settings = loadSettings(sys.argv[1:])

    # First, we uninstall, update and install modules as desired
    for module in settings['uninstallModules']:
        print('Removing {}'.format(module))
        try:
            rmtree(os.path.expanduser('~/.config/pext/modules/pext_module_{}'.format(module)))
        except FileNotFoundError:
            print('Cannot remove {}, it is not installed'.format(module))

    if settings['updateModules']:
        for directory in os.listdir(os.path.expanduser('~/.config/pext/modules/')):
            print('Updating {}'.format(directory))
            call(['git', 'pull'], cwd=os.path.expanduser('~/.config/pext/modules/{}'.format(directory)))

    for module in settings['installModules']:
        storename = module.split("/")[-1]
        print('Installing {}'.format(storename))
        if not storename.startswith('pext_module_'):
            storename = 'pext_module_' + storename

        call(['git', 'clone', module, storename.replace('.', '_')], cwd=os.path.expanduser('~/.config/pext/modules/'))

    if settings['listModules']:
        print('Installed modules:')
        for directory in os.listdir(os.path.expanduser('~/.config/pext/modules/')):
            print(directory[len('pext_module_'):])

    if len(settings['modules']) == 0:
        print('No module given. Not launching.')
        sys.exit(0)

    app = QApplication(sys.argv)

    # Set up persistence
    if not settings['closeWhenDone']:
        pidfile = initPersist(settings['modules'])

    # Run until we close, then clean up
    window = Window(settings, pidfile)
