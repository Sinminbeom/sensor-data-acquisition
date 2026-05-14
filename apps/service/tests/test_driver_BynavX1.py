import logging
import threading
import time
import unittest

import jsons

from core.const import ConnState, HealthStatus, AcqState
from drivers.BynavX1 import BynavX1
from drivers.Storage import Storage
from interface import DriverError


# noinspection DuplicatedCode
class TestBynavX1(unittest.TestCase):
    ACQ_DURATION = 10
    loop = False

    storage: Storage = None
    bynav: BynavX1 = None

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

        # Prepare BynavX1 driver
        config = {
            "name": "imu",
            "driver": "BynavX1",
            "src_ip": "192.168.20.50",
            "protocol": "tcp",
            "dst_port": 1111,

            "ping_count": 1,
            "ping_timeout": 0.3,
            "packet_loss_threshold": 0.2,

            "use_fake_tcp_reader": True,

            "ntrip": {
                "from": {
                    "ip": "115.84.164.202",
                    "port": 2101,
                    "mount_point": "YONS-RTCM32-M5",
                    "user": "seoul",
                    "password": "seoul",
                    "timeout_s": 5,
                },
                "to": {
                    "ip": "192.168.20.50",
                    "port": 2222,
                }
            }
        }
        cls.bynav = jsons.load(config, BynavX1)
        try:
            cls.bynav.on_start([True], drivers)
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.bynav.on_stop()
        cls.storage.on_stop()

    def test_check_connection(self):
        self.assertEqual(self.bynav.check_connection(), ConnState.CONNECTED)

    def test_snapshot(self):
        content_type, location = self.bynav.snapshot()
        self.assertEqual(content_type, 'application/json')
        print(location)

    def test_acquisition(self):
        # Test start_acquisition
        self.assertEqual(self.bynav.start_acquisition()[0], AcqState.ACQUIRING)

        # Test check_acquisition after start_acquisition
        self.assertEqual(self.bynav.check_acquisition()[0], AcqState.ACQUIRING)
        threading.Timer(self.ACQ_DURATION, self.__test_stop_acquisition).start()

        self.loop = True
        while self.loop:
            time.sleep(0.1)

        # Test check_acquisition after stop_acquisition
        self.assertEqual(self.bynav.check_acquisition()[0], AcqState.NOT_ACQUIRING)

    def __test_stop_acquisition(self):
        # Test stop_acquisition
        self.assertEqual(self.bynav.stop_acquisition()[0], AcqState.NOT_ACQUIRING)
        self.loop = False

    def test_check_health(self):
        self.assertEqual(self.bynav.check_health(), (HealthStatus.GOOD, ''))


if __name__ == '__main__':
    unittest.main()
