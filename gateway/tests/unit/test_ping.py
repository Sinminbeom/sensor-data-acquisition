import unittest

from pythonping import ping


class TestPing(unittest.TestCase):
    def test_ping_success(self):
        ip = '192.168.1.1'
        data = ping(ip, count=1, timeout=1)
        self.assertLessEqual(data.packet_loss, 0.2)

    def test_ping_fail(self):
        ip = '192.168.1.255'
        data = ping(ip, count=1, timeout=1)
        self.assertGreater(data.packet_loss, 0.2)


if __name__ == '__main__':
    unittest.main()
