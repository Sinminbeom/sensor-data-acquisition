# noinspection PyUnresolvedReferences
from typing import Tuple

import numpy
import requests
from bs4 import BeautifulSoup
from scapy.all import *

from core.Acquisitor import Acquisitor
from core.const import *
from interface import LiDARDriver, DriverError
from .pcd_conv import RSBPPcdConv


class ReqBufferRSBP(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.sniff_timeout = 1
        self.call_timeout = 2

        self.src_ip = config['src_ip']
        self.protocol = config['protocol']
        self.dst_ip = config['dst_ip']
        self.dst_port = config['dst_port']
        self.difop_port = config['difop_port']
        self.ret_mode = config['ret_mode']
        self.rpm = config['rpm']

        self._connection_lock = threading.Lock()
        self._connection: ConnState = ConnState.UNKNOWN

        self._health_lock = threading.Lock()
        self._health: Tuple[HealthStatus, str] = (HealthStatus.UNKNOWN, '')

    def start(self) -> 'ReqBufferRSBP':
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
            setting = self._get_lidar_setting()
            self._check_setting(setting)

            diagnostic_info = self._get_lidar_diagnostic_info()
            self._check_diagnostic_info(diagnostic_info)

            with self._health_lock:
                self._health = HealthStatus.GOOD, ''

        except DriverError as e:
            with self._health_lock:
                self._health = HealthStatus.BAAD, str(e)

    ###################################################################
    # Private methods

    def _get_lidar_setting(self):
        # http://192.168.20.110/cgi-bin/param_setting.cgi
        # noinspection HttpUrlsUsage
        return self._get_data_from_url(f'http://{self.src_ip}/cgi-bin/param_setting.cgi')

    def _get_lidar_diagnostic_info(self):
        # http://192.168.20.110/cgi-bin/diagnostic_info.cgi
        # noinspection HttpUrlsUsage
        return self._get_data_from_url(f'http://{self.src_ip}/cgi-bin/diagnostic_info.cgi')

    def _get_data_from_url(self, url):
        try:
            response = requests.get(url, timeout=self.call_timeout)
        except requests.exceptions.RequestException as e:
            raise DriverError(f'Failed to connect to {url}') from e

        if response.status_code != 200:
            raise DriverError(f'Failed to connect to {url}')
        return response.text

    def _check_setting(self, setting):
        soup = BeautifulSoup(setting, 'html.parser')

        self._check_destination(soup)
        self._check_msop_port(soup)
        self._check_difop_port(soup)
        self._check_return_mode(soup)

    def _check_diagnostic_info(self, diagnostic_info):
        soup = BeautifulSoup(diagnostic_info, 'html.parser')

        self._check_rpm(soup)
        self._check_laser_state(soup)
        self._check_ptp_status(soup)

    def _check_destination(self, soup):
        # des_ip_addr 추출 및 비교
        des_ip_addr = soup.find('input', {'name': 'des_ip_addr'})['value']
        if self.dst_ip != des_ip_addr:
            raise DriverError(f'Destination IP address mismatch: {self.dst_ip} != {des_ip_addr}')

    def _check_msop_port(self, soup):
        # MSOP Port Number 추출 및 비교
        lidar_msop_port = int(soup.find('input', {'name': 'lidar_msop_port'})['value'])
        if self.dst_port != lidar_msop_port:
            raise DriverError(f'MSOP Port Number mismatch: {self.dst_port} != {lidar_msop_port}')

    def _check_difop_port(self, soup):
        # DIFOP Port Number 추출 및 비교
        lidar_difop_port = int(soup.find('input', {'name': 'lidar_difop_port'})['value'])
        if self.difop_port != lidar_difop_port:
            raise DriverError(f'DIFOP Port Number mismatch: {self.difop_port} != {lidar_difop_port}')

    def _check_return_mode(self, soup):
        # Return Mode 추출 및 비교 (Strong, Dual, Last) <select name="RetModeSel" />
        ret_mode_select = soup.find('select', {'name': 'RetModeSel'})
        # selected option 추출
        selected_option = ret_mode_select.find('option', {'selected': True})['value']
        if self.ret_mode != selected_option:
            raise DriverError(f'Return Mode mismatch: {self.ret_mode} != {selected_option}')

    def _check_rpm(self, soup):
        rpm = int(soup.find('input', {'name': 'rpm_text'})['value'])
        if self.rpm != rpm:
            raise DriverError(f'Rotation Speed mismatch: {self.rpm} != {rpm}')

    @staticmethod
    def _check_laser_state(soup):
        # Laser Status 추출 및 비교
        laser_state = soup.find('input', {'name': 'laser_state_text'})['value']
        if laser_state != 'ON':
            raise DriverError(f'Laser is not ON: {laser_state}')

    @staticmethod
    def _check_ptp_status(soup):
        ptp_status = soup.find('input', {'name': 'ptp_remote_sync_status_text'})['value']
        if not ptp_status.startswith('Locked'):
            raise DriverError(f'PTP is not locked: {ptp_status}')


class RSBP(LiDARDriver):
    src_ip: str = 'localhost'
    protocol: str = 'udp'
    dst_ip: str = 'localhost'
    dst_port: int = -1
    difop_port: int = -1

    ret_mode: str = 'Strong'
    rpm: int = 600

    extrinsic: str = None

    _req_buffer = None
    _pcd_conv = None
    _acquisitor: Acquisitor = None

    def on_start(self, is_init_ref: list, drivers: dict):
        params = {
            'msop_port': self.dst_port,
            'difop_port': self.difop_port,
        }

        if self.extrinsic:
            params['extrinsic'] = self._conv_ap500_extrinsic(self.parse_extrinsic(self.extrinsic))

        self._req_buffer = ReqBufferRSBP({
            'src_ip': self.src_ip,
            'protocol': self.protocol,
            'dst_ip': self.dst_ip,
            'dst_port': self.dst_port,
            'difop_port': self.difop_port,
            'ret_mode': self.ret_mode,
            'rpm': self.rpm
        }).start()

        self._pcd_conv = RSBPPcdConv(params)
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
        filter_str = f'src {self.src_ip} and {self.protocol} port {self.dst_port} or {self.difop_port}'
        return self._acquisitor.start_acquisition(filter_str)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.stop_acquisition()

    def check_health(self) -> Tuple[HealthStatus, str]:
        return self._req_buffer.health()

    @staticmethod
    def _conv_ap500_extrinsic(extrinsic: dict) -> dict:
        x = extrinsic['x']
        y = extrinsic['y']
        z = extrinsic['z']
        yaw = extrinsic['yaw']
        roll = extrinsic['roll']
        pitch = extrinsic['pitch']

        conv_extrinsic = {
            'x': x,
            'y': y,
            'z': z,
            'yaw': pitch,
            'roll': yaw + math.radians(90),
            'pitch': -roll,
        }
        return conv_extrinsic
