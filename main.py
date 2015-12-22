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
from os.path import expanduser
from subprocess import call

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.Qt import QQmlApplicationEngine, QObject, QQmlProperty, QUrl

class ViewModel():
    def __init__(self):
        self.getPasswords()
        self.filteredPasswordList = self.passwordList
        self.listViewModelPasswordList = QStringListModel(self.filteredPasswordList)

    def bindListView(self, listView):
        self.listView = listView

    def getPasswords(self):
        self.passwordList = []

        passDir = expanduser("~") + "/.password-store/"
        for root, dirs, files in os.walk(passDir):
            for name in files:
                if name[0] == ".":
                    continue

                self.passwordList.append(os.path.join(root, name)[len(passDir):-4])

    def search(self, text):
        self.filteredPasswordList = [];
        searchStrings = text.lower().split(" ")
        for password in self.passwordList:
            if all(searchString in password.lower() for searchString in searchStrings):
                self.filteredPasswordList.append(password)

        QQmlProperty.write(self.listView, "model", QStringListModel(self.filteredPasswordList))

    def select(self):
        if len(self.filteredPasswordList) == 0: return

        exit(call(["pass", "-c", self.filteredPasswordList[0]]))
        
class Window(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.engine = QQmlApplicationEngine(self)

        self.vm = ViewModel()
        self.engine.rootContext().setContextProperty("listViewModel", self.vm.listViewModelPasswordList)

        self.engine.load(QUrl.fromLocalFile(os.path.dirname(os.path.realpath(__file__)) + "/main.qml"))

        self.window = self.engine.rootObjects()[0]

        searchInput = self.window.findChild(QObject, "searchInput")
        resultList = self.window.findChild(QObject, "resultList")

        self.vm.bindListView(resultList)

        searchInput.textChanged.connect(lambda: self.vm.search(QQmlProperty.read(searchInput, "text")))
        searchInput.accepted.connect(self.vm.select)

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())

