import unittest

import jsons

from core.const import ConnState
from drivers.SWM100FHD import SWM100FHD
from interface import DriverError


# noinspection DuplicatedCode
class TestSWM100FHD(unittest.TestCase):
    swm100fhd: SWM100FHD = None

    @classmethod
    def setUpClass(cls):
        config = {
            "name": "cam_a_1",
            "driver": "SWM100FHD",
            "dev_num": 0,
            "dst_ip": "192.168.10.104",
            "dst_port": 5000,
            "protocol": "udp",
        }
        cls.swm100fhd = jsons.load(config, SWM100FHD)
        try:
            cls.swm100fhd.on_start([True], {})
        except Exception as e:
            raise DriverError(e)

    @classmethod
    def tearDownClass(cls):
        cls.swm100fhd.on_stop()

    def test_check_connection(self):
        self.assertEqual(self.swm100fhd.check_connection(), ConnState.CONNECTED)


if __name__ == '__main__':
    unittest.main()
