#!/usr/bin/env python3

# Copyright (c) 2016 - 2017 Sylvia van Os <sylvia@hackerchick.me>
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

"""Pext Helpers.

This file contains various functionality that is relevant to both Pext
and modules and helps keep the API consistent.
"""

from enum import Enum


class Action(Enum):
    """The list of actions a module can request.

    A module can request any of these actions of the core by putting it in the
    queue. All of these actions need to be accompanied by a list of arguments.

    Example:
        self.q.put([Action.add_message, "message to show"])

    critical_error:
        Show an error message on the screen and unload the module.
        This function is also called when the module throws an exception.

        message -- error message to show

    add_message:
        Show a message on the screen.

        message -- message to show

    add_error:
        Show an error message on the screen.

        message -- error message to show

    add_entry:
        Add an entry to the entry list.

        entry -- the entry

    prepend_entry:
        Prepend an entry to the entry list.

        entry -- the entry

    remove_entry:
        Remove an entry from the entry list.

        entry -- the entry

    replace_entry_list:
        Replace the list of entries with the given list.

        list -- the new list of entries

    add_command:
        Add an entry to the command list.

        entry -- the entry

    prepend_command:
        Prepend an entry to the command list.

        entry -- the entry

    remove_command:
        Remove a command from the entry list.

        entry -- the entry

    replace_command_list:
        Replace the list of commands with the given list.

        list -- the new list of entries

    set_header:
        Set or replace the text currently in the header bar.

        If header is not given, the header will be removed.

        header -- the new header text

    set_filter:
        Replace the text currently in the search bar.

        filter -- the new text to put in the search bar

    ask_question_default_yes:
        Ask a yes/no question, with the default value being yes.

        question -- the question to ask

    ask_question_default_no:
        Ask a yes/no question, with the default value being no.

        question -- the question to ask

    ask_input:
        Ask the user to input a single line of text.

        text -- the text to show the user, such as "Please enter code"

    ask_input_password:
        Ask the user to input a single line of text into a password field.

        text -- the text to show the user, such as "Please enter code"

    ask_input_multi_line:
        Ask the user to input one or more lines of text.

        text -- the text to show the user, such as "Please enter code"
        prefill -- the text to already put into the input field

    copy_to_clipboard:
        Request the specific data to be copied to the clipboard.

        text -- the text to copy to the clipboard

    set_selection:
        Change the internal Pext selected entry for this module.

        The internal Pext selected entry contains an array of the path the
        user has taken in selection and thus looks like follows:
        ["Settings", "Audio", "Mute"].

        To go a single level up, simply remove the last entry from this list.
        To reset to the main screen, use an empty list.

        list -- the selection hierarchy.

    notify_message:
        Notify the user.

        message -- the message to show

    notify_error:
        Notify the user of an error.

        message -- the error message to show

    close:
        Close the window.

        Call this when the user is done. For example, when the user made a
        selection.
    """

    critical_error = 0
    add_message = 1
    add_error = 2
    add_entry = 3
    prepend_entry = 4
    remove_entry = 5
    replace_entry_list = 6
    add_command = 7
    prepend_command = 8
    remove_command = 9
    replace_command_list = 10
    set_header = 11
    set_filter = 12
    ask_question_default_yes = 13
    ask_question_default_no = 14
    ask_input = 15
    ask_input_password = 16
    ask_input_multi_line = 17
    copy_to_clipboard = 18
    set_selection = 19
    notify_message = 20
    notify_error = 21
    close = 22


class SelectionType(Enum):
    """A list of possible selection types."""

    entry = 0
    command = 1
