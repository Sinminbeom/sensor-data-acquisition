import json
import logging
from typing import Tuple

import numpy
import requests
from scapy.all import *

from core.Acquisitor import Acquisitor
from core.const import *
from interface import DriverError, LiDARDriver, DriverWarn
from .pcd_conv import AT128PcdConv


class ReqBufferAT128(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.sniff_timeout = 1
        self.call_timeout = 2

        self.src_ip = config['src_ip']
        self.protocol = config['protocol']
        self.dst_ip = config['dst_ip']
        self.dst_port = config['dst_port']
        self.spin_rate = config['spin_rate']
        self.return_mode = config['return_mode']
        self.max_temperature_threshold = config['max_temperature_threshold']
        self.min_temperature_threshold = config['min_temperature_threshold']

        self._connection_lock = threading.Lock()
        self._connection: ConnState = ConnState.UNKNOWN

        self._health_lock = threading.Lock()
        self._health: Tuple[HealthStatus, str] = (HealthStatus.UNKNOWN, '')

    def start(self) -> 'ReqBufferAT128':
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
        packet_filter = f'src host {self.src_ip} and {self.protocol} port {self.dst_port}'
        sniffed = sniff(iface=get_if_list(), filter=packet_filter, count=1, timeout=self.sniff_timeout)
        with self._connection_lock:
            self._connection = ConnState.CONNECTED if sniffed else ConnState.DISCONNECTED

    def _check_health(self):
        try:
            lidar_config = self._get_lidar_config()
            self._check_status(lidar_config)
            self._check_destination(lidar_config)

            lidar_mode = self._get_lidar_mode()
            self._check_lidar_mode(lidar_mode)

            lidar_statistic = self._get_lidar_statistic()
            self._check_temperature(lidar_statistic)

            with self._health_lock:
                self._health = HealthStatus.GOOD, ''

        except DriverWarn as e:
            with self._health_lock:
                self._health = HealthStatus.WARN, str(e)
        except DriverError as e:
            with self._health_lock:
                self._health = HealthStatus.BAAD, str(e)

    ###################################################################
    # Private methods

    def _get_lidar_config(self):
        return self._get_json_from_url(f'http://{self.src_ip}/pandar.cgi?action=get&object=lidar_config')

    def _get_lidar_mode(self):
        return self._get_json_from_url(f'http://{self.src_ip}/pandar.cgi?action=get&object=lidar_data&key=lidar_mode')

    def _get_lidar_statistic(self):
        return self._get_json_from_url(f'http://{self.src_ip}/pandar.cgi?action=get&object=operationstatistics')

    def _get_json_from_url(self, url):
        try:
            response = requests.get(url, timeout=self.call_timeout)
        except requests.exceptions.RequestException as e:
            raise DriverError(f'Failed to connect to {url} - {e}')

        if response.status_code != 200:
            raise DriverError(f'Failed to connect to {url}')
        return json.loads(response.text)

    def _check_status(self, data):
        # check spin rate
        spin_rate = self._spin_rate(int(data['Body']['SpinSpeed']))
        if spin_rate != self.spin_rate:
            raise DriverError(f'Spin rate is set {spin_rate}.')

        # check ptp status
        ptp_status = data['Body']['PTPStatus']
        is_locked = ptp_status.startswith('Locked')
        if not is_locked:
            raise DriverWarn(f'PTP is not locked.')

    @staticmethod
    def _spin_rate(spin_speed: int) -> int:
        table = [0, 300, 600, 1200, 200, 150, 750, 400, 500]
        return table[spin_speed]

    def _check_destination(self, data):
        # check destination ip
        dst_ip = data['Body']['DestIp']
        if dst_ip != self.dst_ip:
            raise DriverError(f'Destination IP is set {dst_ip}.')

        # check destination port
        dst_port = int(data['Body']['DestPort'])
        if dst_port != self.dst_port:
            raise DriverError(f'Destination port is set {dst_port}.')

    def _check_lidar_mode(self, data):
        # check lidar mode
        mode_idx = int(data['Body']['lidar_mode'])
        table = ['Last Return', 'Strongest Return', 'Dual Return']
        if table[mode_idx] != self.return_mode:
            raise DriverError(f'Lidar mode is set {table[mode_idx]}.')

    def _check_temperature(self, data):
        # check temperature
        temperature = float(data['Body']['CurrentTemp'])
        if temperature < self.min_temperature_threshold or self.max_temperature_threshold < temperature:
            raise DriverError(f'Temperature is out of range. {temperature}℃.')


class AT128(LiDARDriver):
    src_ip: str = 'localhost'
    protocol: str = 'udp'
    dst_ip: str = 'unknown'
    dst_port: int = -1

    spin_rate: int = 400
    return_mode: str = 'unknown'
    max_temperature_threshold: int = 0
    min_temperature_threshold: int = 0

    extrinsic: str = None

    _req_buffer = None
    _pcd_conv = None
    _acquisitor: Acquisitor = None

    def on_start(self, is_init_ref: list, drivers: dict):
        params = {
            'device_ip_address': self.src_ip,
            'udp_port': self.dst_port
        }

        if self.extrinsic:
            params['extrinsic'] = self.parse_extrinsic(self.extrinsic)

        self._req_buffer = ReqBufferAT128({
            'src_ip': self.src_ip,
            'protocol': self.protocol,
            'dst_ip': self.dst_ip,
            'dst_port': self.dst_port,
            'spin_rate': self.spin_rate,
            'return_mode': self.return_mode,
            'max_temperature_threshold': self.max_temperature_threshold,
            'min_temperature_threshold': self.min_temperature_threshold
        }).start()

        self._pcd_conv = AT128PcdConv(params)
        self._pcd_conv.start()

        self._acquisitor = Acquisitor(drivers, self.name)

    def on_stop(self):
        self._acquisitor.stop_acquisition()

        if self._pcd_conv:
            self._pcd_conv.stop()
            self._pcd_conv = None

        if self._req_buffer:
            self._req_buffer.stop()
            self._req_buffer = None

    def pcd(self) -> numpy.ndarray:
        return self._pcd_conv.pcd()

    def check_connection(self) -> ConnState:
        return self._req_buffer.connection()

    def check_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.check_acquisition()

    def start_acquisition(self) -> Tuple[AcqState, str]:
        filter_str = f'src {self.src_ip} and {self.protocol} port {self.dst_port}'
        return self._acquisitor.start_acquisition(filter_str)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.stop_acquisition()

    def check_health(self) -> Tuple[HealthStatus, str]:
        return self._req_buffer.health()
