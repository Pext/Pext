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
        self.filteredPasswordList = self.passwordList
        self.listViewModelPasswordList = QStringListModel(self.filteredPasswordList)
        self.listViewModelIndexMax = len(self.passwordList) - 1

    def bindViews(self, searchInput, listView, errorMessage):
        self.searchInput = searchInput
        self.listView = listView
        self.errorMessage = errorMessage

        self.errorUpdateTime = time.time()
        self.clearOldError()

    def stop(self):
        self.clearOldErrorUpdateTimer.cancel()

    def runCommand(self, command, closeWhenDone=False):
        proc = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = proc.communicate()
        if (proc.returncode == 0):
            return output
        else:
            QQmlProperty.write(self.errorMessage, "text", error.decode("utf-8").rstrip() if error else "Error code {} running '{}'. More info may be logged to the console".format(str(errorCode), " ".join(command)))
            QQmlProperty.write(self.errorMessage, "lineHeight", 1)

            self.errorUpdateTime = time.time()

            return None

    def clearOldError(self):
        if time.time() - self.errorUpdateTime > 5:
            QQmlProperty.write(self.errorMessage, "text", "")

        if QQmlProperty.read(self.errorMessage, "text") == "":
            QQmlProperty.write(self.errorMessage, "lineHeight", 0)

        self.clearOldErrorUpdateTimer = Timer(1, self.clearOldError)
        self.clearOldErrorUpdateTimer.start()

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
        currentIndex = QQmlProperty.read(self.listView, "currentIndex")
        if currentIndex == -1:
            currentIndex = 0

        self.filteredPasswordList = [];
        commandList = []

        searchStrings = QQmlProperty.read(self.searchInput, "text").lower().split(" ")
        for password in self.passwordList:
            if all(searchString in password.lower() for searchString in searchStrings):
                self.filteredPasswordList.append(password)

        self.listViewModelIndexMax = len(self.filteredPasswordList) - 1
        QQmlProperty.write(self.listView, "maximumIndex", self.listViewModelIndexMax)

        for command in self.commandsText:
            if (searchStrings[0] in command):
                commandList.append(command)

        if len(self.filteredPasswordList) == 0 and len(commandList) > 0:
            self.filteredPasswordList = commandList
            for password in self.passwordList:
                if(all(searchString in password.lower() for searchString in searchStrings[1:])):
                    self.filteredPasswordList.append(password)
        else:
            self.filteredPasswordList += commandList

        QQmlProperty.write(self.listView, "model", QStringListModel(self.filteredPasswordList))
        if (currentIndex > self.listViewModelIndexMax):
            QQmlProperty.write(self.listView, "currentIndex", self.listViewModelIndexMax)
        else:
            QQmlProperty.write(self.listView, "currentIndex", currentIndex)

    def select(self):
        if len(self.filteredPasswordList) == 0: return

        currentIndex = QQmlProperty.read(self.listView, "currentIndex")
        if currentIndex == -1:
            currentIndex = 0

        chosenEntry = self.filteredPasswordList[currentIndex]

        if chosenEntry in self.commandsText:
            callCommand = ["pass"] + QQmlProperty.read(self.searchInput, "text").split(" ") + self.supportedCommands[chosenEntry.split(" ")[0]]
            self.runCommand(callCommand)

            self.getPasswords()
            QQmlProperty.write(self.searchInput, "text", "")
            return

        # pass forks itself to sleep for 45 seconds before clearing the 
        # clipboard, which means we can't use self.runCommand here, or we 
        # just plain lock up.
        # TODO: Find a way to check for issues copying the password to the 
        # clipboard. This could fail for example if the GPG key used for 
        # decrypting is not available, among other reasons.
        self.stop()
        exit(call(["pass", "-c", chosenEntry]))
        
class Window(QDialog):
    def __init__(self, vm, parent=None):
        super().__init__(parent)

        self.engine = QQmlApplicationEngine(self)

        self.vm = vm

        context = self.engine.rootContext()
        context.setContextProperty("listViewModel", self.vm.listViewModelPasswordList)
        context.setContextProperty("listViewModelIndexMax", self.vm.listViewModelIndexMax)

        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        searchInput = self.window.findChild(QObject, "searchInput")
        resultList = self.window.findChild(QObject, "resultList")
        errorMessage = self.window.findChild(QObject, "errorMessage")

        self.vm.bindViews(searchInput, resultList, errorMessage)

        searchInput.textChanged.connect(self.vm.search)
        searchInput.accepted.connect(self.vm.select)

    def show(self):
        self.window.show()

if __name__ == "__main__":
    vm = ViewModel()
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(vm.stop)
    w = Window(vm)
    w.show()
    sys.exit(app.exec_())

