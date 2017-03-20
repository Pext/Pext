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

"""Pext Module Base.

This file contains the definition of the Pext module base, which all
Pext modules must implement. This is basically the API of Pext.
"""

from abc import ABC, abstractmethod  # type: ignore
from queue import Queue
from typing import Dict, List, Union

from pext_helpers import SelectionType


class ModuleBase(ABC):
    """The base all Pext modules must implement."""

    @abstractmethod
    def init(self, settings: Dict, q: Queue) -> None:
        """Called when the module is first loaded.

        In this function, the application should initialize all its data and
        use the Action.add_entry and Action.add_command to asynchronously
        populate the main list.

        If the list can be generated very quickly, the module may opt for using
        Action.replace_entry_list and Action.replace_command_list instead, although
        it is recommended to queue the data per entry so that the user can
        start interacting with at least some of the data as quickly as
        possible.

        The settings variable is a dictionary containing all "module settings".
        For example, if the user enters "foo=bar foobar=fubar" in the custom
        module settings dialog, this dictionary will have
        {"foo": "bar", "foobar": "fubar"} as values.

        The q variable contains the queue that actions can be put it. It is
        very important to keep a reference to this variable so that you can do
        anything on the UI at all.
        """
        pass

    @abstractmethod
    def stop(self):
        """Called when the module gets unloaded.

        If necessary, the module should clean itself up nicely.
        """
        pass

    @abstractmethod
    def selection_made(self, selection: List[Dict[SelectionType, str]]) -> None:
        """Called when the user makes a selection.

        The selection variable contains a list of the selection tree and the
        type, which can be either entry or command.

        For example, if the user chooses the entry "Audio settings" in the main
        screen, the value of selection is
        [{type: SelectionType.entry, value: "Audio settings"}]. If the user
        then runs the command "volume 50", this function is called again, with
        the value of selection being
        [{type: SelectionType.entry, value: "Audio settings"},
         {type: SelectionType.command, value: "volume 50"}].
        """
        pass

    @abstractmethod
    def process_response(self, response: Union[bool, str]):
        """Process a response to a requested action.

        Called when a response is given as a result of an Action being put into
        the queue. Not all Actions return a response.
        """
        pass
