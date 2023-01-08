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

This is Pext's LocaleManager class.
"""

import os

try:
    from typing import Dict, Optional
except ImportError:
    from backports.typing import Dict, Optional  # type: ignore  # noqa: F401

from PyQt5.Qt import QApplication, QLocale, QTranslator

from pext.appfile import AppFile


class LocaleManager():
    """Load and switch locales."""

    def __init__(self) -> None:
        """Initialize the locale manager."""
        self.locale_dir = os.path.join(AppFile.get_path(), 'i18n')
        self.current_locale = None
        self.translator = QTranslator()  # prevent Python from garbage collecting it after load_locale function

    @staticmethod
    def get_locales() -> Dict[str, str]:
        """Return the list of supported locales.

        It is return as a dictionary formatted as follows: {nativeLanguageName: languageCode}.
        """
        locales = {}

        try:
            for locale_file in os.listdir(os.path.join(AppFile.get_path(), 'i18n')):
                if not locale_file.endswith('.qm'):
                    continue

                locale_code = os.path.splitext(locale_file)[0][len('pext_'):]
                locale_name = QLocale(locale_code).nativeLanguageName()
                locales[locale_name] = locale_code
        except FileNotFoundError:
            print("No translations found")

        return locales

    def get_current_locale(self, system_if_unset=True) -> Optional[QLocale]:
        """Get the current locale.

        If no locale is explicitly set, it will return the current system locale, unless system_if_unset is set to
        False, in which case it will return None.
        """
        if self.current_locale:
            return self.current_locale

        if system_if_unset:
            return QLocale()

        return None

    @staticmethod
    def find_best_locale(locale=None) -> QLocale:
        """Find the best locale to use, defaulting to system locale."""
        return QLocale(locale) if locale else QLocale()

    def load_locale(self, app: QApplication, locale: QLocale) -> None:
        """Load the given locale into the application."""
        system_locale = QLocale()

        if locale != system_locale:
            self.current_locale = locale

        print('Using locale: {} {}'
              .format(locale.name(), "(system locale)" if locale == system_locale else ""))
        print('Localization loaded:',
              self.translator.load(locale, 'pext', '_', self.locale_dir, '.qm'))

        app.installTranslator(self.translator)
