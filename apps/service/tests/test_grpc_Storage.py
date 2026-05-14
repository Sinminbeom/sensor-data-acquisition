import json
import logging
import unittest
from concurrent import futures

import grpc

import protos.service_pb2_grpc as pb_grpc
from core.ServiceServer import ServiceServer
from service_pb2 import Connection, Sensor


# noinspection DuplicatedCode
class TestGrpcStorage(unittest.TestCase):
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
        connection = self.client.is_connected(Sensor(name='storage'))
        self.assertEqual(connection.state, Connection.State.CONNECTED)

    def test_snapshot(self):
        snapshot = self.client.get_snapshot(Sensor(name='storage'))
        self.assertEqual(snapshot.name, 'storage')
        self.assertEqual(snapshot.content_type, 'application/json')

        # snapshot.data to json
        storage_stat = json.loads(snapshot.data)
        # check keys
        self.assertIn('total', storage_stat)
        self.assertIn('used', storage_stat)
        self.assertIn('free', storage_stat)


if __name__ == '__main__':
    unittest.main()
