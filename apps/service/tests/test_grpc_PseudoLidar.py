import logging
import unittest
from concurrent import futures

import grpc

import protos.service_pb2_grpc as pb_grpc

from core.ServiceServer import ServiceServer
from service_pb2 import Sensor


class TestGrpcPseudoLidar(unittest.TestCase):
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

    def test_snapshot(self):
        # Test get_snapshot 5 times
        for i in range(5):
            snapshot = self.client.get_snapshot(Sensor(name='lidar'))
            self.assertEqual(snapshot.name, 'lidar')
            self.assertEqual(snapshot.content_type, 'image/png')
            with open(f'tmp/grpc_lidar_snapshot_{i}.png', 'wb') as f:
                f.write(snapshot.data)


if __name__ == '__main__':
    unittest.main()
