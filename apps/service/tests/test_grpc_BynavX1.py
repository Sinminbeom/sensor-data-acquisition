import json
import logging
import threading
import time
import unittest
from concurrent import futures

import grpc

import protos.service_pb2_grpc as pb_grpc
from core.ServiceServer import ServiceServer
from service_pb2 import Connection, Health, Sensor, Acquisition


class TestGrpcBynavX1(unittest.TestCase):
    ACQ_DURATION = 10
    loop = False

    server = None
    channel = None

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

        sensors = cls.process_config('config/T_BENCH_2/cpu.json')

        cls.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        pb_grpc.add_ServiceServicer_to_server(ServiceServer(sensors), cls.server)
        port = cls.server.add_insecure_port('[::]:0')
        cls.server.start()
        cls.channel = grpc.insecure_channel(f'localhost:{port}')
        cls.client = pb_grpc.ServiceStub(cls.channel)

    @classmethod
    def process_config(cls, file_path) -> list:
        import os
        import json
        with open(file_path, "r") as config_json:
            config = json.load(config_json)

        if 'vid' not in config:
            raise ValueError('Vehicle ID(vid: str) is not defined in the config file.')

        os.environ['VEHICLE_ID'] = config['vid']

        if 'sensors' not in config:
            raise ValueError('Sensors(sensors: list) are not defined in the config file.')

        return config['sensors']

    @classmethod
    def tearDownClass(cls):
        cls.server.stop(None)
        cls.server = None
        cls.channel.close()

    def test_check_connection(self):
        connection = self.client.is_connected(Sensor(name='imu'))
        self.assertEqual(connection.state, Connection.State.CONNECTED)

    def test_snapshot(self):
        snapshot = self.client.get_snapshot(Sensor(name='imu'))
        self.assertEqual(snapshot.name, 'imu')
        self.assertEqual(snapshot.content_type, 'application/json')

        # snapshot.data to json
        location = json.loads(snapshot.data)
        # check keys
        self.assertIn('lat', location)
        self.assertIn('lon', location)
        self.assertIn('solnsvs', location)

    def test_acquisition(self):
        # Test start_acquisition
        acquisition = self.client.start_acquisition(Sensor(name='imu'))
        self.assertEqual(acquisition.name, 'imu')
        self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)
        self.assertEqual(acquisition.reason, '')

        # Test check_acquisition after start_acquisition
        acquisition = self.client.is_acquiring(Sensor(name='imu'))
        self.assertEqual(acquisition.name, 'imu')
        self.assertEqual(acquisition.state, Acquisition.State.ACQUIRING)
        self.assertEqual(acquisition.reason, '')

        threading.Timer(self.ACQ_DURATION, self.__test_stop_acquisition).start()
        self.loop = True
        while self.loop:
            time.sleep(0.1)

        # Test check_acquisition after stop_acquisition
        acquisition = self.client.is_acquiring(Sensor(name='imu'))
        self.assertEqual(acquisition.name, 'imu')
        self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)
        self.assertEqual(acquisition.reason, '')

    def __test_stop_acquisition(self):
        # Test stop_acquisition
        acquisition = self.client.stop_acquisition(Sensor(name='imu'))
        self.assertEqual(acquisition.name, 'imu')
        self.assertEqual(acquisition.state, Acquisition.State.NOT_ACQUIRING)
        self.assertEqual(acquisition.reason, '')
        self.loop = False

    def test_check_health(self):
        health = self.client.is_healthy(Sensor(name='imu'))
        self.assertEqual(health.name, 'imu')
        self.assertEqual(health.status, Health.Status.GOOD)
        self.assertEqual(health.reason, '')


if __name__ == '__main__':
    unittest.main()
