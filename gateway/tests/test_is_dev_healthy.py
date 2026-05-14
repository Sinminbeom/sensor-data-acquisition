import sys
import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from gateway_pb2 import Device
from service_pb2 import Health, void


# noinspection DuplicatedCode
class TestIsDevHealthy(unittest.TestCase):
    def setUp(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        pb_grpc.add_GatewayServicer_to_server(GatewayServer('config/test_is_dev_healthy.json'), self.server)
        port = self.server.add_insecure_port('[::]:0')
        self.server.start()
        self.channel = grpc.insecure_channel(f'localhost:{port}')
        self.client = pb_grpc.GatewayStub(self.channel)

    def tearDown(self):
        self.server.stop(None)
        self.channel.close()

    def test_is_dev_healthy_unknown(self):
        request = Device(name='unknown_dev')
        health = self.client.is_dev_healthy(request)
        self.assertEqual(health.status, Health.Status.UNKNOWN)

    def test_is_dev_healthy_good(self):
        request = Device(name='healthy_dev')
        health = self.client.is_dev_healthy(request)
        if health.reason:
            print(health.reason, file=sys.stderr)
        self.assertEqual(health.status, Health.Status.GOOD)

    def test_is_dev_healthy_baad(self):
        request = Device(name='unhealthy_dev')
        health = self.client.is_dev_healthy(request)
        self.assertEqual(health.status, Health.Status.BAAD)

    def test_is_all_dev_healthy(self):
        healths = self.client.is_all_dev_healthy(void())
        for health in healths.list:
            if health.name == 'healthy_dev':
                self.assertEqual(health.status, Health.Status.GOOD)
            elif health.name == 'unhealthy_dev':
                self.assertEqual(health.status, Health.Status.BAAD)
            elif health.name == 'unknown_dev':
                self.assertEqual(health.status, Health.Status.UNKNOWN)


if __name__ == '__main__':
    unittest.main()
