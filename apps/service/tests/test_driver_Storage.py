import logging
import unittest

import jsons

from core.const import ConnState
from drivers.Storage import Storage
from interface import DriverError


# noinspection DuplicatedCode
class TestStorage(unittest.TestCase):
    storage: Storage = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

        config = {
            "name": "storage",
            "driver": "Storage",
            "mount_point": "/storage",
            "minimum_free_space_byte": 1073741824,
        }
        cls.storage = jsons.load(config, Storage)
        try:
            cls.storage.on_start([True], {})
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.storage.on_stop()

    def test_check_connection(self):
        self.assertEqual(self.storage.check_connection(), ConnState.CONNECTED)

    def test_snapshot(self):
        content_type, status = self.storage.snapshot()
        self.assertEqual(content_type, 'application/json', status.decode('utf-8'))
        print(status)

    def test_recommend_storage(self):
        try:
            path = self.storage.recommend_storage('')
            self.assertTrue(path)
            print(path)
        except DriverError as e:
            self.fail(e)


if __name__ == '__main__':
    unittest.main()
