import os
from typing import Tuple

from core.const import *
from drivers.SWM100FHD.gst_pipe import GstPipe
from interface import DriverError, RealCamDriver


class SWM100FHD(RealCamDriver):
    name: str = 'unknown'
    dev_num: int = -1
    dst_ip: str = ''
    dst_port: int = -1
    protocol: str = 'udp'
    thumbnail_width: int = 640
    thumbnail_height: int = 360

    _gst_pipe: GstPipe = None

    def on_start(self, is_init_ref: list, drivers: dict):
        if ConnState.CONNECTED != self.check_connection():
            raise DriverError(
                f'Connection is not established: /dev/video{self.dev_num} which is named \'{self.name}\'')
        self._gst_pipe = GstPipe(self.name, self.dev_num, self.protocol, self.dst_ip, self.dst_port,
                                 (self.thumbnail_width, self.thumbnail_height))
        self._gst_pipe.start()

    def on_stop(self):
        if self._gst_pipe:
            self._gst_pipe.stop()

    def check_connection(self) -> ConnState:
        try:
            self._check_serialize_channel(self.dev_num)
            self._check_deserialize_link(self.dev_num)
            self._check_serialize_pipeline(self.dev_num)
            return ConnState.CONNECTED
        except DriverError:
            return ConnState.DISCONNECTED

    def snapshot(self) -> Tuple[str, bytes]:
        return self._gst_pipe.snapshot()

    ###################################################################
    # Private methods

    @staticmethod
    def _check_file_locked(file_path: str):
        with open(file_path, 'r') as f:
            if not f.read().startswith('locked'):
                raise DriverError(f'Device is not locked. {file_path}')

    def _check_serialize_channel(self, dev_num: int):
        if dev_num < 0 or 3 < dev_num:
            raise DriverError('Invalid device number')
        table = [
            '/sys/bus/i2c/drivers/max9296t/0-0048/channellock_x',
            '/sys/bus/i2c/drivers/max9296t/0-0048/channellock_y',
            '/sys/bus/i2c/drivers/max9296t/8-0048/channellock_x',
            '/sys/bus/i2c/drivers/max9296t/8-0048/channellock_y'
        ]
        device = table[dev_num]
        if not os.path.exists(device):
            raise DriverError(f'Device channel lock file is not found. {device}')
        self._check_file_locked(device)

    def _check_deserialize_link(self, dev_num: int):
        if dev_num < 0 or 3 < dev_num:
            raise DriverError('Invalid device number')
        table = [
            '/sys/bus/i2c/drivers/max9296t/0-0048/linklock',
            '/sys/bus/i2c/drivers/max9296t/0-0048/linklock',
            '/sys/bus/i2c/drivers/max9296t/8-0048/linklock',
            '/sys/bus/i2c/drivers/max9296t/8-0048/linklock'
        ]
        device = table[dev_num]
        if not os.path.exists(device):
            raise DriverError(f'Device link lock file is not found. {device}')
        self._check_file_locked(device)

    def _check_serialize_pipeline(self, dev_num: int):
        if dev_num < 0 or 3 < dev_num:
            raise DriverError('Invalid device number')
        table = [
            '/sys/bus/i2c/drivers/max9296t/0-0048/pipelinelock_x',
            '/sys/bus/i2c/drivers/max9296t/0-0048/pipelinelock_y',
            '/sys/bus/i2c/drivers/max9296t/8-0048/pipelinelock_x',
            '/sys/bus/i2c/drivers/max9296t/8-0048/pipelinelock_y'
        ]
        device = table[dev_num]
        if not os.path.exists(device):
            raise DriverError(f'Device pipeline lock file is not found. {device}')
        self._check_file_locked(device)
