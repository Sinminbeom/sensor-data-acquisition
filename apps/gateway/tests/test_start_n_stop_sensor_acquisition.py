import unittest
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from core import GatewayServer
from gateway_pb2 import Device
from service_pb2 import Connection, Sensor, Health, void, Acquisition


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

    def test_start_acquisition_success(self):
        sensor = Sensor(name='cpu/dummy_start_acquisition_success')
        acquisition = self.client.start_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)

    def test_start_acquisition_fail_unknown(self):
        sensor = Sensor(name='cpu/dummy_start_acquisition_fail_unknown')
        acquisition = self.client.start_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)

    def test_start_acquisition_fail_not_acquiring(self):
        sensor = Sensor(name='cpu/dummy_start_acquisition_fail_not_acquiring')
        acquisition = self.client.start_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)

    def test_start_all_acquisition(self):
        acquisitions = self.client.start_all_sensor_acquisition(void())
        for acquisition in acquisitions.list:
            if acquisition.name == 'cpu/dummy_start_acquisition_success':
                self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)
            elif acquisition.name == 'cpu/dummy_start_acquisition_fail_unknown':
                self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)
            elif acquisition.name == 'cpu/dummy_start_acquisition_fail_not_acquiring':
                self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)

    def test_stop_acquisition_success(self):
        sensor = Sensor(name='cpu/dummy_stop_acquisition_success')
        acquisition = self.client.stop_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)

    def test_stop_acquisition_fail_unknown(self):
        sensor = Sensor(name='cpu/dummy_stop_acquisition_fail_unknown')
        acquisition = self.client.stop_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)

    def test_stop_acquisition_fail_acquiring(self):
        sensor = Sensor(name='cpu/dummy_stop_acquisition_fail_acquiring')
        acquisition = self.client.stop_sensor_acquisition(sensor)
        self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)

    def test_stop_all_acquisition(self):
        acquisitions = self.client.stop_all_sensor_acquisition(void())
        for acquisition in acquisitions.list:
            if acquisition.name == 'cpu/dummy_stop_acquisition_success':
                self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)
            elif acquisition.name == 'cpu/dummy_stop_acquisition_fail_unknown':
                self.assertEqual(acquisition.state, Acquisition.State.UNKNOWN)
            elif acquisition.name == 'cpu/dummy_stop_acquisition_fail_acquiring':
                self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)


if __name__ == '__main__':
    unittest.main()
