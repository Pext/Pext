#!/usr/bin/env python3

# Copyright (c) 2015 - 2023 Sylvia van Os <sylvia@hackerchick.me>
#
# This file is part of Pext.
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

"""Pext.

This is Pext's ViewModel class.
"""

import os
import sys
import threading

from queue import Queue, Empty
try:
    from typing import Any, Callable, Dict, List, Optional
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional  # type: ignore  # noqa: F401

from pext.appfile import AppFile
from pext.enums import SortMode
from pext.settings import Logger, Settings
from pext.translation import Translation
# Ensure pext_base and pext_helpers can always be loaded by us and the modules
sys.path.append(os.path.join(AppFile.get_path(), 'helpers'))
sys.path.append(os.path.join(AppFile.get_path()))

from pext_base import ModuleBase  # noqa: E402
from pext_helpers import Action, Selection, SelectionType  # noqa: E402


class ViewModel():
    """Manage the communication between user interface and module."""

    def __init__(self, view_settings) -> None:
        """Initialize ViewModel."""
        # Temporary values to allow binding. These will be properly set when
        # possible and relevant.
        self._settings = {}  # type: Dict[str, Any]
        self.entry_list = []  # type: List
        self.filtered_entry_list = []  # type: List
        self.command_list = []  # type: List
        self.filtered_command_list = []  # type: List
        self.result_list = []  # type: List
        self.result_list_index = -1
        self.result_list_model_max_index = -1
        self.selection = []  # type: List[Selection]
        self.search_string = ""
        self.last_search = ""
        self.context_menu_enabled = False
        self.context_menu_index = -1
        self.context_menu_list = []  # type: List
        self.context_menu_base_list = []  # type: List
        self.context_menu_list_full = []  # type: List
        self.extra_info_entries = {}  # type: Dict[str, str]
        self.extra_info_commands = {}  # type: Dict[str, str]
        self.context_menu_entries = {}  # type: Dict[str, List[str]]
        self.context_menu_commands = {}  # type: Dict[str, List[str]]
        self.context_menu_base = []  # type: List[str]
        self.selection_thread = None  # type: Optional[threading.Thread]
        self.minimize_disabled = False

        self.settings = view_settings

        self.stopped = False

        # Callback functions
        self.search_string_changed = lambda search_string: None  # type: Callable[[str], None]
        self.result_list_changed = lambda results, normal_count, entry_count, unfiltered_entry_count: None \
            # type: Callable[[List[str], int, int, int], None]
        self.result_list_index_changed = lambda index: None  # type: Callable[[int], None]
        self.context_menu_enabled_changed = lambda value: None  # type: Callable[[bool], None]
        self.context_menu_index_changed = lambda index: None  # type: Callable[[int], None]
        self.context_menu_list_changed = lambda base, entry_specific: None \
            # type: Callable[[List[str], List[str]], None]
        self.context_info_panel_changed = lambda value: None  # type: Callable[[str], None]
        self.sort_mode_changed = lambda mode: None  # type: Callable[[str], None]
        self.unprocessed_count_changed = lambda count: None  # type: Callable[[int], None]
        self.selection_changed = lambda selection: None  # type: Callable[[List[Selection]], None]
        self.header_text_changed = lambda value: None  # type: Callable[[str], None]

        self.ask_argument = lambda entry, callback: None  # type: Callable[[str, Callable], None]
        self.close_request = lambda manual, force_tray: None  # type: Callable[[bool, bool], None]

    @property
    def settings(self):
        """Return all ViewModel settings."""
        return self._settings

    @settings.setter
    def settings(self, settings):
        """Overwrite ViewModel settings."""
        self._settings = settings

    @property
    def sort_mode(self):
        """Retrieve the current sorting mode as printable name."""
        for data in SortMode:
            if data == self._settings['__pext_sort_mode']:
                return data.name

        # Maybe mode doesn't exist (anymore)
        # Return first value
        for data in SortMode:
            self.sort_mode = data
            return data.name

    @sort_mode.setter
    def sort_mode(self, sort_mode: SortMode):
        """Set the new sorting mode."""
        self._settings['__pext_sort_mode'] = sort_mode
        self.sort_mode_changed(self.sort_mode)

        # Force a resort
        self.search(new_entries=True)

    def stop(self) -> None:
        """Stop the module."""
        self.stopped = True
        self.module.stop()

    def next_sort_mode(self):
        """Calculate and set the next sorting mode available."""
        want_next = False
        for data in SortMode:
            if want_next:
                self.sort_mode = data
                return

            if data == self._settings['__pext_sort_mode']:
                want_next = True

        # End of list reached
        for data in SortMode:
            self.sort_mode = data
            return

    def make_selection(self, disable_minimize=False) -> None:
        """Make a selection if no selection is currently being processed.

        Running the selection making in another thread prevents it from locking
        up Pext's UI, while ensuring existing thread completion prevents race
        conditions.
        """
        if self.stopped:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        self.minimize_disabled = disable_minimize
        self.selection_thread = threading.Thread(target=self.module.selection_made, args=(self.selection,))
        self.selection_thread.start()

    def _get_longest_common_string(self, entries: List[str], start="") -> Optional[str]:
        """Return the longest common string.

        Returns the longest common string for each entry in the list, starting
        at the start.

        Keyword arguments:
        entries -- the list of entries
        start -- the string to start with (default "")

        All entries not starting with start are discarded before additional
        matches are looked for.

        Returns the longest common string, or None if not a single value
        matches start.
        """
        # Filter out all entries that don't match at the start
        entry_list = []
        for entry in entries:
            if entry.startswith(start):
                entry_list.append(entry)

        common_chars = list(start)

        try:
            while True:
                common_char = None
                for entry in entry_list:
                    if common_char is None:
                        common_char = entry[len(common_chars)]
                    elif common_char != entry[len(common_chars)]:
                        return ''.join(common_chars)

                if common_char is None:
                    return None

                common_chars.append(common_char)
        except IndexError:
            # We fully match a string
            return ''.join(common_chars)

    def clear_queue(self) -> None:
        """Clear all enqueued actions."""
        while True:
            try:
                self.queue.get_nowait()
            except Empty:
                return
            self.queue.task_done()

    def bind_search_string_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the search_string_changed callback.

        This ensures we can notify the window when the search string changes.
        """
        self.search_string_changed = function

    def bind_result_list_changed_callback(self, function: Callable[[List[str], int, int, int], None]) -> None:
        """Bind the result_list_changed callback.

        This ensures we can notify the window when the result list changes.
        """
        self.result_list_changed = function

    def bind_result_list_index_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the result_list_index_changed callback.

        This ensures we can notify the window when the result list index changes.
        """
        self.result_list_index_changed = function

    def bind_context_menu_enabled_changed_callback(self, function: Callable[[bool], None]) -> None:
        """Bind the context_menu_enabled_changed callback.

        This ensures we can notify the window when the state of the context menu changes.
        """
        self.context_menu_enabled_changed = function

    def bind_context_menu_index_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the context_menu_index_changed callback.

        This ensures we can notify the window when the context menu index changes.
        """
        self.context_menu_index_changed = function

    def bind_context_menu_list_changed_callback(self, function: Callable[[List[str], List[str]], None]) -> None:
        """Bind the context_menu_list_changed callback.

        This ensures we can notify the window when the context menu's list changes.
        """
        self.context_menu_list_changed = function

    def bind_context_info_panel_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the context_info_panel_changed callback.

        This ensures we can notify the window when the context info menu changes.
        """
        self.context_info_panel_changed = function

    def bind_base_info_panel_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the base_info_panel_changed callback.

        This ensures we can notify the window when the base info menu changes.
        """
        self.base_info_panel_changed = function

    def bind_sort_mode_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the sort_mode_changed callback.

        This ensures we can notify the window when the sort mode changes.
        """
        self.sort_mode_changed = function

    def bind_unprocessed_count_changed_callback(self, function: Callable[[int], None]) -> None:
        """Bind the unprocessed_count_changed callback.

        This ensures we can notify the window when the unprocessed count changes.
        """
        self.unprocessed_count_changed = function

    def bind_selection_changed_callback(self, function: Callable[[List[Selection]], None]) -> None:
        """Bind the selection_changed callback.

        This ensures we can notify the window when the selection changes.
        """
        self.selection_changed = function

    def bind_header_text_changed_callback(self, function: Callable[[str], None]) -> None:
        """Bind the header_text_changed callback.

        This ensures we can notify the window when the header text changes.
        """
        self.header_text_changed = function

    def bind_ask_argument_callback(self, function: Callable[[str, Callable], None]) -> None:
        """Bind the ask_argument callback.

        This ensures we can notify the window when an argument is requested.
        """
        self.ask_argument = function

    def bind_close_request_callback(self, function: Callable[[bool, bool], None]) -> None:
        """Bind the close_request callback.

        This ensures we can notify the window when a window closure is requested.
        """
        self.close_request = function

    def bind_queue(self, queue: Queue) -> None:
        """Bind the queue."""
        self.queue = queue

    def bind_module(self, module: ModuleBase) -> None:
        """Bind the module.

        This ensures we can call functions in it.
        """
        self.module = module

    def update_result_list_index(self, index: int) -> None:
        """Update the result list index."""
        self.result_list_index = index

    def update_context_menu_index(self, index: int) -> None:
        """Update the context menu index."""
        self.context_menu_index = index

    def go_up(self, to_base=False) -> None:
        """Go one level up.

        This means that, if we're currently in the entry content list, we go
        back to the entry list. If we're currently in the entry list, we clear
        the search bar. If we're currently in the entry list and the search bar
        is empty, we tell the window to hide/close itself.
        """
        if self.context_menu_enabled:
            self.hide_context()
            if not to_base:
                return

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
            if not to_base:
                return

        if self.stopped:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        if len(self.selection) > 0:
            if not to_base:
                self.selection.pop()
            else:
                self.selection = []

            self.entry_list = []
            self.command_list = []

            self.search(new_entries=True)

            self.selection_changed(self.selection)

            self.clear_queue()

            self.make_selection()
        else:
            self.close_request(True, False)

    def search(self, new_entries=False, manual=False) -> None:
        """Filter the entry list.

        Filter the list of entries in the screen, setting the filtered list
        to the entries containing one or more words of the string currently
        visible in the search bar.
        """
        if self.stopped:
            return

        # Don't search if nothing changed
        if not new_entries and self.search_string == self.last_search:
            return

        # Notify window the search string changed
        self.search_string_changed(self.search_string)

        # Enable checking for changes next time
        self.last_search = self.search_string

        current_match = None
        current_index = 0

        # If context menu is open, search in context menu
        if self.context_menu_enabled:
            current_entry = self._get_entry()
            try:
                if current_entry['type'] == SelectionType.entry:
                    entry_list = [entry for entry in self.context_menu_entries[current_entry['value']]]
                else:
                    entry_list = [entry for entry in self.context_menu_commands[current_entry['value']]]
            except KeyError:
                entry_list = []

            if current_entry['type'] == SelectionType.command:
                entry_list.insert(0, Translation.get("enter_arguments"))

            # Sort if sorting is enabled
            if self.settings['__pext_sort_mode'] != SortMode.Module:
                reverse = self.settings['__pext_sort_mode'] == SortMode.Descending
                self.sorted_context_list = sorted(entry_list, reverse=reverse)
                self.sorted_context_base_list = sorted(self.context_menu_base, reverse=reverse)
            else:
                self.sorted_context_list = entry_list
                self.sorted_context_base_list = self.context_menu_base

            # Get current match
            try:
                current_match = self.context_menu_list_full[self.context_menu_index]
            except IndexError:
                pass
        # Else, search in normal list
        else:
            # Sort if sorting is enabled
            if self.settings['__pext_sort_mode'] != SortMode.Module:
                reverse = self.settings['__pext_sort_mode'] == SortMode.Descending
                self.sorted_entry_list = sorted(self.entry_list, reverse=reverse)
                self.sorted_command_list = sorted(self.command_list, reverse=reverse)
                self.sorted_filtered_entry_list = sorted(self.filtered_entry_list, reverse=reverse)
                self.sorted_filtered_command_list = sorted(self.filtered_command_list, reverse=reverse)
            else:
                self.sorted_entry_list = self.entry_list
                self.sorted_command_list = self.command_list
                self.sorted_filtered_entry_list = self.filtered_entry_list
                self.sorted_filtered_command_list = self.filtered_command_list

            # Get current match
            try:
                current_match = self.result_list[self.result_list_index]
            except IndexError:
                pass

        # If empty, show all
        if not self.search_string and not new_entries:
            if self.context_menu_enabled:
                self.filtered_context_list = entry_list
                self.filtered_context_base_list = self.context_menu_base
                self.sorted_filtered_context_list = self.sorted_context_list
                self.sorted_filtered_context_base_list = self.sorted_context_base_list

                self.context_menu_list_changed(
                    self.sorted_filtered_context_base_list,
                    self.sorted_filtered_context_list)
            else:
                self.filtered_entry_list = self.entry_list
                self.filtered_command_list = self.command_list
                self.sorted_filtered_entry_list = self.sorted_entry_list
                self.sorted_filtered_command_list = self.sorted_command_list

                combined_list = self.sorted_filtered_entry_list + self.sorted_filtered_command_list

                self.result_list = combined_list
                self.result_list_changed(
                    self.result_list,
                    len(self.sorted_filtered_entry_list),
                    len(self.sorted_filtered_command_list),
                    len(self.entry_list) + len(self.command_list))

            # Keep existing selection, otherwise ensure something is selected
            if current_match:
                try:
                    current_index = combined_list.index(current_match)
                except ValueError:
                    current_index = 0

            if self.context_menu_enabled:
                self.context_menu_index = current_index
                self.context_menu_index_changed(self.context_menu_index)
            else:
                self.result_list_index = current_index
                self.result_list_index_changed(self.result_list_index)

            self.update_context_info_panel()

            return

        if self.context_menu_enabled:
            self.filtered_context_list = []
            self.filtered_context_base_list = []
        else:
            self.filtered_entry_list = []
            self.filtered_command_list = []

        # String matching logic
        list_match = self.search_string.lower().split(' ')

        def check_list_match(entries, string_list) -> List[str]:
            return_list = []  # type: List[str]
            for entry in entries:
                lower_entry = str(entry).lower()
                for self.search_string_part in string_list:
                    if self.search_string_part not in lower_entry:
                        break
                else:
                    # If exact match, put on top
                    if len(string_list) == 1 and string_list[0] == lower_entry:
                        return_list.insert(0, entry)
                    # otherwise, put on bottom
                    else:
                        return_list.append(entry)

            return return_list

        if self.context_menu_enabled:
            self.filtered_context_list = check_list_match(self.sorted_context_list, list_match)
            self.filtered_context_base_list = check_list_match(self.sorted_context_base_list, list_match)
        else:
            self.filtered_entry_list = check_list_match(self.sorted_entry_list, list_match)
            self.filtered_command_list = check_list_match(self.sorted_command_list, list_match)

        if self.context_menu_enabled:
            self.context_menu_list_changed(self.filtered_context_base_list, self.filtered_context_list)
            combined_list = self.filtered_context_list + self.filtered_context_base_list
        else:
            combined_list = self.filtered_entry_list + self.filtered_command_list
            self.result_list = combined_list
            self.result_list_changed(
                self.result_list,
                len(self.filtered_entry_list),
                len(self.filtered_command_list),
                len(self.entry_list) + len(self.command_list))

        # See if we have an exact match
        if combined_list and len(list_match) == 1 and str(combined_list[0]).lower() == list_match[0]:
            current_index = 0
        # Otherwise, keep existing selection
        elif current_match:
            try:
                current_index = combined_list.index(current_match)
            # As fallback, ensure something is selected
            except ValueError:
                current_index = 0

        if self.context_menu_enabled:
            self.context_menu_index = current_index
            self.context_menu_index_changed(self.context_menu_index)
        else:
            self.result_list_index = current_index
            self.result_list_index_changed(self.result_list_index)

        self.update_context_info_panel()

        # Turbo mode: Select entry if only entry left
        if Settings.get('turbo_mode') and len(combined_list) == 1 and self.queue.empty() and self.search_string:
            self.select(force_args=True)

    def _get_entry(self, include_context=False) -> Selection:
        """Get info on the entry that's currently focused."""
        if include_context and self.context_menu_enabled:
            current_index = self.context_menu_index

            selected_entry = self._get_entry()

            # Return entry-specific option if selected, otherwise base option
            if current_index >= len(self.filtered_context_list):
                # Selection is a base entry
                return Selection(
                    type=SelectionType.none,
                    value=None,
                    context_option=self.filtered_context_base_list[current_index - len(self.filtered_context_list)]
                )
            else:
                selected_entry.context_option = self.filtered_context_list[current_index]

            return selected_entry

        current_index = self.result_list_index

        if current_index >= len(self.filtered_entry_list):
            # Selection is a command
            selection_type = SelectionType.command
            entry = self.filtered_command_list[current_index - len(self.filtered_entry_list)]
        else:
            selection_type = SelectionType.entry
            entry = self.filtered_entry_list[current_index]

        return Selection(type=selection_type, value=entry, context_option=None)

    def select(self, command_args="", force_args=False, disable_minimize=False) -> None:
        """Notify the module of our selection entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            return

        if self.selection_thread and self.selection_thread.is_alive():
            return

        selection = self._get_entry(include_context=True)
        if selection.type == SelectionType.command:
            if not command_args and (force_args or selection.context_option == Translation.get("enter_arguments")):
                self.input_args()
                return

        if selection.context_option == Translation.get("enter_arguments"):
            selection.context_option = None

        selection.args = command_args
        self.selection.append(selection)

        self.context_menu_enabled = False
        self.context_menu_enabled_changed(self.context_menu_enabled)
        self.selection_changed(self.selection)

        self.entry_list = []
        self.command_list = []
        self.extra_info_entries = {}
        self.extra_info_commands = {}
        self.context_menu_entries = {}
        self.context_menu_commands = {}

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search(new_entries=True, manual=True)
        self.clear_queue()

        self.make_selection(disable_minimize=disable_minimize)

    def show_context(self) -> None:
        """Show the context menu of the selected entry."""
        if self.stopped:
            return

        if not self.filtered_command_list and not self.filtered_entry_list:
            return

        current_entry = self._get_entry()

        entries = 0

        # Get all menu-specific entries
        try:
            if current_entry['type'] == SelectionType.entry:
                entries += len(self.context_menu_entries[current_entry['value']])
            else:
                entries += len(self.context_menu_commands[current_entry['value']])
        except KeyError:
            pass

        if not entries and not self.context_menu_base:
            if current_entry['type'] == SelectionType.command:
                self.input_args()
                return

            Logger.log(None, Translation.get("no_context_menu_available"))
            return

        self.context_menu_enabled = True
        self.context_menu_enabled_changed(self.context_menu_enabled)
        self.context_menu_index_changed(0)

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search(new_entries=True)

    def hide_context(self) -> None:
        """Hide the context menu."""
        if self.stopped:
            return

        self.context_menu_enabled = False
        self.context_menu_enabled_changed(self.context_menu_enabled)

        if self.search_string != "":
            self.search_string = ""
            self.search_string_changed(self.search_string)
        self.search()

    def update_context_info_panel(self, request_update=True) -> None:
        """Update the context info panel with the info panel data of the currently selected entry."""
        if self.stopped:
            return

        if not self.filtered_entry_list and not self.filtered_command_list:
            self.context_info_panel_changed("")
            return

        current_entry = self._get_entry()

        if request_update:
            info_selection = self.selection[:]
            new_selection_entry = current_entry
            info_selection.append(new_selection_entry)

            threading.Thread(target=self.module.extra_info_request, args=(info_selection,)).start()

        try:
            if current_entry.value is not None:
                if current_entry.type == SelectionType.entry:
                    self.context_info_panel_changed(self.extra_info_entries[current_entry.value])
                else:
                    self.context_info_panel_changed(self.extra_info_commands[current_entry.value])
        except KeyError:
            self.context_info_panel_changed("")

    def update_base_info_panel(self, base_info: str) -> None:
        """Update the base info panel based on the current module state."""
        self.base_info_panel_changed(str(base_info))

    def set_header(self, content) -> None:
        """Set the header text."""
        self.header_text_changed(str(content))

    def tab_complete(self) -> None:
        """Tab-complete based on the current seach input.

        This tab-completes the command, entry or combination currently in the
        search bar to the longest possible common completion.
        """
        if self.stopped:
            return

        current_input = self.search_string
        combined_list = self.filtered_entry_list + self.filtered_command_list

        entry = self._get_longest_common_string(
                [entry.lower() for entry in combined_list],
                start=current_input.lower())
        if entry is None or len(entry) <= len(current_input):
            self.queue.put(
                [Action.add_error, Translation.get("no_tab_completion_possible")])
            return

        self.search_string = entry
        self.search_string_changed(entry)
        self.search()

    def input_args(self) -> None:
        """Open dialog that allows the user to input command arguments."""
        if self.stopped:
            return

        if not self.filtered_command_list and not self.filtered_entry_list:
            self.queue.put(
                [Action.add_error, Translation.get("no_entry_selected")])
            return

        selected_entry = self._get_entry(include_context=True)
        if not self.context_menu_enabled and selected_entry["type"] != SelectionType.command:
            if len(self.filtered_command_list) > 0:
                # Jump to the first command in case the current selection
                # is not a command
                self.result_list_index = len(self.filtered_entry_list)
                self.result_list_index_changed(self.result_list_index)
                selected_entry = self._get_entry(include_context=True)
            else:
                self.queue.put(
                    [Action.add_error, Translation.get("no_command_available_for_current_filter")])
                return

        self.ask_argument(selected_entry["value"], self.select)
