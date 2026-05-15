import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from gateway_pb2 import Device
from service_pb2 import Connection, Sensor, Health, void


class TestProtocolGateway(unittest.TestCase):
    def setUp(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        pb_grpc.add_GatewayServicer_to_server(GatewayServer('config/test_sensor_functions.json'), self.server)
        port = self.server.add_insecure_port('[::]:0')
        self.server.start()
        self.channel = grpc.insecure_channel(f'localhost:{port}')
        self.client = pb_grpc.GatewayStub(self.channel)

    def tearDown(self):
        self.server.stop(None)
        self.channel.close()

    def test_is_sensor_healthy_uncheckable(self):
        sensor = Sensor(name='cpu/dummy_health_uncheckable')
        health = self.client.is_sensor_healthy(sensor)
        self.assertEqual(health.status, Health.Status.UNKNOWN)
        self.assertEqual(health.reason, 'This driver does not support health check.')

    def test_is_sensor_healthy_unknown(self):
        sensor = Sensor(name='cpu/dummy_health_unknown')
        health = self.client.is_sensor_healthy(sensor)
        self.assertEqual(health.status, Health.Status.UNKNOWN)

    def test_is_sensor_healthy_good(self):
        sensor = Sensor(name='cpu/dummy_health_good')
        health = self.client.is_sensor_healthy(sensor)
        self.assertEqual(health.status, Health.Status.GOOD)

    def test_is_sensor_healthy_warn(self):
        sensor = Sensor(name='cpu/dummy_health_warn')
        health = self.client.is_sensor_healthy(sensor)
        self.assertEqual(health.status, Health.Status.WARN)

    def test_is_sensor_healthy_baad(self):
        sensor = Sensor(name='cpu/dummy_health_baad')
        health = self.client.is_sensor_healthy(sensor)
        self.assertEqual(health.status, Health.Status.BAAD)

    def test_is_all_sensor_healthy(self):
        healths = self.client.is_all_sensor_healthy(void())
        for health in healths.list:
            if health.name == 'cpu/dummy_health_uncheckable':
                self.assertEqual(health.status, Health.Status.UNKNOWN)
                self.assertEqual(health.reason, 'This driver does not support health check.')
            elif health.name == 'cpu/dummy_health_unknown':
                self.assertEqual(health.status, Health.Status.UNKNOWN)
            elif health.name == 'cpu/dummy_health_good':
                self.assertEqual(health.status, Health.Status.GOOD)
            elif health.name == 'cpu/dummy_health_warn':
                self.assertEqual(health.status, Health.Status.WARN)
            elif health.name == 'cpu/dummy_health_baad':
                self.assertEqual(health.status, Health.Status.BAAD)


if __name__ == '__main__':
    unittest.main()
