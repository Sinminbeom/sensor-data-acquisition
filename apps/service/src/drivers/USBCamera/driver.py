import os
from typing import Tuple

from core.const import *
from drivers.SWM100FHD.gst_pipe import IGstPipe
from drivers.SWM100FHD.gst_pipe_cpu import GstPipeCpu
from interface import DriverError, LocalCamDriver


class USBCamera(LocalCamDriver):
    name: str = 'unknown'
    dev_num: int = -1
    dst_ip: str = ''
    dst_port: int = -1
    protocol: str = 'udp'
    thumbnail_width: int = 640
    thumbnail_height: int = 360

    _gst_pipe: IGstPipe = None

    def on_start(self, is_init_ref: list, drivers: dict):
        if ConnState.CONNECTED != self.check_connection():
            raise DriverError(
                f'Connection is not established: /dev/video{self.dev_num} which is named \'{self.name}\'')

    def on_stop(self):
        if self._gst_pipe:
            self._gst_pipe.stop()
            self._gst_pipe = None

    def check_connection(self) -> ConnState:
        if os.path.exists(f'/dev/video{self.dev_num}'):
            return ConnState.CONNECTED
        return ConnState.DISCONNECTED

    def snapshot(self) -> Tuple[str, bytes]:
        if self._gst_pipe is None:
            return 'text/plain', b'Acquisition has not started.'
        return self._gst_pipe.snapshot()

    def check_acquisition(self) -> Tuple[AcqState, str]:
        if self._gst_pipe is not None and self._gst_pipe.is_alive():
            return AcqState.ACQUIRING, ''
        return AcqState.NOT_ACQUIRING, ''

    def start_acquisition(self) -> Tuple[AcqState, str]:
        if self._gst_pipe is not None and self._gst_pipe.is_alive():
            return AcqState.ACQUIRING, 'Already acquiring.'
        self._gst_pipe = GstPipeCpu(self.name, self.dev_num, self.protocol, self.dst_ip, self.dst_port,
                                    (self.thumbnail_width, self.thumbnail_height))
        self._gst_pipe.start()
        return AcqState.ACQUIRING, ''

    def stop_acquisition(self) -> Tuple[AcqState, str]:
        if self._gst_pipe is None:
            return AcqState.NOT_ACQUIRING, 'Already not acquiring.'
        self._gst_pipe.stop()
        self._gst_pipe = None
        return AcqState.NOT_ACQUIRING, ''
