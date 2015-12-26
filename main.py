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

import sys
import os
import time
from os.path import expanduser
from subprocess import call, check_output, Popen, CalledProcessError, PIPE
from threading import Timer

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.Qt import QQmlApplicationEngine, QObject, QQmlProperty, QUrl

class ViewModel():
    def __init__(self):
        self.getCommands()
        self.getPasswords()

        # Temporary values to allow binding. These will be properly set when 
        # possible and relevant.
        self.filteredList = []
        self.resultListModelList = QStringListModel()
        self.resultListModelMaxIndex = -1
        self.errorMessageModelText = ""
        self.errorUpdateTime = time.time()
        self.chosenEntry = None
        self.passwordEntryContent = None

    def bindContext(self, context, searchInputModel, resultListModel):
        self.context = context
        self.searchInputModel = searchInputModel
        self.resultListModel = resultListModel

        self.search()

    def runCommand(self, command):
        proc = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = proc.communicate()
        if proc.returncode == 0:
            return output
        else:
            self.errorMessageModelText = error.decode("utf-8").rstrip() if error else "Error code {} running '{}'. More info may be logged to the console".format(str(errorCode), " ".join(command))
            self.context.setContextProperty("errorMessageModelText", self.errorMessageModelText)
            self.context.setContextProperty("errorMessageModelLineHeight", 1)

            self.errorUpdateTime = time.time()

            return None

    def clearOldError(self):
        if time.time() - self.errorUpdateTime > 3:
            self.errorMessageModelText = ""
            self.context.setContextProperty("errorMessageModelText", self.errorMessageModelText)
            self.context.setContextProperty("errorMessageModelLineHeight", 0)

    def getCommands(self):
        self.commandsText = []

        self.supportedCommands = {"generate": [], "rm": ["-f"], "mv": ["-f"], "cp": ["-f"]}

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
        if self.passwordEntryContent != None:
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
                if all(searchString in password.lower() for searchString in searchStrings[1:]):
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
        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        currentItem = self.passwordEntryContent[currentIndex]

        searchStrings = QQmlProperty.read(self.searchInputModel, "text").lower().split(" ")

        self.filteredList = []

        for entry in self.passwordEntryContent:
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
        if self.passwordEntryContent != None:
            self.selectField()
            return

        if len(self.filteredList) == 0: return

        currentIndex = QQmlProperty.read(self.resultListModel, "currentIndex")
        if currentIndex == -1:
            currentIndex = 0

        self.chosenEntry = self.filteredList[currentIndex]

        if self.chosenEntry in self.commandsText:
            callCommand = ["pass"] + QQmlProperty.read(self.searchInputModel, "text").split(" ") + self.supportedCommands[self.chosenEntry.split(" ")[0]]
            result = self.runCommand(callCommand)

            if result != None:
                self.getPasswords()
                QQmlProperty.write(self.searchInputModel, "text", "")

            return

        self.passwordEntryContent = self.runCommand(["pass", self.chosenEntry]).decode("utf-8").rstrip().split("\n")

        if len(self.passwordEntryContent) == 1:
            exit(call(["pass", "-c", self.chosenEntry]))

        # The first line is most likely the password. Do not show this on the 
        # screen
        self.passwordEntryContent[0] = "********"

        # If the password entry has more than one line, fill the result list 
        # with all lines, so the user can choose the line they want to copy to 
        # the clipboard
        self.resultListModelList = QStringListModel(self.passwordEntryContent)
        self.context.setContextProperty("resultListModel", self.resultListModelList)
        self.resultListModelMaxIndex = len(self.passwordEntryContent) - 1
        self.context.setContextProperty("resultListModelMaxIndex", self.resultListModelMaxIndex)
        self.context.setContextProperty("resultListModelMakeItalic", False)
        QQmlProperty.write(self.resultListModel, "currentIndex", 0)
        QQmlProperty.write(self.searchInputModel, "text", "")

    def selectField(self):
        currentIndex = self.passwordEntryContent.index(self.filteredList[QQmlProperty.read(self.resultListModel, "currentIndex")])
        if currentIndex == 0:
            exit(call(["pass", "-c", self.chosenEntry]))

        # Only copy the final part. For example, if the entry is named 
        # "URL: https://example.org/", only copy "https://example.org/" to the 
        # clipboard
        copyStringParts = self.passwordEntryContent[currentIndex].split(": ", 1)

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
        context.setContextProperty("errorMessageModelText", self.vm.errorMessageModelText)
        context.setContextProperty("errorMessageModelLineHeight", 0)

        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        searchInputModel = self.window.findChild(QObject, "searchInputModel")
        resultListModel = self.window.findChild(QObject, "resultListModel")
        clearErrorMessageTimer = self.window.findChild(QObject, "clearErrorMessageTimer")

        self.vm.bindContext(context, searchInputModel, resultListModel)

        searchInputModel.textChanged.connect(self.vm.search)
        searchInputModel.accepted.connect(self.vm.select)

        clearErrorMessageTimer.triggered.connect(self.vm.clearOldError)

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())

