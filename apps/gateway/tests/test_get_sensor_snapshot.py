import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from service_pb2 import void, Sensor


class TestGetSensorSnapshot(unittest.TestCase):
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

    def test_get_sensor_snapshot(self):
        sensor = Sensor(name='cpu/snapshotable')
        snapshot = self.client.get_sensor_snapshot(sensor)
        self.assertEqual(snapshot.content_type, 'image/jpeg')

    def test_get_all_sensor_snapshot(self):
        snapshots = self.client.get_all_sensor_snapshot(void())
        for snapshot in snapshots.list:
            self.assertEqual(snapshot.content_type, 'image/jpeg')


if __name__ == '__main__':
    unittest.main()
