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
    """Introduced in API version 0.1.0.

    The list of actions a module can request.

    A module can request any of these actions of the core by putting it in the
    queue. All of these actions need to be accompanied by a list of arguments.
    In these examples, we assume that you have assigned the queue variable to
    self.q, a common practice in Pext modules.

    critical_error
        Introduced in API version 0.1.0.

        Show an error message on the screen and unload the module.
        This function is also called when the module throws an exception.

        message -- error message to show

        Example: self.q.put([Action.critical_error, "Something went wrong!"])

    add_message
        Introduced in API version 0.1.0.

        Show a message on the screen.

        message -- message to show

        Example: self.q.put([Action.add_message, "We did a thing"])

    add_error
        Introduced in API version 0.1.0.

        Show an error message on the screen.

        message -- error message to show

        Example: self.q.put([Action.add_error, "We did a thing, but it went wrong"])

    add_entry
        Introduced in API version 0.1.0.

        Add an entry to the entry list.

        entry -- the entry

        Example: self.q.put([Action.add_entry, "Audio settings"])

    prepend_entry
        Introduced in API version 0.1.0.

        Prepend an entry to the entry list.

        entry -- the entry

        Example: self.q.put([Action.prepend_entry, "Audio settings"])

    remove_entry
        Introduced in API version 0.1.0.

        Remove an entry from the entry list.

        entry -- the entry

        Example: self.q.put([Action.remove_entry, "Audio settings"])

    replace_entry_list
        Introduced in API version 0.1.0.

        Replace the list of entries with the given list.

        list -- the new list of entries

        Example: self.q.put([Action.replace_entry_list, ["Audio settings", "Video settings"]])

    add_command
        Introduced in API version 0.1.0.

        Add an entry to the command list.

        entry -- the entry

        Example: self.q.put([Action.add_command, "download"])

    prepend_command
        Introduced in API version 0.1.0.

        Prepend an entry to the command list.

        entry -- the entry

        Example: self.q.put([Action.prepend_command, "download"])

    remove_command
        Introduced in API version 0.1.0.

        Remove a command from the entry list.

        entry -- the entry

        Example: self.q.put([Action.remove_command, "download"])

    replace_command_list
        Introduced in API version 0.1.0.

        Replace the list of commands with the given list.

        list -- the new list of entries

        Example: self.q.put([Action.replace_command_list, ["download", "upload"]])

    set_header
        Introduced in API version 0.1.0.

        Set or replace the text currently in the header bar.

        If header is not given, the header will be removed.

        header -- the new header text

        Example: self.q.put([Action.set_header, "Weather for New York"])

    set_filter
        Introduced in API version 0.1.0.

        Replace the text currently in the search bar.

        filter -- the new text to put in the search bar

        Example: self.q.put([Action.set_header, "Weather for New York"])

    ask_question_default_yes
        Introduced in API version 0.1.0.

        Ask a yes/no question, with the default value being yes.

        question -- the question to ask
        identifier -- an optional identifier which gets passed back to process_response

        Example: self.q.put([Action.ask_question_default_yes, "Are you sure you want to continue?", 0])

    ask_question_default_no
        Introduced in API version 0.1.0.

        Ask a yes/no question, with the default value being no.

        question -- the question to ask
        identifier -- an optional identifier which gets passed back to process_response

        Example: self.q.put([Action.ask_question_default_no, "Are you sure you want to continue?", 0])

    ask_input
        Introduced in API version 0.1.0.

        Ask the user to input a single line of text.

        text -- the text to show the user
        identifier -- an optional identifier which gets passed back to process_response

        Example: self.q.put([Action.ask_input, "Please choose a new name for this entry", 0])

    ask_input_password:
        Introduced in API version 0.1.0.

        Ask the user to input a single line of text into a password field.

        text -- the text to show the user
        identifier -- an optional identifier which gets passed back to process_response

        Example: self.q.put([Action.ask_input_password, "Please enter your password", 0])

    ask_input_multi_line
        Introduced in API version 0.1.0.

        Ask the user to input one or more lines of text.

        text -- the text to show the user
        prefill -- the text to already put into the input field
        identifier -- an optional identifier which gets passed back to process_response

        The prefill may contain newline characters.

        Example: self.q.put([Action.ask_input_multi_line, "List your favourite animals", "Cat and dog", 0])

    copy_to_clipboard
        Introduced in API version 0.1.0.

        Copy data to the clipboard.

        text -- the text to copy to the clipboard

        Example: self.q.put([Action.copy_to_clipboard, "I like Pext"])

    set_selection
        Introduced in API version 0.1.0.

        Change the internal Pext selection for this module.

        The internal Pext selection contains a list of all options and commands
        the user chose and typed since the last time the window was closed and
        looks something like this:
        [{type: SelectionType.entry, value: "Audio settings"}, {type: SelectionType.command, value: "volume 50"}].

        To go a single level up, simply remove the last entry from this list.
        To reset to the main screen, use an empty list.

        After set_selection is called, selection_made in ModuleBase will be
        called with the new values.

        list -- the selection list

        Example: self.q.put([Action.set_selection, [{type: SelectionType.entry, value: "Audio settings"}])

    close:
        Introduced in API version 0.1.0.

        Close the window.

        Call this when the user is done. For example, when the user made a
        selection.

        Example: self.q.put([Action.close])
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
    close = 20


class SelectionType(Enum):
    """Introduced in API version 0.1.0.

    A list of possible selection types.

    entry
        Introduced in API version 0.1.0.

        An entry in the entry list was chosen.

    command
        Introduced in API version 0.1.0.

        A valid command was typed (valid commands start with an entry in the
        command list).
    """

    entry = 0
    command = 1
