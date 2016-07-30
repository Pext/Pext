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

from enum import Enum


class Action(Enum):
    """A list of actions that the module can request of the core by putting it
    in the queue. All of this actions need to be accompanied by a list of
    arguments.

    Example:
        self.q.put(Action.addMessage, ["message to show"])

    addMessage:
        Show a message on the screen.

        message -- message to show

    addError:
        Show an error message on the screen.

        message -- error message to show

    prependEntry:
        Prepend an entry to the entry list.

        identifier -- the identifier of the entry
        searchable name -- the searchable name of the entry

    removeEntry:
        Remove an entry from the entry list.

        identifier -- the identifier of the entry
        searchable name -- the searchable name of the entry

    replaceEntryList:
        Replace the list of entries with the given list.

        list -- the new list of entries

    setFilter:
        Replace the text currently in the search bar.

        filter -- the new text to put in the search bar

    askQuestionDefaultYes:
        Ask a yes/no question, with the default value being yes.

        question -- the question to ask

    askQuestionDefaultNo:
        Ask a yes/no question, with the default value being no.

        question -- the question to ask

    askInput:
        Ask the user to input a single line of text.

        text -- the text to show the user, such as "Please enter code"

    askInputPassword:
        Ask the user to input a single line of text into a password field.

        text -- the text to show the user, such as "Please enter code"

    askInputMultiLine:
        Ask the user to input one or more lines of text.

        text -- the text to show the user, such as "Please enter code"
        prefill -- the text to already put into the input field
    """
    addMessage = 1
    addError = 2
    prependEntry = 3
    removeEntry = 4
    replaceEntryList = 5
    setFilter = 6
    askQuestionDefaultYes = 7
    askQuestionDefaultNo = 8
    askInput = 9
    askInputPassword = 10
    askInputMultiLine = 11
