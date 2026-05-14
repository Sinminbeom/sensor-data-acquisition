import logging
import threading
import time

import grpc

import protos.gateway_pb2_grpc as pb_grpc
from service_pb2 import SensorSnapshot, Sensor
from dbg_flag import CAM


class ImageInvoker(threading.Thread):
    _channel = None
    _client = None
    _callback = None

    def __init__(self, duration_sec: float):
        super().__init__()
        self._event = threading.Event()
        self._duration_sec = duration_sec

        self._png_lock = threading.Lock()
        self._png: bytes = b''

    def open(self, callback) -> 'ImageInvoker':
        self._callback = callback
        self.start()
        return self

    def close(self) -> None:
        self._event.set()
        self.join()

    def get_content(self) -> bytes:
        with self._png_lock:
            return self._png

    def run(self):
        self._on_loop_start()

        while not self._event.is_set():
            start_time = time.time()
            self._loop()
            end_time = time.time()
            time_diff = end_time - start_time
            if time_diff < self._duration_sec:
                time.sleep(self._duration_sec - time_diff)
            else:
                logging.warning(f"Loop took {time_diff} seconds")

        self._on_loop_stop()

    def _on_loop_start(self):
        self._channel = grpc.insecure_channel('192.168.20.100:50050')
        self._client = pb_grpc.GatewayStub(self._channel)

    def _loop(self):
        if CAM:
            snapshot: SensorSnapshot = self._client.get_sensor_snapshot(Sensor(name='vpu_a/cam_a_1'))
            wish_content_type = 'image/jpeg'
        else:
            snapshot: SensorSnapshot = self._client.get_sensor_snapshot(Sensor(name='cpu/lidar'))
            wish_content_type = 'image/png'
        if snapshot.content_type == wish_content_type:
            with self._png_lock:
                self._png = snapshot.data
            self._callback(self._png)

    def _on_loop_stop(self):
        self._channel.close()
