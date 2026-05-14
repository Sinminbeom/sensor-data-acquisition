import json
import logging
import os
import shutil
import threading
import time
from typing import Tuple

from core.const import ConnState
from interface import StorageDriver, DriverError


class ReqBufferStorage(threading.Thread):
    def __init__(self, config: dict):
        super().__init__()
        self._loop_stop = threading.Event()

        self.mount_point = config['mount_point']
        self.free_space_threshold = config['free_space_threshold']

        self._disk_usages_lock = threading.Lock()
        self._disk_usages: dict = {}

        self._connection_lock = threading.Lock()
        self._connection: ConnState = ConnState.UNKNOWN

        self._snapshot_lock = threading.Lock()
        self._snapshot: Tuple[str, bytes] = ('text/plain', b'Not initialized.')

        self._recommend_lock = threading.Lock()
        self._recommend: str = ''

    def start(self) -> 'ReqBufferStorage':
        super().start()
        return self

    def stop(self):
        self._loop_stop.set()
        self.join()

    def run(self):
        while not self._loop_stop.is_set():
            try:
                disks = self._get_mounted_disks()
            except DriverError as e:
                with self._connection_lock:
                    self._connection = ConnState.DISCONNECTED
                with self._snapshot_lock:
                    self._snapshot = 'text/plain', str(e).encode()
                with self._recommend_lock:
                    self._recommend = ''
                time.sleep(1)
                continue

            self._check_connection(disks)

            try:
                disk_usages = {disk: shutil.disk_usage(disk) for disk in disks}
            except DriverError as e:
                with self._snapshot_lock:
                    self._snapshot = 'text/plain', str(e).encode()
                with self._recommend_lock:
                    self._recommend = ''
                time.sleep(1)
                continue

            self._generate_snapshot(disk_usages)
            self._recommend_storage(disk_usages)

            with self._disk_usages_lock:
                self._disk_usages = disk_usages

            time.sleep(1)

    def connection(self) -> ConnState:
        with self._connection_lock:
            return self._connection

    def snapshot(self) -> Tuple[str, bytes]:
        with self._snapshot_lock:
            return self._snapshot

    def recommend_storage(self, prefer) -> str:
        with self._disk_usages_lock:
            disk_usages = self._disk_usages

        if prefer in disk_usages and disk_usages[prefer].free >= self.free_space_threshold:
            return prefer

        with self._recommend_lock:
            return self._recommend

    def _check_connection(self, disks):
        with self._connection_lock:
            self._connection = ConnState.DISCONNECTED if len(disks) == 0 else ConnState.CONNECTED

    def _generate_snapshot(self, disk_usages: dict):
        result = {
            "total": sum(usage.total for usage in disk_usages.values()),
            "used": sum(usage.used for usage in disk_usages.values()),
            "free": sum(usage.free for usage in disk_usages.values())
        }
        with self._snapshot_lock:
            self._snapshot = 'application/json', json.dumps(result).encode()

    def _recommend_storage(self, disk_usages: dict):
        max_free_space_path = max(disk_usages, key=lambda x: disk_usages[x].free, default='')

        with self._recommend_lock:
            if max_free_space_path and disk_usages[max_free_space_path].free < self.free_space_threshold:
                self._recommend = ''
            else:
                self._recommend = max_free_space_path

    ###################################################################
    # Private methods

    def _get_mounted_disks(self):
        try:
            sub_dirs = next(os.walk(self.mount_point))[1]
            return [os.path.join(self.mount_point, _dir) for _dir in sub_dirs]
        except StopIteration:
            raise DriverError(f"Mount point {self.mount_point} is not a directory")


class Storage(StorageDriver):
    mount_point: str = '/storage'
    free_space_threshold: int = 0

    _req_buffer = None

    def on_start(self, is_init_ref: list, drivers: dict):
        self.mount_point = os.path.normpath(self.mount_point) + os.sep

        self._req_buffer = ReqBufferStorage({
            'mount_point': self.mount_point,
            'free_space_threshold': self.free_space_threshold
        }).start()

    def on_stop(self):
        if self._req_buffer:
            self._req_buffer.stop()
            self._req_buffer = None

    def check_connection(self) -> ConnState:
        return self._req_buffer.connection()

    def snapshot(self) -> Tuple[str, bytes]:
        return self._req_buffer.snapshot()

    def recommend_storage(self, prefer) -> str:
        return self._req_buffer.recommend_storage(os.path.normpath(prefer))


def sizeof_fmt(num, suffix='B'):
    """Readable file size
    :param num: Bytes value
    :type num: int
    :param suffix: Unit suffix (optional) default = o
    :type suffix: str
    :rtype: str
    """
    for unit in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    storage = Storage()
    storage.on_start([True], {})

    time.sleep(1)

    connection_state = storage.check_connection()
    print(connection_state)

    _, data = storage.snapshot()
    json_data = json.loads(data)

    json_data['total'] = sizeof_fmt(json_data['total'])
    json_data['used'] = sizeof_fmt(json_data['used'])
    json_data['free'] = sizeof_fmt(json_data['free'])

    print(json_data)

    storage.on_stop()
