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

This is Pext's Enums file, it contains common Enum definitions used in
multiple places.
"""

from enum import IntEnum


class UIType(IntEnum):
    """A list of supported UI types."""

    Qt5 = 0


class MinimizeMode(IntEnum):
    """A list of possible ways Pext can react on minimization."""

    Normal = 0
    Tray = 1
    NormalManualOnly = 2
    TrayManualOnly = 3


class SortMode(IntEnum):
    """A list of possible ways Pext can sort module entries."""

    Module = 0
    Ascending = 1
    Descending = 2


class OutputMode(IntEnum):
    """A list of possible locations to output to."""

    DefaultClipboard = 0
    SelectionClipboard = 1
    FindBuffer = 2
    AutoType = 3


class OutputSeparator(IntEnum):
    """A list of possible separators to put between entries in the output queue."""

    None_ = 0
    Tab = 1
    Enter = 2
