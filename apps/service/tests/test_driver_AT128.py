import logging
import threading
import time
import unittest

import jsons

from core.const import ConnState, HealthStatus, AcqState
from drivers.AT128 import AT128
from drivers.Storage import Storage
from interface import DriverError


# noinspection DuplicatedCode
class TestAT128(unittest.TestCase):
    ACQ_DURATION = 10
    loop = False

    storage: Storage = None
    at128: AT128 = None

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

        # Prepare AT128 driver
        config = {
            "name": "eth_e_a",
            "driver": "AT128",
            "src_ip": "192.168.20.201",
            "protocol": "udp",
            "dst_ip": "192.168.20.100",
            "dst_port": 2361,

            "ping_count": 1,
            "ping_timeout": 0.3,
            "packet_loss_threshold": 0.2,

            "spin_rate": 400,
            "return_mode": "Last Return",
            "max_temperature_threshold": 85,
            "min_temperature_threshold": -40,

            "call_timeout": 0.5,

            "extrinsic": "config/eth_e_a_extrinsics.yaml"
        }
        cls.at128 = jsons.load(config, AT128)
        try:
            cls.at128.on_start([True], drivers)
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.at128.on_stop()
        cls.storage.on_stop()

    def test_check_connection(self):
        self.assertEqual(self.at128.check_connection(), ConnState.CONNECTED)

    # def test_acquisition(self):
    #     # Test start_acquisition
    #     self.assertEqual(self.at128.start_acquisition()[0], AcqState.ACQUIRING)
    #
    #     # Test check_acquisition after start_acquisition
    #     self.assertEqual(self.at128.check_acquisition()[0], AcqState.ACQUIRING)
    #     threading.Timer(self.ACQ_DURATION, self.__test_stop_acquisition).start()
    #
    #     self.loop = True
    #     while self.loop:
    #         time.sleep(0.1)
    #
    #     # Test check_acquisition after stop_acquisition
    #     self.assertEqual(self.at128.check_acquisition()[0], AcqState.NOT_ACQUIRING)
    #
    # def __test_stop_acquisition(self):
    #     # Test stop_acquisition
    #     self.assertEqual(self.at128.stop_acquisition()[0], AcqState.NOT_ACQUIRING)
    #     self.loop = False
    #
    # def test_check_health(self):
    #     self.assertEqual(self.at128.check_health(), (HealthStatus.GOOD, ''))


if __name__ == '__main__':
    unittest.main()
