import logging
import os
from concurrent import futures

import grpc

from protos.service_pb2 import *
import protos.service_pb2_grpc as pb_grpc
from core.Drivers import Drivers


class ServiceServer(pb_grpc.ServiceServicer):
    _drivers = None

    def __init__(self, sensors: list):
        self._drivers = Drivers.load(sensors)

    def __del__(self):
        if self._drivers:
            self._drivers.stop_all()

    def run(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        pb_grpc.add_ServiceServicer_to_server(self, server)
        server.add_insecure_port('0.0.0.0:50051')
        server.start()
        logging.info('Service Server started. Listening on port 50051.')
        server.wait_for_termination()

    def ping(self, request, context):
        return void()

    def get_sensors(self, request, context):
        names, reason = self._drivers.get_sensor_names()
        return Sensors(list=names, reason=reason)

    def is_connected(self, request, context):
        connection = self._drivers.check_connection(request.name)
        return Connection(name=request.name, state=connection.value)

    def is_healthy(self, request, context):
        health, reason = self._drivers.check_health(request.name)
        return Health(name=request.name, status=health.value, reason=reason)

    def get_snapshot(self, request, context):
        content_type, data = self._drivers.get_snapshot(request.name)
        return SensorSnapshot(name=request.name, content_type=content_type, data=data)

    def get_snapshots(self, request, context):
        shots = [SensorSnapshot(name=name, content_type=content_type, data=data)
                 for name, content_type, data in self._drivers.get_snapshots()]
        return SensorSnapshots(list=shots)

    def is_acquiring(self, request, context):
        acquisition, reason = self._drivers.check_acquisition(request.name)
        return Acquisition(name=request.name, state=acquisition.value, reason=reason)

    def start_acquisition(self, request, context):
        acquisition, reason = self._drivers.start_acquisition(request.name)
        return Acquisition(name=request.name, state=acquisition.value, reason=reason)

    def stop_acquisition(self, request, context):
        acquisition, reason = self._drivers.stop_acquisition(request.name)
        return Acquisition(name=request.name, state=acquisition.value, reason=reason)
