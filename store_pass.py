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
from os.path import expanduser
from subprocess import call, check_output

from PyQt5.QtWidgets import QInputDialog, QMessageBox, QLineEdit
import pexpect

from main import InputDialog

import pyinotify

class Store():
    def __init__(self, vm, window, q):
        self.vm = vm
        self.window = window
        self.q = q

        self.initInotify(vm, q)

    def initInotify(self, vm, q):
        # Initialize the EventHandler and make it watch the password store
        eventHandler = EventHandler(vm, q, self)
        watchManager = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(watchManager, eventHandler)
        watchedEvents = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | pyinotify.IN_OPEN
        watchManager.add_watch(self.getStoreLocation(), watchedEvents, rec=True, auto_add=True)
        self.notifier.daemon = True
        self.notifier.start()

    def stop(self):
        self.notifier.stop()

    def getStoreLocation(self):
        return expanduser("~") + "/.password-store/"

    def call(self, command):
        callCommand = ["pass"] + command
        call(callCommand)

    def getSupportedCommands(self):
        return ["init", "insert", "edit", "generate", "rm", "mv", "cp"]

    def getCommands(self):
        commandsText = []

        # We will crash here if pass is not installed.
        # TODO: Find a nice way to notify the user they need to install pass
        commandText = check_output(["pass", "--help"])

        for line in commandText.splitlines():
            strippedLine = line.lstrip().decode("utf-8")
            if strippedLine[:4] == "pass":
                command = strippedLine[5:]
                for supportedCommand in self.getSupportedCommands():
                    if command.startswith(supportedCommand):
                        commandsText.append(command)

        return commandsText

    def getPasswords(self):
        passwordList = []

        passDir = self.getStoreLocation()

        unsortedPasswords = []
        for root, dirs, files in os.walk(passDir):
            for name in files:
                if name[-4:] != ".gpg":
                    continue

                unsortedPasswords.append(os.path.join(root, name))

        for password in sorted(unsortedPasswords, key=lambda name: os.path.getatime(os.path.join(root, name)), reverse=True):
            passwordList.append(password[len(passDir):-4])

        return passwordList

    def copyPasswordToClipboard(self, passwordName):
        return self.call(["-c", passwordName])

    def getAllPasswordFields(self, passwordName):
        return self.runCommand([passwordName]).rstrip().split("\n")

    def runCommand(self, command, printOnSuccess=False, prefillInput=''):
        # If we edit a password, make sure to get the original input first so we can show the user
        if command[0] == "edit" and len(command) == 2:
            prefillData = self.runCommand([command[1]])
            if prefillData == None:
                prefillData = ''
            return self.runCommand(["insert", "-fm", command[1]], True, prefillData.rstrip())

        proc = pexpect.spawn("pass", command)
        while True:
            result = proc.expect_exact([pexpect.EOF, pexpect.TIMEOUT, "[Y/n]", "[y/N]", "Enter password ", "Retype password ", " and press Ctrl+D when finished:"], timeout=3)
            if result == 0:
                exitCode = proc.sendline("echo $?")
                break
            elif result == 1 and proc.before:
                self.vm.addError("Timeout error while running '{}'. This specific way of calling the command is most likely not supported yet by PyPass.".format(" ".join(command)))
                self.vm.addError("Command output: {}".format(self.vm.ANSIEscapeRegex.sub('', proc.before.decode("utf-8"))))

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
            elif result == 4 or result == 5:
                printOnSuccess = False
                proc.setecho(False)
                answer, ok = QInputDialog.getText(self.window, "Input", proc.after.decode("utf-8"), QLineEdit.Password)
                if not ok:
                    break

                proc.waitnoecho()
                proc.sendline(answer)
                proc.setecho(True)
            elif result == 6:
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

        message = self.vm.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")) if proc.before else ""

        if exitCode == 0:
            if printOnSuccess and message:
                self.vm.addMessage(message)

            return message
        else:
            self.vm.addError(message if message else "Error code {} running '{}'. More info may be logged to the console".format(str(exitCode), " ".join(command)))

            return None

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, vm, q, store):
        self.vm = vm
        self.q = q
        self.store = store

    def process_IN_CREATE(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(self.store.getStoreLocation()):-4]

        self.vm.passwordList = [passwordName] + self.vm.passwordList
        self.q.put("created")

    def process_IN_DELETE(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(self.store.getStoreLocation()):-4]

        self.vm.passwordList.remove(passwordName)
        self.q.put("deleted")

    def process_IN_MOVED_FROM(self, event):
        self.process_IN_DELETE(event)

    def process_IN_MOVED_TO(self, event):
        self.process_IN_CREATE(event)

    def process_IN_OPEN(self, event):
        if event.dir:
            return

        passwordName = event.pathname[len(self.store.getStoreLocation()):-4]

        try:
            self.vm.passwordList.remove(passwordName)
        except ValueError:
            # process_IN_OPEN is also called when moving files, after the
            # initial move event. In this case, we want to do nothing and let
            # IN_MOVED_FROM and IN_MOVED_TO handle this
            return

        self.vm.passwordList = [passwordName] + self.vm.passwordList
        self.q.put("opened")

