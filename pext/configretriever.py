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

This is Pext's ConfigRetriever class.
"""

import os
import tempfile

try:
    from typing import Optional
except ImportError:
    from backports.typing import Optional  # type: ignore  # noqa: F401

from pext.appfile import AppFile


class ConfigRetriever():
    """Retrieve global configuration entries."""

    __config_data_path = None
    __config_temp_path = None

    @staticmethod
    def set_data_path(path: Optional[str]) -> None:
        """Set the root configuration directory for Pext to store in and load from."""
        ConfigRetriever.__config_data_path = path

    @staticmethod
    def make_portable(portable: Optional[bool]) -> None:
        """Make changes to locations so that Pext can be considered portable."""
        if not portable:
            return

        if not ConfigRetriever.__config_data_path:
            if 'APPIMAGE' in os.environ:
                base_path = os.path.dirname(os.path.abspath(os.environ['APPIMAGE']))
            else:
                base_path = AppFile.get_path()
            ConfigRetriever.__config_data_path = os.path.join(base_path, 'pext_data')

        ConfigRetriever.__config_temp_path = os.path.join(ConfigRetriever.__config_data_path, 'pext_temp')

    @staticmethod
    def get_path() -> str:
        """Get the config path."""
        if ConfigRetriever.__config_data_path:
            config_data_path = os.path.expanduser(ConfigRetriever.__config_data_path)
            os.makedirs(config_data_path, exist_ok=True)
            return config_data_path

        # Fall back to default config location
        try:
            config_data_path = os.environ['XDG_CONFIG_HOME']
        except Exception:
            config_data_path = os.path.join(os.path.expanduser('~'), '.config')

        os.makedirs(config_data_path, exist_ok=True)
        return os.path.join(config_data_path, 'pext')

    @staticmethod
    def get_temp_path() -> str:
        """Get the temp path."""
        if ConfigRetriever.__config_temp_path:
            temp_path = os.path.expanduser(ConfigRetriever.__config_temp_path)
        else:
            temp_path = tempfile.gettempdir()

        os.makedirs(temp_path, exist_ok=True)
        return temp_path
