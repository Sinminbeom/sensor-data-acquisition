import logging
import os
import shutil
import threading
import time
from datetime import datetime
from typing import List

import h5py
import numpy as np

from core import Devices


class StorageError(RuntimeError):
    pass


class NetworkError(RuntimeError):
    pass


# Singleton class
class StorageManager(threading.Thread):
    FREE_SPACE_THRESHOLD = 104857600

    def __init__(self, mount_point: str, on_change: callable = None, on_error: callable = None):
        super().__init__()
        self._mount_point = os.path.normpath(mount_point)

        self._on_change = on_change
        self._on_error = on_error

        self._stop_loop = threading.Event()

    def start(self) -> 'StorageManager':
        super().start()
        return self

    def stop(self):
        self._stop_loop.set()
        self.join()

    def run(self):
        current_storage: str = ''
        try:
            disks = self._mounted_disks()
        except StorageError as e:
            if callable(self._on_error):
                self._on_error(e)
            logging.error(f'Failed to get mounted disks: {e}')
            return

        while not self._stop_loop.is_set():
            try:
                selected_storage = self._select_storage(disks, current_storage)
            except StorageError as e:
                logging.error(e)
                if callable(self._on_error):
                    self._on_error(e)
                break

            if selected_storage != current_storage and callable(self._on_change):
                if self._on_change(selected_storage):
                    current_storage = selected_storage

            time.sleep(5)

    def _mounted_disks(self) -> List[str]:
        try:
            sub_dirs = next(os.walk(self._mount_point))[1]
            return [os.path.join(self._mount_point, _dir) for _dir in sub_dirs]
        except StopIteration:
            raise StorageError(f"Mount point {self._mount_point} is not a directory")

    def _select_storage(self, disks, current_storage) -> str:
        disk_usages = {path: shutil.disk_usage(path).free for path in disks}

        # check prefer exists in disk_usage and has enough free space then use it
        if current_storage in disk_usages and disk_usages[current_storage] >= self.FREE_SPACE_THRESHOLD:
            return current_storage

        max_free_space_path = max(disk_usages, key=disk_usages.get, default='')
        if max_free_space_path and disk_usages[max_free_space_path] < self.FREE_SPACE_THRESHOLD:
            raise StorageError(f"No disk with free space. Maximum free space: {disk_usages[max_free_space_path]} "
                               f"bytes on {max_free_space_path}")

        return max_free_space_path


class ThumbnailLogger(threading.Thread):
    MOUNT_POINT = '/storage'

    INTERVAL = 0.5

    MAX_DATASET_CREATE_RETRY = 3

    def __init__(self, devices: Devices):
        super().__init__()
        self._devices = devices
        self._stop_loop = threading.Event()
        self._thumbnail_file = None

    def stop(self):
        self._stop_loop.set()
        self.join()

    def run(self):
        storage_manager = StorageManager(self.MOUNT_POINT, self.on_storage_change, self.on_storage_error).start()

        while not self._stop_loop.is_set():
            # logging 아니면 1초 대기
            if not self._thumbnail_file:
                time.sleep(1)
                continue

            # frame 처리
            self._process_frame_with_time(self._thumbnail_file)

        self.stop_logging()
        storage_manager.stop()
        logging.info('ThumbnailLogger is stopped.')

    def on_storage_change(self, storage: str) -> bool:
        self.stop_logging()
        try:
            self.start_logging(storage)
            return True
        except Exception as e:
            logging.error(f'Error while changing storage: {e}')
            return False

    def on_storage_error(self, error: StorageError):
        logging.error(f'Storage error: {error}')
        self.stop_logging()

    def start_logging(self, storage: str):
        self._thumbnail_file = h5py.File(self.new_file_path(storage), 'w')

    def stop_logging(self):
        if self._thumbnail_file:
            self._thumbnail_file.close()
            self._thumbnail_file = None

    @staticmethod
    def new_file_path(storage: str) -> str:
        return os.path.join(storage, datetime.now().strftime('thumbnail_%Y%m%d%H%M%S.hdf5'))

    def _process_frame_with_time(self, file):
        start_time = time.time()
        try:
            self._process_frame(file)
        except Exception as e:
            logging.warning(f'Error while processing frame: {e}')
        elapsed_time = time.time() - start_time
        left_time = self.INTERVAL - elapsed_time
        if left_time > 0:
            time.sleep(left_time)
        else:
            logging.warning('ThumbnailLogger is running behind the schedule about %.3f seconds.', -left_time)

    def _process_frame(self, file: h5py.File):
        # timestamp 데이터셋이 없을 경우 생성
        try:
            if 'timestamps' not in file:
                file.create_dataset('timestamps', shape=(0,), maxshape=(None,), dtype='float64')
        except Exception as e:
            logging.error(f'Failed to create timestamps dataset: {e}')
            return

        # 새로운 데이터셋 크기 계산
        ds_timestamps = file['timestamps']
        index = len(ds_timestamps)
        new_size = index + 1

        # 현재 시간 추가
        try:
            timestamp = datetime.now().timestamp()

            ds_timestamps = file['timestamps']
            ds_timestamps.resize((new_size,))
            ds_timestamps[index] = timestamp
        except Exception as e:
            logging.error(f'Failed to add timestamp: {e}')
            return

        # 센서 스냅샷 수집
        snapshots = self._devices.get_all_sensor_snapshot()
        for snapshot in snapshots.list:

            # 센서의 type 데이터셋이 없을 경우 생성
            try:
                if f'{snapshot.name}/type' not in file:
                    file.create_dataset(f'{snapshot.name}/type', shape=(0,), maxshape=(None,),
                                        dtype=h5py.string_dtype(encoding='utf-8'))
            except Exception as e:
                logging.error(f'Failed to create {snapshot.name}/type dataset: {e}')
                continue

            # 센서의 type 추가
            try:
                ds_type = file[f'{snapshot.name}/type']
                ds_type.resize((new_size,))
                ds_type[index] = snapshot.content_type
            except Exception as e:
                logging.error(f'Failed to add type at {snapshot.name}: {e}')
                continue

            # 센서의 data 데이터셋이 없을 경우 생성
            try:
                if f'{snapshot.name}/data' not in file:
                    file.create_dataset(f'{snapshot.name}/data', shape=(0,), maxshape=(None,),
                                        dtype=h5py.vlen_dtype(np.dtype('uint8')))
            except Exception as e:
                logging.error(f'Failed to create {snapshot.name}/data dataset: {e}')
                continue

            # 센서의 data 추가
            try:
                ds_data = file[f'{snapshot.name}/data']
                ds_data.resize((new_size,))
                ds_data[index] = np.frombuffer(snapshot.data, dtype='uint8')
            except Exception as e:
                logging.error(f'Failed to add data at {snapshot.name}: {e}')

        file.flush()

    def add_voice_tag(self, timestamp: int, voice: bytes):
        # TODO
        logging.info(f'Voice tag added at {timestamp}')
        pass
