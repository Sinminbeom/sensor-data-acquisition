import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from gateway_pb2 import Device
from service_pb2 import Connection, Sensor, Health, void, Acquisition


# noinspection DuplicatedCode
class TestIsSensorAcquiring(unittest.TestCase):
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

    def test_is_sensor_acquisition_unknown(self):
        sensor = Sensor(name='cpu/dummy_acquisition_unknown')
        acquisition = self.client.is_sensor_acquiring(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)

    def test_is_sensor_acquisition_acquiring(self):
        sensor = Sensor(name='cpu/dummy_acquisition_acquiring')
        acquisition = self.client.is_sensor_acquiring(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)

    def test_is_sensor_acquisition_not_acquiring(self):
        sensor = Sensor(name='cpu/dummy_acquisition_not_acquiring')
        acquisition = self.client.is_sensor_acquiring(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)

    def test_is_all_sensor_acquiring(self):
        acquisitions = self.client.is_all_sensor_acquiring(void())
        for acquisition in acquisitions.list:
            if acquisition.name == 'cpu/dummy_acquisition_unknown':
                self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)
            elif acquisition.name == 'cpu/dummy_acquisition_acquiring':
                self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)
            elif acquisition.name == 'cpu/dummy_acquisition_not_acquiring':
                self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)


if __name__ == '__main__':
    unittest.main()
