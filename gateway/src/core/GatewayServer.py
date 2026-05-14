import logging
from concurrent import futures

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from .Devices import Devices
from .ThumbnailLogger import ThumbnailLogger
from gateway_pb2 import Healths, Connections, Acquisitions
from service_pb2 import Connection, Health, Acquisition, Sensors, SensorSnapshot, SensorSnapshots, void


class GatewayServer(pb_grpc.GatewayServicer):
    def __init__(self, config_file_path: str):
        self._devices = Devices.load(config_file_path)
        self._thumbnail_logger = ThumbnailLogger(self._devices)

    def run(self):
        self._thumbnail_logger.start()

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        pb_grpc.add_GatewayServicer_to_server(self, server)
        server.add_insecure_port('[::]:50050')
        server.start()
        logging.info('Gateway Server started. Listening on port 50050.')
        server.wait_for_termination()

    def __del__(self):
        if self._thumbnail_logger and self._thumbnail_logger.is_alive():
            self._thumbnail_logger.stop()

    def ping(self, request, context):
        return void()

    def is_dev_connected(self, request, context) -> Connection:
        return self._devices.is_dev_connected(request.name)

    def is_all_dev_connected(self, request, context) -> Connections:
        return self._devices.is_all_dev_connected()

    def is_dev_healthy(self, request, context) -> Health:
        return self._devices.is_dev_healthy(request.name)

    def is_all_dev_healthy(self, request, context) -> Healths:
        return self._devices.is_all_dev_healthy()

    def get_sensors(self, request, context) -> Sensors:
        return self._devices.get_sensors()

    def is_sensor_connected(self, request, context) -> Connection:
        return self._devices.is_sensor_connected(request.name)

    def is_all_sensor_connected(self, request, context) -> Connections:
        return self._devices.is_all_sensor_connected()

    def is_sensor_healthy(self, request, context) -> Health:
        return self._devices.is_sensor_healthy(request.name)

    def is_all_sensor_healthy(self, request, context) -> Healths:
        return self._devices.is_all_sensor_healthy()

    def get_sensor_snapshot(self, request, context) -> SensorSnapshot:
        return self._devices.get_sensor_snapshot(request.name)

    def get_all_sensor_snapshot(self, request, context) -> SensorSnapshots:
        return self._devices.get_all_sensor_snapshot()

    def is_sensor_acquiring(self, request, context) -> Acquisition:
        return self._devices.is_sensor_acquiring(request.name)

    def is_all_sensor_acquiring(self, request, context) -> Acquisitions:
        return self._devices.is_all_sensor_acquiring()

    def start_sensor_acquisition(self, request, context) -> Acquisition:
        return self._devices.start_sensor_acquisition(request.name)

    def start_all_sensor_acquisition(self, request, context) -> Acquisitions:
        return self._devices.start_all_sensor_acquisition()

    def stop_sensor_acquisition(self, request, context) -> Acquisition:
        return self._devices.stop_sensor_acquisition(request.name)

    def stop_all_sensor_acquisition(self, request, context) -> Acquisitions:
        return self._devices.stop_all_sensor_acquisition()

    def add_voice_tag(self, request, context):
        self._thumbnail_logger.add_voice_tag(request.timestamp, request.voice)
        return void()
