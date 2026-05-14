import json
from typing import Tuple

from core.Acquisitor import Acquisitor
from core.const import *
from interface import CANDriver
from .fake_recv import FakeReceiver
from .packet_counter import PacketCounter


class AP500CAN(CANDriver):
    local_ip: str = '10.0.0.2'
    local_port: int = 8282
    remote_ip: str = '10.0.0.1'
    remote_port: int = 8282
    use_fake_tcp_reader: bool = False

    _fake_recv: FakeReceiver = None
    _packet_counter: PacketCounter = None
    _acquisitor: Acquisitor = None

    def on_start(self, is_init_ref: list, drivers: dict):
        if self.use_fake_tcp_reader:
            self._fake_recv = FakeReceiver(self.local_ip, self.local_port, self.remote_ip, self.remote_port).start()

        self._packet_counter = PacketCounter(self.remote_ip, self.local_port).start()

        self._acquisitor = Acquisitor(drivers, self.name)

    def on_stop(self):
        self._acquisitor.stop_acquisition()

        if self._packet_counter and self._packet_counter.is_alive():
            self._packet_counter.stop()

        if self._fake_recv and self._fake_recv.is_alive():
            self._fake_recv.stop()

    def check_connection(self) -> ConnState:
        return ConnState.CONNECTED \
            if self._packet_counter and self._packet_counter.bytes_per_sec() > 0 \
            else ConnState.DISCONNECTED

    def snapshot(self) -> Tuple[str, bytes]:
        if self._packet_counter:
            result = {
                "bytes_per_sec": self._packet_counter.bytes_per_sec()
            }
            return 'application/json', json.dumps(result).encode()

        return 'text/plain', b'No packet counter is running.'

    def check_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.check_acquisition()

    def start_acquisition(self) -> Tuple[AcqState, str]:
        filter_str = f'src {self.remote_ip} and tcp port {self.local_port}'
        return self._acquisitor.start_acquisition(filter_str)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        return self._acquisitor.stop_acquisition()
