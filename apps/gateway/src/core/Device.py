import logging
import threading
import time
from typing import List, Tuple

import grpc
from pythonping import ping

import protos.service_pb2_grpc as pb_grpc
from core.DeviceError import DeviceError
from service_pb2 import Connection, Health, void, Sensor, Acquisition, SensorSnapshots


class DeviceReqBuffer(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.ip = config['ip']
        self.ping_timeout = config['ping_timeout']
        self.client = config['client']
        self.call_timeout = config['call_timeout']

        self._connection_lock = threading.Lock()
        self._connection: Connection.State = Connection.State.UNKNOWN

        self._health_lock = threading.Lock()
        self._health: Tuple[Health.Status, str] = (Health.Status.UNKNOWN, '')

    def start(self) -> 'DeviceReqBuffer':
        super().start()
        return self

    def stop(self):
        self._loop_stop.set()
        self.join()

    def run(self):
        while not self._loop_stop.is_set():
            self._check_connection()
            self._check_health()
            time.sleep(1)

    def connection(self) -> Connection.State:
        with self._connection_lock:
            return self._connection

    def _check_connection(self):
        data = ping(self.ip, count=1, timeout=self.ping_timeout)
        with self._connection_lock:
            self._connection = Connection.State.CONNECTED if data.packet_loss <= 0.2 \
                else Connection.State.DISCONNECTED

    def health(self) -> (Health.Status, str):
        with self._health_lock:
            return self._health

    def _check_health(self):
        try:
            # noinspection PyTestUnpassedFixture
            self.client.ping.with_call(void(), timeout=self.call_timeout)
            with self._health_lock:
                self._health = Health.Status.GOOD, ''
        except grpc.RpcError as e:
            with self._health_lock:
                self._health = Health.Status.BAAD, str(e.args[0].details)


class Device:
    ip: str
    ping_count: int = 1  # default 1 packet
    ping_timeout: float = 0.3  # default 300ms
    packet_loss_threshold: float = 0.2  # default 20%
    call_timeout = 0.5  # default 500ms
    acq_ip: str = None

    _channel: grpc.Channel
    _client: pb_grpc.ServiceStub
    _sensors: List[str] = []
    _acq_channel: grpc.Channel
    _acq_client: pb_grpc.ServiceStub

    _req_buffer: DeviceReqBuffer

    def post_init(self):
        self._channel = grpc.insecure_channel(f'{self.ip}:50051')
        self._client = pb_grpc.ServiceStub(self._channel)

        if not self.acq_ip:
            self.acq_ip = self.ip
        self._acq_channel = grpc.insecure_channel(f'{self.acq_ip}:50051')
        self._acq_client = pb_grpc.ServiceStub(self._acq_channel)

        self._req_buffer = DeviceReqBuffer({
            'ip': self.ip,
            'client': self._client,
            'ping_timeout': self.ping_timeout,
            'call_timeout': self.call_timeout,
        }).start()

    def __del__(self):
        self._req_buffer.stop()
        self._channel.close()
        self._acq_channel.close()

    @property
    def sensors(self):
        if not self._sensors:
            try:
                _sensors, _ = self._client.get_sensors.with_call(void(), timeout=self.call_timeout)
                self._sensors = [name for name in _sensors.list]
            except grpc.RpcError:
                return []
        return self._sensors

    def check_connection(self) -> Connection.State:
        if self._req_buffer and self._req_buffer.is_alive():
            return self._req_buffer.connection()

        data = ping(self.ip, count=self.ping_count, timeout=self.ping_timeout)
        return Connection.State.CONNECTED if data.packet_loss <= self.packet_loss_threshold \
            else Connection.State.DISCONNECTED

    def check_health(self) -> (Health.Status, str):
        if self._req_buffer and self._req_buffer.is_alive():
            return self._req_buffer.health()

        try:
            # noinspection PyTestUnpassedFixture
            self._client.ping.with_call(void(), timeout=self.call_timeout)
            return Health.Status.GOOD, ''
        except grpc.RpcError as e:
            return Health.Status.BAAD, str(e.args[0].details)

    def check_sensor_connection(self, sensor_name: str) -> Connection.State:
        try:
            connection, _ = self._client.is_connected.with_call(Sensor(name=sensor_name), timeout=self.call_timeout)
            return connection.state
        except grpc.RpcError:
            return Connection.State.DISCONNECTED

    def check_sensor_health(self, sensor_name: str) -> (Health.Status, str):
        try:
            health, _ = self._client.is_healthy.with_call(Sensor(name=sensor_name), timeout=self.call_timeout)
            return health.status, health.reason
        except grpc.RpcError as e:
            return Health.Status.BAAD, str(e.args[0].details)

    def get_sensor_snapshot(self, sensor_name: str) -> (str, bytes):
        try:
            snapshot, _ = self._client.get_snapshot.with_call(Sensor(name=sensor_name))
            return snapshot.content_type, snapshot.data
        except grpc.RpcError as e:
            return 'unknown', bytes(e.args[0].details, 'utf-8')

    def get_all_sensor_snapshot(self) -> SensorSnapshots:  # List of (content_type, data)
        try:
            _snapshots, _ = self._client.get_snapshots.with_call(void())
            return _snapshots
        except grpc.RpcError as e:
            raise DeviceError(e)

    def check_sensor_acquisition(self, sensor_name: str) -> (Acquisition.State, str):
        try:
            acquisition, _ = self._acq_client.is_acquiring.with_call(Sensor(name=sensor_name),
                                                                     timeout=self.call_timeout)
            return acquisition.state, acquisition.reason
        except grpc.RpcError as e:
            return Acquisition.State.UNKNOWN, str(e.args[0].details)

    def start_sensor_acquisition(self, sensor_name: str) -> (Acquisition.State, str):
        try:
            acquisition, _ = self._acq_client.start_acquisition.with_call(Sensor(name=sensor_name),
                                                                          timeout=self.call_timeout)
            logging.info(f"Acq started at '{sensor_name}': {acquisition.state}, reason: {acquisition.reason}")
            return acquisition.state, acquisition.reason
        except grpc.RpcError as e:
            logging.error(f"Acq start failed at '{sensor_name}': {e.args[0].details}")
            return Acquisition.State.UNKNOWN, str(e.args[0].details)

    def stop_sensor_acquisition(self, sensor_name: str) -> (Acquisition.State, str):
        try:
            acquisition, _ = self._acq_client.stop_acquisition.with_call(Sensor(name=sensor_name),
                                                                         timeout=self.call_timeout)
            logging.info(f"Acq stopped at '{sensor_name}': {acquisition.state}, reason: {acquisition.reason}")
            return acquisition.state, acquisition.reason
        except grpc.RpcError as e:
            logging.error(f"Acq stop failed at '{sensor_name}': {e.args[0].details}")
            return Acquisition.State.UNKNOWN, str(e.args[0].details)
