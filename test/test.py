import os
import shutil
import tempfile
import unittest

from PyQt5.QtWidgets import QApplication
from pext.__main__ import ConfigRetriever, LocaleManager

test_src = os.path.dirname(__file__)


class TestConfig(unittest.TestCase):
    def setUp(self):
        # Copy test data to a temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        test_data = shutil.copytree(os.path.join(test_src, 'testdata'),
                                    os.path.join(self.temp_dir.name, 'testdata'))

        self.test_config = os.path.join(test_data, "config")
        ConfigRetriever.set_data_path(self.test_config)

    def tearDown(self):
        # Delete the temporary directory
        self.temp_dir.cleanup()

    def test_get_setting(self):
        self.assertEqual(ConfigRetriever.get_path(),
                         self.test_config)


class TestLocaleManager(unittest.TestCase):
    def setUp(self):
        # Create QApplication without creating a GUI
        self.app = QApplication.__new__(QApplication)

        # Replace method with dummy function, so we can run tests without
        # properly initializing the class
        self.app.installTranslator = lambda translationFile: None

        self.locale_manager = LocaleManager()

    def test_get_locales(self):
        locales = self.locale_manager.get_locales()
        self.assertIn('American English', locales)
        self.assertIn('Nederlands', locales)

        # hu language no longer available
        # self.assertEqual(locales['magyar'], 'hu')

    def test_get_current_locale(self):
        # Load English locale
        locale = self.locale_manager.find_best_locale('en')
        self.locale_manager.load_locale(self.app, locale)

        self.assertEqual(self.locale_manager.get_current_locale(), locale)


if __name__ == '__main__':
    unittest.main()
