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

from subprocess import Popen, PIPE
from emoji import unicode_codes

from module_base import ModuleBase


class Module(ModuleBase):
    def __init__(self, binary, window, q):
        self.window = window

    def stop(self):
        pass

    def getSupportedCommands(self):
        return []

    def getCommands(self):
        return []

    def getEntries(self):
        entryList = []

        for emoji, code in sorted(unicode_codes.UNICODE_EMOJI.items()):
            entryList.append('{0} {1}'.format(emoji, code))

        return entryList

    def copyEntryToClipboard(self, entryName):
        proc = Popen(["xclip", "-selection", "clipboard"], stdin=PIPE)
        proc.communicate(entryName.split(" ")[0].encode("utf-8"))

    def getAllEntryFields(self, entryName):
        return ['']

    def runCommand(self, command, printOnSuccess=False, hideErrors=False):
        pass
