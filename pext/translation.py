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

This is Pext's Translation class.
"""

from PyQt5.Qt import QQmlProperty


class Translation():
    """Retrieves translations for Python code.

    This works by reading values from QML.
    """

    __window = None

    @staticmethod
    def bind_window(window: 'Window') -> None:  # type: ignore # noqa: F821
        """Give the translator access to the translations stored in the window."""
        Translation.__window = window

    @staticmethod
    def get(string_id: str) -> str:
        """Return the translated value."""
        if Translation.__window:
            translation = QQmlProperty.read(Translation.__window.window, 'tr_{}'.format(string_id))
            if translation:
                return translation

            return "TRANSLATION MISSING: {}".format(string_id)

        return "TRANSLATION SYSTEM NOT YET AVAILABLE: {}".format(string_id)
