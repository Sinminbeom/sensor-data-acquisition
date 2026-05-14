import logging
import threading
import time
import unittest

import jsons

from core.const import AcqState
from drivers.Storage import Storage
from drivers.AP500CAN import AP500CAN
from interface import DriverError


class TestAP500CAN(unittest.TestCase):
    ACQ_DURATION = 20
    loop = False

    storage: Storage = None
    ap500can: AP500CAN = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

        # Prepare Storage driver
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
        drivers = {"storage": cls.storage}

        # Prepare AP500CAN driver
        config = {
            "name": "can",
            "driver": "AP500CAN",
            "local_ip": "10.0.0.2",
            "local_port": 8282,
            "remote_ip": "10.0.0.1",
            "remote_port": 8282,
            "use_fake_tcp_reader": True
        }
        cls.ap500can = jsons.load(config, AP500CAN)
        try:
            cls.ap500can.on_start([True], drivers)
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.ap500can.on_stop()
        cls.storage.on_stop()

    def test_snapshot(self):
        threading.Timer(self.ACQ_DURATION, self.__stop_loop).start()
        self.loop = True
        while self.loop:
            time.sleep(1)
            content_type, status = self.ap500can.snapshot()
            self.assertEqual(content_type, 'application/json', status.decode('utf-8'))
            print(status)

    def __stop_loop(self):
        self.loop = False

    def test_acquisition(self):
        # Test start_acquisition
        self.assertEqual(self.ap500can.start_acquisition()[0], AcqState.ACQUIRING)

        # Test check_acquisition after start_acquisition
        self.assertEqual(self.ap500can.check_acquisition()[0], AcqState.ACQUIRING)
        threading.Timer(self.ACQ_DURATION, self.__test_stop_acquisition).start()

        self.loop = True
        while self.loop:
            time.sleep(0.1)

        # Test check_acquisition after stop_acquisition
        self.assertEqual(self.ap500can.check_acquisition()[0], AcqState.NOT_ACQUIRING)

    def __test_stop_acquisition(self):
        # Test stop_acquisition
        self.assertEqual(self.ap500can.stop_acquisition()[0], AcqState.NOT_ACQUIRING)
        self.loop = False


if __name__ == '__main__':
    unittest.main()
