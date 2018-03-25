import os
import datetime
import shutil
import tempfile
import unittest

from pext.__main__ import ConfigRetriever

test_src = os.path.dirname(__file__)

# Copy test data to temporary directory
temp_dir = tempfile.mkdtemp()
test_data = shutil.copytree(os.path.join(test_src, 'testdata'),
                            os.path.join(temp_dir, 'testdata'))


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
        date = datetime.datetime(2018, 3, 25, 13, 29, 55, tzinfo=datetime.timezone.utc)
        utc_offset = date.astimezone().utcoffset()

        # Remove tzinfo attribute
        date = date.replace(tzinfo=None)

        # Convert to local time
        date += utc_offset

        self.assertEqual(self.config_retriever.get_last_update_check_time(), date)


if __name__ == '__main__':
    unittest.main()
