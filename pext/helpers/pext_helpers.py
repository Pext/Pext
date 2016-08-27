#!/usr/bin/env python3

# Copyright 2016 (c) Sylvia van Os <iamsylvie@openmailbox.org>
#
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
        self.q.put([Action.addMessage, "message to show"])

    criticalError:
        Show an error message on the screen and unload the module.
        This function is also called when the module throws an exception.

        message -- error message to show

    addMessage:
        Show a message on the screen.

        message -- message to show

    addError:
        Show an error message on the screen.

        message -- error message to show

    addEntry:
        Add an entry to the entry list.

        entry -- the entry

    prependEntry:
        Prepend an entry to the entry list.

        entry -- the entry

    removeEntry:
        Remove an entry from the entry list.

        entry -- the entry

    replaceEntryList:
        Replace the list of entries with the given list.

        list -- the new list of entries

    addCommand:
        Add an entry to the command list.

        entry -- the entry

    prependCommand:
        Prepend an entry to the command list.

        entry -- the entry

    removeCommand:
        Remove a command from the entry list.

        entry -- the entry

    replaceCommandList:
        Replace the list of commands with the given list.

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

    copyToClipboard:
        Request the specific data to be copied to the clipboard.

        text -- the text to copy to the clipboard

    setSelection:
        Change the internal Pext selected entry for this module.

        The internal Pext selected entry contains an array of the path the
        user has taken in selection and thus looks like follows:
        ["Settings", "Audio", "Mute"].

        To go a single level up, simply remove the last entry from this list.
        To reset to the main screen, use an empty list.

        list -- the selection hierarchy.

    notifyMessage:
        Notify the user.

        message -- the message to show

    notifyError:
        Notify the user of an error.

        message -- the error message to show

    close:
        Close the window.

        Call this when the user is done. For example, when the user made a
        selection.

    """
    criticalError = 0
    addMessage = 1
    addError = 2
    addEntry = 3
    prependEntry = 4
    removeEntry = 5
    replaceEntryList = 6
    addCommand = 7
    prependCommand = 8
    removeCommand = 9
    replaceCommandList = 10
    setFilter = 11
    askQuestionDefaultYes = 12
    askQuestionDefaultNo = 13
    askInput = 14
    askInputPassword = 15
    askInputMultiLine = 16
    copyToClipboard = 17
    setSelection = 18
    notifyMessage = 19
    notifyError = 20
    close = 21

class SelectionType(Enum):
    """A list of possible selection types."""
    entry = 0
    command = 1
