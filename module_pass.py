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

import re
import os
from os.path import expanduser
from subprocess import call, check_output
from shlex import quote

import pexpect

from module_base import ModuleBase
from helpers import Action

import pyinotify


class Module(ModuleBase):
    def __init__(self, binary, q):
        self.binary = "pass" if (binary is None) else binary

        self.q = q

        self.ANSIEscapeRegex = re.compile('(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

        self.initInotify(q)

    def initInotify(self, q):
        # Initialize the EventHandler and make it watch the password store
        eventHandler = EventHandler(q, self)
        watchManager = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(watchManager, eventHandler)
        watchedEvents = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | pyinotify.IN_OPEN
        watchManager.add_watch(self.getDataLocation(), watchedEvents, rec=True, auto_add=True)
        self.notifier.daemon = True
        self.notifier.start()

    def stop(self):
        self.notifier.stop()

    def getDataLocation(self):
        return expanduser("~") + "/.password-store/"

    def call(self, command):
        call([self.binary] + command)

    def getSupportedCommands(self):
        return ["init", "insert", "edit", "generate", "rm", "mv", "cp"]

    def getCommands(self):
        commandsText = []

        # We will crash here if pass is not installed.
        # TODO: Find a nice way to notify the user they need to install pass
        commandText = check_output([self.binary, "--help"])

        for line in commandText.splitlines():
            strippedLine = line.lstrip().decode("utf-8")
            if strippedLine[:4] == "pass":
                command = strippedLine[5:]
                for supportedCommand in self.getSupportedCommands():
                    if command.startswith(supportedCommand):
                        commandsText.append(command)

        return commandsText

    def getEntries(self):
        passDir = self.getDataLocation()

        unsortedPasswords = []
        for root, dirs, files in os.walk(passDir):
            for name in files:
                if name[-4:] == ".gpg":
                    unsortedPasswords.append(os.path.join(root, name))

        return [password[len(passDir):-4] for password in sorted(unsortedPasswords, key=lambda name: os.path.getatime(os.path.join(root, name)), reverse=True)]

    def copyEntryToClipboard(self, entryName):
        self.call(["show", "-c", entryName])

    def getAllEntryFields(self, entryName):
        return self.runCommand(["show", entryName], hideErrors=True).rstrip().split("\n")

    def runCommand(self, command, printOnSuccess=False, hideErrors=False, prefillInput=''):
        # If we edit a password, make sure to get the original input first so we can show the user
        if command[0] == "edit" and len(command) == 2:
            prefillData = self.runCommand(["show", command[1]], hideErrors=True)
            if prefillData is None:
                prefillData = ''
            return self.runCommand(["insert", "-fm", command[1]], printOnSuccess=True, prefillInput=prefillData.rstrip())

        sanitizedCommandList = [quote(commandPart) for commandPart in command]

        proc = pexpect.spawn('/bin/sh', ['-c', self.binary + " " + " ".join(sanitizedCommandList) + (" 2>/dev/null" if hideErrors else "")])
        return self.processProcOutput(proc, printOnSuccess, hideErrors, prefillInput)

    def processProcOutput(self, proc, printOnSuccess=False, hideErrors=False, prefillInput=''):
        result = proc.expect_exact([pexpect.EOF, pexpect.TIMEOUT, "[Y/n]", "[y/N]", "Enter password ", "Retype password ", " and press Ctrl+D when finished:"], timeout=3)
        if result == 0:
            exitCode = proc.sendline("echo $?")
        elif result == 1 and proc.before:
            self.q.put([Action.addError, "Timeout error while running '{}'. This specific way of calling the command is most likely not supported yet by Pext.".format(" ".join(command))])
            self.q.put([Action.addError, "Command output: {}".format(self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")))])
        elif result == 2 or result == 3:
            proc.setecho(False)
            question = proc.before.decode("utf-8")

            if (result == 2):
                self.proc = {'proc': proc,
                             'type': Action.askQuestionDefaultYes,
                             'printOnSuccess': printOnSuccess,
                             'hideErrors': hideErrors,
                             'prefillInput': prefillInput}
                self.q.put([Action.askQuestionDefaultYes, question])
            else:
                self.proc = {'proc': proc,
                             'type': Action.askQuestionDefaultNo,
                             'printOnSuccess': printOnSuccess,
                             'hideErrors': hideErrors,
                             'prefillInput': prefillInput}
                self.q.put([Action.askQuestionDefaultNo, question])

            return
        elif result == 4 or result == 5:
            printOnSuccess = False
            proc.setecho(False)
            self.proc = {'proc': proc,
                         'type': Action.askInputPassword,
                         'printOnSuccess': printOnSuccess,
                         'hideErrors': hideErrors,
                         'prefillInput': prefillInput}
            self.q.put([Action.askInputPassword, proc.after.decode("utf-8")])

            return
        elif result == 6:
            self.proc = {'proc': proc,
                         'type': Action.askInputMultiLine,
                         'printOnSuccess': printOnSuccess,
                         'hideErrors': hideErrors,
                         'prefillInput': prefillInput}
            self.q.put([Action.askInputMultiLine, proc.before.decode("utf-8").lstrip(), prefillInput])

            proc.setecho(False)

            return

        proc.close()
        exitCode = proc.exitstatus

        message = self.ANSIEscapeRegex.sub('', proc.before.decode("utf-8")) if proc.before else ""

        self.q.put([Action.setFilter, ""])

        if exitCode == 0:
            if printOnSuccess and message:
                self.q.put([Action.addMessage, message])

            return message
        else:
            self.q.put([Action.addError, message if message else "Error code {} running '{}'. More info may be logged to the console".format(str(exitCode), " ".join(command))])

            return None

    def processResponse(self, response):
        if self.proc['type'] == Action.askQuestionDefaultYes or self.proc['type'] == Action.askQuestionDefaultNo:
            self.proc['proc'].waitnoecho()
            self.proc['proc'].sendline('y' if response else 'n')
            self.proc['proc'].setecho(True)
        elif self.proc['type'] == Action.askInput or self.proc['type'] == Action.askInputPassword:
            self.proc['proc'].waitnoecho()
            if response is None:
                self.proc['proc'].close()
            else:
                self.proc['proc'].sendline(response)
                self.proc['proc'].setecho(True)
        elif self.proc['type'] == Action.askInputMultiLine:
            self.proc['proc'].waitnoecho()
            if response is None:
                # At this point, pass won't let us exit out safely, so we
                # write the prefilled data
                for line in self.proc['prefillInput'].splitlines():
                    self.proc['proc'].sendline(line)
            else:
                for line in response.splitlines():
                    self.proc['proc'].sendline(line)

            self.proc['proc'].sendcontrol("d")
            self.proc['proc'].setecho(True)

        self.processProcOutput(self.proc['proc'], printOnSuccess=self.proc['printOnSuccess'], hideErrors=self.proc['hideErrors'], prefillInput=self.proc['prefillInput'])

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, q, store):
        self.q = q
        self.store = store

    def process_IN_CREATE(self, event):
        if event.dir:
            return

        entryName = event.pathname[len(self.store.getDataLocation()):-4]

        self.q.put([Action.prependEntry, entryName])

    def process_IN_DELETE(self, event):
        if event.dir:
            return

        entryName = event.pathname[len(self.store.getDataLocation()):-4]

        self.q.put([Action.removeEntry, entryName])

    def process_IN_MOVED_FROM(self, event):
        self.process_IN_DELETE(event)

    def process_IN_MOVED_TO(self, event):
        self.process_IN_CREATE(event)

    def process_IN_OPEN(self, event):
        if event.dir:
            return

        entryName = event.pathname[len(self.store.getDataLocation()):-4]

        self.q.put([Action.prependEntry, entryName])
        self.q.put([Action.removeEntry, entryName])
