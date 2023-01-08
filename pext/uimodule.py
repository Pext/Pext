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

This is Pext's UiModule class.
"""

from pext.viewmodel import ViewModel


class UiModule():
    """The module and all the relevant data to make UI display possible."""

    def __init__(self, vm: ViewModel, module_code, module_import, metadata, settings) -> None:
        """Put together the module and relevant classes and data."""
        self.init = False
        self.vm = vm
        self.module_code = module_code
        self.module_import = module_import
        self.metadata = metadata
        self.settings = settings

        self.entries_processed = 0
