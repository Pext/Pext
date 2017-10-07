#!/usr/bin/env python3

# Copyright (c) 2017 Sylvia van Os <sylvia@hackerchick.me>
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

"""Pext wrapper.

This is the Pext wrapper file. It will run Pext and restart it whenever it
exits with error code 129 (129 is hardcoded to mean a restart request).
"""

import os
import subprocess
import sys


def main() -> None:
    """Launch Pext and ensure it restarts if it returns error code 257."""
    while True:
        command = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pext.py")] + sys.argv[1:]
        return_code = subprocess.Popen(command).wait()
        if return_code != 129:
            sys.exit(return_code)
        print("Restarting...")


if __name__ == "__main__":
    main()
