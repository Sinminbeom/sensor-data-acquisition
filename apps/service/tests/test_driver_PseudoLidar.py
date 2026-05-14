import logging
import unittest

import jsons

from drivers.PseudoLidar import PseudoLidar
from drivers.RSBP import RSBP
from drivers.AT128 import AT128
from interface import DriverError


# noinspection DuplicatedCode
class TestPseudoLidar(unittest.TestCase):
    at128: AT128 = None
    rsbp: RSBP = None
    pseudo_lidar: PseudoLidar = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

        drivers = {}

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
            drivers["eth_e_a"] = cls.at128
        except Exception as e:
            raise DriverError(e)

        # Prepare RSBP driver
        config = {
            "name": "eth_e_i",
            "driver": "RSBP",
            "src_ip": "192.168.20.112",
            "protocol": "udp",
            "dst_ip": "192.168.20.100",
            "dst_port": 6701,
            "difop_port": 7789,
            "ret_mode": "Strong",
            "rpm": 600,

            'min_distance': 0,
            'max_distance': 200,
            'start_angle': 0,
            'end_angle': 360,

            "ping_count": 1,
            "ping_timeout": 0.3,
            "packet_loss_threshold": 0.2,

            "call_timeout": 0.5,

            "extrinsic": "config/eth_e_i_extrinsics.yaml"
        }
        cls.rsbp = jsons.load(config, RSBP)
        try:
            cls.rsbp.on_start([True], drivers)
            drivers["eth_e_i"] = cls.rsbp
        except Exception as e:
            raise DriverError(e)

        # Prepare PseudoLidar driver
        config = {
            "name": "lidar",
            "driver": "PseudoLidar",
            "image_width": 800,
            "image_height": 800,
            "zFar": 70
        }
        cls.pseudo_lidar = jsons.load(config, PseudoLidar)
        try:
            cls.pseudo_lidar.on_start([True], drivers)
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.pseudo_lidar.on_stop()
        cls.rsbp.on_stop()
        cls.at128.on_stop()

    def test_snapshot(self):
        content_type, data = self.pseudo_lidar.snapshot()
        self.assertEqual(content_type, 'image/png')
        with open('tmp/pseudo_lidar_snapshot.png', 'wb') as f:
            f.write(data)


if __name__ == '__main__':
    unittest.main()
