import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from service_pb2 import Connection, Sensor, void


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

    def test_is_connected_unknown(self):
        request = Sensor(name='cpu/dummy_connection_unknown')
        connection = self.client.is_sensor_connected(request)
        self.assertEqual(connection.state, Connection.State.UNKNOWN)

    def test_is_connected_connected(self):
        request = Sensor(name='cpu/dummy_connection_connected')
        connection = self.client.is_sensor_connected(request)
        self.assertEqual(connection.state, Connection.State.CONNECTED)

    def test_is_connected_disconnected(self):
        request = Sensor(name='cpu/dummy_connection_disconnected')
        connection = self.client.is_sensor_connected(request)
        self.assertEqual(connection.state, Connection.State.DISCONNECTED)

    def test_is_all_sensor_connected(self):
        connections = self.client.is_all_sensor_connected(void())
        for connection in connections.list:
            if connection.name == 'cpu/dummy_connection_unknown':
                self.assertEqual(connection.state, Connection.State.UNKNOWN)
            elif connection.name == 'cpu/dummy_connection_connected':
                self.assertEqual(connection.state, Connection.State.CONNECTED)
            elif connection.name == 'cpu/dummy_connection_disconnected':
                self.assertEqual(connection.state, Connection.State.DISCONNECTED)


if __name__ == '__main__':
    unittest.main()
