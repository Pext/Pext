#!/usr/bin/env python3

# Copyright (c) <year> <Your name> <Your email>
#
# This program is free software: you can redistribute it and/or modify
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

from pext_base import ModuleBase
from pext_helpers import Action, SelectionType


class Module(ModuleBase):
    def init(self, settings, q):
        pass

    def stop(self):
        pass

    def selection_made(self, selection):
        pass

    def process_response(self, response, identifier):
        pass
