from scapy.all import *

from core.Acquisitor import Acquisitor
from core.const import *
from interface import NetCamDriver


class ReqBufferNetCamera(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.sniff_timeout = 1

        self.src_ip = config['src_ip']
        self.protocol = config['protocol']
        self.dst_port = config['dst_port']

        self._health_lock = threading.Lock()
        self._health: Tuple[HealthStatus, str] = (HealthStatus.UNKNOWN, '')

    def start(self) -> 'ReqBufferNetCamera':
        super().start()
        return self

    def stop(self):
        self._loop_stop.set()
        self.join()

    def run(self):
        while not self._loop_stop.is_set():
            self._check_health()
            time.sleep(1)

    def health(self) -> Tuple[HealthStatus, str]:
        with self._health_lock:
            return self._health

    def _check_health(self):
        packet_filter = f'src host {self.src_ip} and {self.protocol} port {self.dst_port}'
        sniffed = sniff(iface=get_if_list(), filter=packet_filter, count=1, timeout=self.sniff_timeout)
        with self._health_lock:
            self._health = (HealthStatus.GOOD, '') if sniffed else (HealthStatus.BAAD, 'No packet arrived.')


class NetCamera(NetCamDriver):
    src_ip: str = 'localhost'
    protocol: str = 'udp'
    dst_port: int = -1
    sniff_timeout: float = 0.3

    _req_buffer = None
    _acquisitor: Acquisitor = None

    def on_start(self, is_init_ref: list, drivers: dict):
        self._req_buffer = ReqBufferNetCamera({
            'src_ip': self.src_ip,
            'protocol': self.protocol,
            'dst_port': self.dst_port
        }).start()

        self._acquisitor = Acquisitor(drivers, self.name)

    def on_stop(self):
        self._acquisitor.stop_acquisition()

        if self._req_buffer:
            self._req_buffer.stop()
            self._req_buffer = None

    def check_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.check_acquisition()

    def start_acquisition(self) -> Tuple[AcqState, str]:
        filter_str = f'src {self.src_ip} and {self.protocol} port {self.dst_port}'
        return self._acquisitor.start_acquisition(filter_str)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.stop_acquisition()

    def check_health(self) -> Tuple[HealthStatus, str]:
        return self._req_buffer.health()
