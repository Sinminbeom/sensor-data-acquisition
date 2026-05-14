import time
from typing import Tuple

from core.TcpDump import TcpDump
from core.const import AcqState


class Acquisitor:
    drivers: dict = None
    name: str = 'unknown'
    tcpdump = None

    def __init__(self, drivers: dict, name: str):
        self.drivers = drivers
        self.name = name

    def __del__(self):
        if self.tcpdump:
            self.tcpdump.stop()

    def check_acquisition(self) -> Tuple[AcqState, str]:
        if not self.tcpdump:
            return AcqState.NOT_ACQUIRING, ''
        return self.tcpdump.state(), ''

    def start_acquisition(self, filter_str: str) -> Tuple[AcqState, str]:
        if self.tcpdump:
            return self.tcpdump.state(), 'Already acquiring.'

        try:
            self.tcpdump = TcpDump(self.drivers, self.name, filter_str, self.on_stopped).start()
            while self.tcpdump.state() == AcqState.UNKNOWN:
                time.sleep(0.01)
            return self.tcpdump.state(), ''
        except Exception as e:
            return AcqState.NOT_ACQUIRING, str(e)

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        if self.tcpdump:
            self.tcpdump.stop()
            self.tcpdump = None
        return AcqState.NOT_ACQUIRING, ''

    def on_stopped(self):
        if self.tcpdump:
            self.tcpdump = None
