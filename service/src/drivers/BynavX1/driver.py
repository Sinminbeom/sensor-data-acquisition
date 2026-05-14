import json
import threading
import time
from typing import Tuple

from pythonping import ping

from core.Acquisitor import Acquisitor
from core.const import *
from interface import GNSSDriver, DriverError
from .fake_recv import FakeReceiver
from .ntrip_bridge import NtripBridge
from .proxy import BynavX1Proxy


class ProtocolError(Exception):
    pass


class ReqBufferBynavX1(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.ping_count = 1
        self.ping_timeout = 0.3
        self.packet_loss_threshold = 0.1

        self.src_ip = config['src_ip']
        self._proxy = config['proxy']

        self._connection_lock = threading.Lock()
        self._connection: ConnState = ConnState.UNKNOWN

        self._health_lock = threading.Lock()
        self._health: Tuple[HealthStatus, str] = (HealthStatus.UNKNOWN, '')

    def start(self) -> 'ReqBufferBynavX1':
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

    def connection(self) -> ConnState:
        with self._connection_lock:
            return self._connection

    def health(self) -> Tuple[HealthStatus, str]:
        with self._health_lock:
            return self._health

    def _check_connection(self):
        data = ping(self.src_ip, count=self.ping_count, timeout=self.ping_timeout)
        with self._connection_lock:
            self._connection = ConnState.CONNECTED if data.packet_loss <= self.packet_loss_threshold else ConnState.DISCONNECTED

    def _check_health(self):
        try:
            health = self._proxy.get_health()

            solstat_status, solstat_reason = self._check_solution_status(health)
            postype_status, postype_reason = self._check_position_type(health)
            diffage_status, diffage_reason = self._check_differential_age(health)
            deviation_status, deviation_reason = self._check_deviation(health, 0.3)

            status = max(solstat_status, postype_status, diffage_status, deviation_status)
            with self._health_lock:
                self._health = status, f'{solstat_reason}\n{postype_reason}\n{diffage_reason}\n{deviation_reason}'

        except DriverError as e:
            with self._health_lock:
                self._health = HealthStatus.BAAD, str(e)

    ###################################################################
    # Private methods

    @staticmethod
    def _check_solution_status(health):
        if 'solstat' not in health:
            return HealthStatus.UNKNOWN, 'No solstat'
        solstat = health['solstat']
        if solstat == 'SOL_COMPUTED':
            return HealthStatus.GOOD, ''
        else:
            return HealthStatus.WARN, f'solstat is {solstat}'

    @staticmethod
    def _check_position_type(health):
        if 'postype' not in health:
            return HealthStatus.UNKNOWN, 'No postype'
        postype = health['postype']
        if postype in ['NARROW_INT', 'INS_RTKFLOAT', 'INS_RTKFIXED']:
            return HealthStatus.GOOD, ''
        elif postype in ['SINGLE', 'PSRDIFF', 'WIDE_INT']:
            return HealthStatus.WARN, f'postype is {postype}'
        else:
            return HealthStatus.BAAD, f'postype is {postype}'

    @staticmethod
    def _check_differential_age(health):
        if 'diffage' not in health:
            return HealthStatus.UNKNOWN, 'No diffage'
        diffage = health['diffage']
        if diffage == 0.0 or diffage > 1.0:
            return HealthStatus.WARN, 'diffage is not greater than 0.0 and less than 1.0'
        return HealthStatus.GOOD, ''

    @staticmethod
    def _check_deviation(health, threshold):
        if 'latstd' not in health or 'lonstd' not in health:
            return HealthStatus.UNKNOWN, 'No latstd or lonstd'
        latstd = health['latstd']
        lonstd = health['lonstd']
        if latstd <= threshold and lonstd <= threshold:
            return HealthStatus.GOOD, ''
        return HealthStatus.WARN, f'latstd is {latstd}, lonstd is {lonstd}'


class BynavX1(GNSSDriver):
    src_ip: str = 'localhost'
    protocol: str = 'udp'
    dst_port: int = -1

    ping_count: int = 1
    ping_timeout: float = 0.3
    packet_loss_threshold: float = 0.1

    call_timeout = 0.5

    use_fake_tcp_reader: bool = False
    ntrip: dict = {}

    _req_buffer = None
    _proxy = None
    _ntrip_bridge = None
    _fake_recv: FakeReceiver = None
    _acquisitor: Acquisitor = None

    @staticmethod
    def _get_ntrip_config(config: dict) -> Tuple[dict, dict]:
        if 'from' not in config or 'to' not in config:
            raise ValueError('ntrip \'from\' and \'to\' configuration is required.')

        return config['from'], config['to']

    def on_start(self, is_init_ref: list, drivers: dict):
        self._proxy = BynavX1Proxy(f'ws://{self.src_ip}/webSock').start()

        self._req_buffer = ReqBufferBynavX1({
            'src_ip': self.src_ip,
            'proxy': self._proxy
        }).start()

        if self.ntrip:
            ntrip_from, ntrip_to = self._get_ntrip_config(self.ntrip)
            self._ntrip_bridge = NtripBridge(ntrip_from, ntrip_to)
            self._ntrip_bridge.start()

        if self.use_fake_tcp_reader:
            self._fake_recv = FakeReceiver(self.src_ip, self.dst_port)
            self._fake_recv.start()

        self._acquisitor = Acquisitor(drivers, self.name)

    def on_stop(self):
        self._acquisitor.stop_acquisition()

        if self._fake_recv and self._fake_recv.is_alive():
            self._fake_recv.stop()

        if self._ntrip_bridge and self._ntrip_bridge.is_alive():
            self._ntrip_bridge.stop()

        if self._req_buffer and self._req_buffer.is_alive():
            self._req_buffer.stop()
            self._req_buffer = None

        if self._proxy and self._proxy.is_alive():
            self._proxy.stop()

    def check_connection(self) -> ConnState:
        return self._req_buffer.connection()

    def snapshot(self) -> Tuple[str, bytes]:
        try:
            return 'application/json', json.dumps(self._proxy.get_location()).encode()
        except DriverError as e:
            return 'exception', str(e).encode()

    def check_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.check_acquisition()

    def start_acquisition(self) -> Tuple[AcqState, str]:
        filter_str = f'src {self.src_ip} and {self.protocol} port {self.dst_port}'
        return self._acquisitor.start_acquisition(filter_str)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.stop_acquisition()

    def check_health(self) -> Tuple[HealthStatus, str]:
        return self._req_buffer.health()
