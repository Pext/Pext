#!/usr/bin/python3

# This file is part of PyPass
#
# PyPass is free software: you can redistribute it and/or modify
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

import getopt
import os
import signal
import sys
import re
import time
from os.path import expanduser
from subprocess import call, check_output, Popen, CalledProcessError, PIPE
from queue import Queue, Empty

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox
from PyQt5.Qt import QQmlApplicationEngine, QObject, QQmlProperty, QUrl

import pyinotify
import pexpect

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, vm, q):
        self.vm = vm
        self.q = q

    def process_IN_CREATE(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(expanduser("~") + "/.password-store/"):-4]

        self.vm.passwordList = [passwordName] + self.vm.passwordList
        self.q.put("created")

    def process_IN_DELETE(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(expanduser("~") + "/.password-store/"):-4]

        self.vm.passwordList.remove(passwordName)
        self.q.put("deleted")

    def process_IN_MOVED_FROM(self, event):
        self.process_IN_DELETE(event)

    def process_IN_MOVED_TO(self, event):
        self.process_IN_CREATE(event)

    def process_IN_OPEN(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(expanduser("~") + "/.password-store/"):-4]

        try:
            self.vm.passwordList.remove(passwordName)
        except ValueError:
            # process_IN_OPEN is also called when moving files, after the
            # initial move event. In this case, we want to do nothing and let
            # IN_MOVED_FROM and IN_MOVED_TO handle this
            return

        self.vm.passwordList = [passwordName] + self.vm.passwordList
        self.q.put("opened")

class SignalHandler():
    def __init__(self, window):
        self.window = window

    def handle(self, signum, frame):
        # Signal received
        self.window.show()

class ViewModel():
    def __init__(self):
        self.getCommands()
        self.getPasswords()

        self.ANSIEscapeRegex = re.compile('(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self.filteredList = []
        self.resultListModelList = QStringListModel()
        self.resultListModelMaxIndex = -1
        self.messageList = []
        self.messageListModelList = QStringListModel()
        self.chosenEntry = None
        self.chosenEntryList = []

    def bindContext(self, context, window, searchInputModel, resultListModel):
        self.context = context
        self.window = window
        self.searchInputModel = searchInputModel
        self.resultListModel = resultListModel

        self.search()

    def addError(self, message):
        for line in message.splitlines():
            if not line or line.isspace():
                continue
            self.messageList.append(["<font color='red'>{}</color>".format(line), time.time()])

        self.showMessages()

    def addMessage(self, message):
        for line in message.splitlines():
            if not line or line.isspace():
                continue
            self.messageList.append([line, time.time()])

        self.showMessages()

    def showMessages(self):
        messageListForModel = []
        for message in self.messageList:
            messageListForModel.append(message[0])
        self.messageListModelList = QStringListModel(messageListForModel)
        self.context.setContextProperty("messageListModelList", self.messageListModelList)

    def runCommand(self, command, printOnSuccess=False, prefillInput=''):
        proc = pexpect.spawn(command[0], command[1:])
        while True:
            result = proc.expect_exact([pexpect.EOF, pexpect.TIMEOUT, "[Y/n]", "[y/N]", " and press Ctrl+D when finished:"], timeout=3)
            if result == 0:
                exitCode = proc.sendline("echo $?")
                break
            elif result == 1 and proc.before:
                self.addError("Timeout error while running '{}'. This specific way of calling the command is most likely not supported yet by PyPass.".format(" ".join(command)))
                self.addError("Command output: {}".format(self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8"))))

                return None
            elif result == 2 or result == 3:
                proc.setecho(False)
                answer = QMessageBox.question(self.window, "Confirmation", proc.before.decode("utf-8"), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes if result == 2 else QMessageBox.No)
                proc.waitnoecho()
                if answer == QMessageBox.Yes:
                    proc.sendline('y')
                else:
                    proc.sendline('n')
                proc.setecho(True)
            elif result == 4:
                dialog = InputDialog(proc.before.decode("utf-8").lstrip(), prefillInput, self.window)

                accepted = 0
                while accepted != 1:
                    result = dialog.show()
                    accepted = result[1]

                proc.setecho(False)
                proc.waitnoecho()
                for line in result[0].splitlines():
                    proc.sendline(line)
                proc.sendcontrol("d")
                proc.setecho(True)

        proc.close()
        exitCode = proc.exitstatus

        message = self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")) if proc.before else ""

        if exitCode == 0:
            if printOnSuccess and message:
                self.addMessage(message)

            return message
        else:
            self.addError(message if message else "Error code {} running '{}'. More info may be logged to the console".format(str(exitCode), " ".join(command)))

            return None

    def clearOldMessages(self):
        if len(self.messageList) == 0:
            return

        # Remove every error message older than 3 seconds and redraw the error list
        currentTime = time.time()
        self.messageList = [message for message in self.messageList if currentTime - message[1] < 3]
        self.showMessages()

    def getCommands(self):
        self.commandsText = []

        self.supportedCommands = ["init", "insert", "edit", "generate", "rm", "mv", "cp"]

        # We will crash here if pass is not installed.
        # TODO: Find a nice way to notify the user they need to install pass
        commandText = check_output(["pass", "--help"])

        for line in commandText.splitlines():
            strippedLine = line.lstrip().decode("utf-8")
            if strippedLine[:4] == "pass":
                command = strippedLine[5:]
                for supportedCommand in self.supportedCommands:
                    if command.startswith(supportedCommand):
                        self.commandsText.append(command)

    def getPasswords(self):
        self.passwordList = []

        passDir = expanduser("~") + "/.password-store/"

        unsortedPasswords = []
        for root, dirs, files in os.walk(passDir):
            for name in files:
                if name[-4:] != ".gpg":
                    continue

                unsortedPasswords.append(os.path.join(root, name))

        for password in sorted(unsortedPasswords, key=lambda name: os.path.getatime(os.path.join(root, name)), reverse=True):
            self.passwordList.append(password[len(passDir):-4])

    def goUp(self):
        if QQmlProperty.read(self.searchInputModel, "text") != "":
            QQmlProperty.write(self.searchInputModel, "text", "")
            return

        if self.chosenEntry == None:
            self.window.close()
            return

        self.chosenEntry = None
        self.search()

    def tabComplete(self):
        currentInput = QQmlProperty.read(self.searchInputModel, "text")
        stringToMatch = None
        for entry in self.filteredList:
            if entry in self.commandsText:
                continue

            if stringToMatch == None:
                stringToMatch = entry
            else:
                for i in range(0, len(stringToMatch)):
                    if entry[i] != stringToMatch[i]:
                        stringToMatch = stringToMatch[:i]
                        break

        possibleCommand = currentInput.split(" ", 1)[0]
        output = stringToMatch
        for command in self.commandsText:
            if command.startswith(possibleCommand):
                output = possibleCommand + " " + stringToMatch
                break

        if len(output) <= len(currentInput):
            self.addError("No tab completion possible")
            return

        QQmlProperty.write(self.searchInputModel, "text", output)
        self.search()

    def search(self):
        if self.chosenEntry != None:
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
        for password in self.passwordList:
            if all(searchString in password.lower() for searchString in searchStrings):
                self.filteredList.append(password)

        self.resultListModelMaxIndex = len(self.filteredList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)

        for command in self.commandsText:
            if searchStrings[0] in command:
                commandList.append(command)

        if len(self.filteredList) == 0 and len(commandList) > 0:
            self.filteredList = commandList
            for password in self.passwordList:
                if any(searchString in password.lower() for searchString in searchStrings[1:]):
                    self.filteredList.append(password)
        else:
            self.filteredList += commandList

        self.resultListModelList = QStringListModel(self.filteredList)
        self.context.setContextProperty("resultListModel", self.resultListModelList)

        if self.resultListModelMaxIndex == -1:
            currentIndex = -1
        elif currentItem == None:
            currentIndex = 0
        else:
            try:
                currentIndex = self.filteredList.index(currentItem)
            except ValueError:
                currentIndex = 0

        QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex)

    def searchChosenEntry(self):
        # Ensure this entry still exists
        if self.chosenEntry not in self.passwordList:
            self.addError(self.chosenEntry + " is no longer available")
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
            if any(searchString in entry.lower() for searchString in searchStrings):
                self.filteredList.append(entry)

        try:
           currentIndex = self.filteredList.index(currentItem)
        except ValueError:
           currentIndex = 0

        self.resultListModelList = QStringListModel(self.filteredList)
        self.context.setContextProperty("resultListModel", self.resultListModelList)

        QQmlProperty.write(self.resultListModel, "currentIndex", currentIndex)

    def select(self):
        if self.chosenEntry != None:
            self.selectField()
            return

        if len(self.filteredList) == 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")

        if currentIndex == -1:
            commandTyped = QQmlProperty.read(self.searchInputModel, "text").split(" ")
            if commandTyped[0] not in self.supportedCommands:
                return

            if commandTyped[0] == "edit" and len(commandTyped) == 2:
                prefillData = self.runCommand(["pass", commandTyped[1]])
                if prefillData == None:
                    prefillData = ''
                result = self.runCommand(["pass", "insert", "-fm", commandTyped[1]], True, prefillData.rstrip())
            else:
                callCommand = ["pass"] + commandTyped
                result = self.runCommand(callCommand, True)

            if result != None:
                QQmlProperty.write(self.searchInputModel, "text", "")

            return

        self.chosenEntry = self.filteredList[currentIndex]
        passwordEntryContent = self.runCommand(["pass", self.chosenEntry]).rstrip().split("\n")

        if len(passwordEntryContent) == 1:
            call(["pass", "-c", self.chosenEntry])
            self.window.close()
            return

        # The first line is most likely the password. Do not show this on the
        # screen
        passwordEntryContent[0] = "********"

        # If the password entry has more than one line, fill the result list
        # with all lines, so the user can choose the line they want to copy to
        # the clipboard
        self.chosenEntryList = passwordEntryContent
        self.filteredList = passwordEntryContent

        self.resultListModelList = QStringListModel(self.filteredList)
        self.context.setContextProperty("resultListModel", self.resultListModelList)
        self.resultListModelMaxIndex = len(self.filteredList) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)
        self.context.setContextProperty("resultListModelMakeItalic", False)
        QQmlProperty.write(self.resultListModel, "currentIndex", 0)
        QQmlProperty.write(self.searchInputModel, "text", "")

    def selectField(self):
        if len(self.filteredList) == 0:
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if self.filteredList[currentIndex] == "********":
            call(["pass", "-c", self.chosenEntry])
            self.window.close()
            return

        # Only copy the final part. For example, if the entry is named
        # "URL: https://example.org/", only copy "https://example.org/" to the
        # clipboard
        copyStringParts = self.filteredList[currentIndex].split(": ", 1)

        copyString = copyStringParts[1] if len(copyStringParts) > 1 else copyStringParts[0]

        # Use the same clipboard that password store is set to use (untested)
        selection = os.getenv("PASSWORD_STORE_X_SELECTION", "clipboard")

        proc = Popen(["xclip", "-selection", selection], stdin=PIPE)
        proc.communicate(copyString.encode("ascii"))
        self.window.close()
        return

class InputDialog(QDialog):
    def __init__(self, question, text, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Input needed")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(question))
        self.textEdit = QTextEdit(self)
        self.textEdit.setPlainText(text)
        layout.addWidget(self.textEdit)
        button = QDialogButtonBox(QDialogButtonBox.Ok)
        button.accepted.connect(self.accept)
        layout.addWidget(button)

    def show(self):
        result = self.exec_()
        return (self.textEdit.toPlainText(), result == QDialog.Accepted)

class Window(QDialog):
    def __init__(self, vm, settings, parent=None):
        super().__init__(parent)

        self.engine = QQmlApplicationEngine(self)

        self.vm = vm

        context = self.engine.rootContext()
        context.setContextProperty("resultListModel", self.vm.resultListModelList)
        context.setContextProperty("resultListModelMaxIndex", self.vm.resultListModelMaxIndex)
        context.setContextProperty("resultListModelMakeItalic", True)
        context.setContextProperty("messageListModelList", self.vm.messageListModelList)

        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        escapeShortcut = self.window.findChild(QObject, "escapeShortcut")
        tabShortcut = self.window.findChild(QObject, "tabShortcut")
        searchInputModel = self.window.findChild(QObject, "searchInputModel")
        resultListModel = self.window.findChild(QObject, "resultListModel")
        clearOldMessagesTimer = self.window.findChild(QObject, "clearOldMessagesTimer")

        self.vm.bindContext(context, self, searchInputModel, resultListModel)

        escapeShortcut.activated.connect(self.vm.goUp)
        tabShortcut.activated.connect(self.vm.tabComplete)

        searchInputModel.textChanged.connect(self.vm.search)
        searchInputModel.accepted.connect(self.vm.select)

        clearOldMessagesTimer.triggered.connect(self.vm.clearOldMessages)

    def show(self):
        self.window.show()
        self.activateWindow()

    def close(self):
        if not settings['closeWhenDone']:
            self.window.hide()
            QQmlProperty.write(self.vm.searchInputModel, "text", "")
            self.vm.chosenEntry = None
            self.vm.search()
        else:
            sys.exit(0)

def loadSettings(argv):
    # Default options
    settings = {'closeWhenDone': False}

    try:
        opts, args = getopt.getopt(argv, "h", ["--help", "close-when-done"])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, args in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == "--close-when-done":
            settings['closeWhenDone'] = True

    return settings

def usage():
    print("Options:")
    print("")
    print("--close-when-done : close after completing an action such as copying")
    print("                    a password or closing the application (through ")
    print("                    escape or (on most systems) Alt+F4) instead of ")
    print("                    staying in memory. This also allows multiple ")
    print("                    instances to be ran at once.")

def initPersist():
    # Ensure only one PyPass instance is running. If one already exists,
    # signal it to open the password selection window.
    # This way, we can keep the password list in memory and start up extra
    # quickly.
    pidfile = "/tmp/pypass.pid"

    if os.path.isfile(pidfile):
        # Notify the main process
        os.kill(int(open(pidfile, 'r').read()), signal.SIGUSR1)
        sys.exit()

    # We are the only instance, claim our pidfile
    pid = str(os.getpid())
    open(pidfile, 'w').write(pid)

def mainLoop(app, q, vm, window):
    while True:
        try:
            q.get_nowait()
        except Empty:
            app.processEvents()
            continue

        vm.search()
        window.update()
        q.task_done()

if __name__ == "__main__":
    settings = loadSettings(sys.argv[1:])

    if not settings['closeWhenDone']:
        initPersist()

    # Set up a queue so that the EventHandler can tell the main thread to
    # redraw the UI.
    q = Queue()

    app = QApplication(sys.argv)

    # Set up the window
    viewModel = ViewModel()
    window = Window(viewModel, settings)

    # Handle signal
    signalHandler = SignalHandler(window)
    signal.signal(signal.SIGUSR1, signalHandler.handle)

    # Initialize the EventHandler and make it watch the password store
    eventHandler = EventHandler(viewModel, q)
    watchManager = pyinotify.WatchManager()
    notifier = pyinotify.ThreadedNotifier(watchManager, eventHandler)
    watchedEvents = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | pyinotify.IN_OPEN
    watchManager.add_watch(expanduser("~") + "/.password-store/", watchedEvents, rec=True, auto_add=True)
    notifier.daemon = True
    notifier.start()

    # Run until the app quits, then clean up
    window.show()
    mainLoop(app, q, viewModel, window)
    sys.exit(app.exec_())
    notifier.stop()

    if not settings['closeWhenDone']:
        os.unlink(pidfile)

