import logging
import threading
import time
import unittest

import jsons

from core.const import ConnState, AcqState
from drivers.NetCamera import NetCamera
from drivers.Storage import Storage
from interface import DriverError


# noinspection DuplicatedCode
class TestNetCamera(unittest.TestCase):
    ACQ_DURATION = 10
    loop = False

    storage: Storage = None
    net_cam: NetCamera = None

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

        # Prepare NetCamera driver
        config = {
            "name": "cam_a_1",
            "driver": "NetCamera",
            "src_ip": "192.168.10.124",
            "protocol": "udp",
            "dst_port": 5000,
            "sniff_timeout": 0.3
        }
        cls.net_cam = jsons.load(config, NetCamera)
        try:
            cls.net_cam.on_start([True], drivers)
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.net_cam.on_stop()
        cls.storage.on_stop()

    def test_check_connection(self):
        self.assertEqual(self.net_cam.check_connection(), ConnState.CONNECTED)

    def test_acquisition(self):
        # Test start_acquisition
        self.assertEqual(self.net_cam.start_acquisition()[0], AcqState.ACQUIRING)

        # Test check_acquisition after start_acquisition
        self.assertEqual(self.net_cam.check_acquisition()[0], AcqState.ACQUIRING)
        threading.Timer(self.ACQ_DURATION, self.__test_stop_acquisition).start()

        self.loop = True
        while self.loop:
            time.sleep(0.1)

        # Test check_acquisition after stop_acquisition
        self.assertEqual(self.net_cam.check_acquisition()[0], AcqState.NOT_ACQUIRING)

    def __test_stop_acquisition(self):
        # Test stop_acquisition
        self.assertEqual(self.net_cam.stop_acquisition()[0], AcqState.NOT_ACQUIRING)
        self.loop = False


if __name__ == '__main__':
    unittest.main()
