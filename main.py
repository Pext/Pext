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

import os
import re
import sys
import time
from os.path import expanduser
from subprocess import call, check_output, Popen, CalledProcessError, PIPE
from threading import Timer

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.Qt import QQmlApplicationEngine, QObject, QQmlProperty, QUrl

import pexpect

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

    def bindContext(self, context, searchInputModel, resultListModel):
        self.context = context
        self.searchInputModel = searchInputModel
        self.resultListModel = resultListModel

        self.search()

    def addError(self, message):
        messagePrepended = []
        for line in message.splitlines():
            messagePrepended.append("<font color='red'>{}</color>".format(line))

        self.messageList.append(["\n".join(messagePrepended), time.time()])
        self.showMessages()

    def addMessage(self, message):
        messagePrepended = []
        for line in message.splitlines():
            messagePrepended.append(line)

        self.messageList.append(["\n".join(messagePrepended), time.time()])
        self.showMessages()

    def showMessages(self):
        messageListForModel = []
        for message in self.messageList:
            messageListForModel.append(message[0])
        self.messageListModelList = QStringListModel(messageListForModel)
        self.context.setContextProperty("messageListModelList", self.messageListModelList)

    def runCommand(self, command, printOnSuccess=False):
        proc = pexpect.spawn(command[0], command[1:])
        while True:
            result = proc.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=0.1)
            if result == 0:
                exitCode = proc.sendline("echo $?")
                break
            elif result == 1 and proc.before:
                self.addError("Timeout error while running '{}'. The command was most likely waiting for input, which is not supported yet.".format(" ".join(command)))
                self.addError("Command output: {}".format(self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")).rstrip()))

                return None

        proc.close()
        exitCode = proc.exitstatus

        message = self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")).rstrip() if proc.before else ""

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

        # Remove every error message older than 5 seconds and redraw the error list
        currentTime = time.time()
        self.messageList = [message for message in self.messageList if currentTime - message[1] < 5]
        self.showMessages()

    def getCommands(self):
        self.commandsText = []

        self.supportedCommands = ["init", "insert", "generate", "rm", "mv", "cp"]

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
        for root, dirs, files in os.walk(passDir):
            dirs.sort()
            files.sort()
            for name in files:
                if name[-4:] != ".gpg":
                    continue

                self.passwordList.append(os.path.join(root, name)[len(passDir):-4])

    def search(self):
        if self.chosenEntry != None:
            self.searchChosenEntry()
            return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex == -1 or len(self.filteredList) < currentIndex + 1:
            currentItem = None
        else:
            currentItem = self.filteredList[currentIndex]

        self.filteredList = [];
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

            callCommand = ["pass"] + commandTyped
            result = self.runCommand(callCommand, True)

            if result != None:
                self.getPasswords()
                QQmlProperty.write(self.searchInputModel, "text", "")

            return

        self.chosenEntry = self.filteredList[currentIndex]
        passwordEntryContent = self.runCommand(["pass", self.chosenEntry]).rstrip().split("\n")

        if len(passwordEntryContent) == 1:
            exit(call(["pass", "-c", self.chosenEntry]))

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
            exit(call(["pass", "-c", self.chosenEntry]))

        # Only copy the final part. For example, if the entry is named 
        # "URL: https://example.org/", only copy "https://example.org/" to the 
        # clipboard
        copyStringParts = self.filteredList[currentIndex].split(": ", 1)

        copyString = copyStringParts[1] if len(copyStringParts) > 1 else copyStringParts[0]

        # Use the same clipboard that password store is set to use (untested)
        selection = os.getenv("PASSWORD_STORE_X_SELECTION", "clipboard")

        proc = Popen(["xclip", "-selection", selection], stdin=PIPE)
        exit(proc.communicate(copyString.encode("ascii")))
        
class Window(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.engine = QQmlApplicationEngine(self)

        self.vm = ViewModel()

        context = self.engine.rootContext()
        context.setContextProperty("resultListModel", self.vm.resultListModelList)
        context.setContextProperty("resultListModelMaxIndex", self.vm.resultListModelMaxIndex)
        context.setContextProperty("resultListModelMakeItalic", True)
        context.setContextProperty("messageListModelList", self.vm.messageListModelList)

        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        searchInputModel = self.window.findChild(QObject, "searchInputModel")
        resultListModel = self.window.findChild(QObject, "resultListModel")
        clearOldMessagesTimer = self.window.findChild(QObject, "clearOldMessagesTimer")

        self.vm.bindContext(context, searchInputModel, resultListModel)

        searchInputModel.textChanged.connect(self.vm.search)
        searchInputModel.accepted.connect(self.vm.select)

        clearOldMessagesTimer.triggered.connect(self.vm.clearOldMessages)

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())

