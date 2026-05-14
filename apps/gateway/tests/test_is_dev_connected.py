import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from gateway_pb2 import Device
from service_pb2 import Connection, void


# noinspection DuplicatedCode
class TestIsDevConnected(unittest.TestCase):
    def setUp(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        pb_grpc.add_GatewayServicer_to_server(GatewayServer('config/test_is_dev_connected.json'), self.server)
        port = self.server.add_insecure_port('[::]:0')
        self.server.start()
        self.channel = grpc.insecure_channel(f'localhost:{port}')
        self.client = pb_grpc.GatewayStub(self.channel)

    def tearDown(self):
        self.server.stop(None)
        self.channel.close()

    def test_is_dev_connected_unknown(self):
        request = Device(name='unknown')
        connection = self.client.is_dev_connected(request)
        self.assertEqual(connection.state, Connection.State.UNKNOWN)

    def test_is_dev_connected_connected(self):
        request = Device(name='localhost')
        connection = self.client.is_dev_connected(request)
        self.assertEqual(connection.state, Connection.State.CONNECTED)

    def test_is_dev_connected_disconnected(self):
        request = Device(name='unreachable')
        connection = self.client.is_dev_connected(request)
        self.assertEqual(connection.state, Connection.State.DISCONNECTED)

    def test_is_all_dev_connected(self):
        connections = self.client.is_all_dev_connected(void())
        for connection in connections.list:
            if connection.name == 'localhost':
                self.assertEqual(connection.state, Connection.State.CONNECTED)
            elif connection.name == 'unreachable':
                self.assertEqual(connection.state, Connection.State.DISCONNECTED)


if __name__ == '__main__':
    unittest.main()
