import os
import datetime
import unittest

from pext.__main__ import ConfigRetriever

# Directory holding test data
test_data = os.path.join(os.path.dirname(__file__), 'testdata')


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.test_config = os.path.join(test_data, "config")
        self.config_retriever = ConfigRetriever(self.test_config)

    def test_get_setting(self):
        self.assertEqual(self.config_retriever.get_setting('config_path'),
                         self.test_config)

    def test_get_updatecheck_permission_asked(self):
        self.assertTrue(self.config_retriever.get_updatecheck_permission_asked())

    def test_get_updatecheck_permission(self):
        self.assertTrue(self.config_retriever.get_updatecheck_permission())

    def test_get_last_update_check_time(self):
        self.assertEqual(self.config_retriever.get_last_update_check_time(),
                         datetime.datetime(2018, 3, 25, 15, 29, 55))


if __name__ == '__main__':
    unittest.main()
