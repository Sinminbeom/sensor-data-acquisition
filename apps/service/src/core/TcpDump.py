import logging
import os
import subprocess
import threading
import time
from datetime import datetime

from core.const import AcqState
from interface import DriverError


class TcpDump(threading.Thread):
    def __init__(self, drivers: dict, dev_name: str, filter_str: str, on_stopped: callable = None):
        super().__init__()
        self._storage = drivers['storage']

        self._dev_name = dev_name
        self._filter_str = filter_str
        self._on_stopped = on_stopped

        self._event = threading.Event()

        self._acq_state_lock = threading.Lock()
        self._acq_state = AcqState.UNKNOWN
        self._process = None
        self._current_storage: str = ''

    def run(self):
        while not self._event.is_set():
            try:
                selected_path = self._select_storage(self._current_storage)
            except Exception as e:
                logging.error(f'No storage available - {e}')
                with self._acq_state_lock:
                    self._acq_state = AcqState.NOT_ACQUIRING
                break

            if selected_path != self._current_storage:
                self._stop_dump()
                self._start_dump(selected_path)
                if self.state() == AcqState.NOT_ACQUIRING:
                    break

            time.sleep(1)

        self._stop_dump()
        if callable(self._on_stopped):
            self._on_stopped()

    def start(self) -> 'TcpDump':
        super().start()
        return self

    def stop(self) -> None:
        self._event.set()
        self.join()

    def state(self) -> AcqState:
        with self._acq_state_lock:
            return self._acq_state

    ###################################################################
    # Private methods

    def _select_storage(self, prefer) -> str:
        return self._storage.recommend_storage(prefer)

    def _start_dump(self, selected_storage: str) -> None:
        selected_path = self._mkpath(selected_storage)
        file_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
        command = f'tcpdump -i any -w "{selected_path}/{self._dev_name}_{file_datetime}.pcap" "{self._filter_str}"'
        try:
            self._process = subprocess.Popen('exec ' + command, stdout=subprocess.PIPE, shell=True)
            # wait for process to start.
            time.sleep(0.1)
            # check if process is still running.
            if self._process.poll() is not None:
                self._process.wait()
                self._process = None
                with self._acq_state_lock:
                    self._acq_state = AcqState.NOT_ACQUIRING
                raise DriverError('Failed to start process')

            self._current_storage = selected_storage
            with self._acq_state_lock:
                self._acq_state = AcqState.ACQUIRING

        except Exception as e:
            logging.error(f'Failed to start tcpdump - {e}')

    def _stop_dump(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                while self._process.poll() is None:
                    time.sleep(0.1)
                with self._acq_state_lock:
                    self._acq_state = AcqState.NOT_ACQUIRING

            except Exception as e:
                logging.error(f'Failed to stop tcpdump - {e}')

    @staticmethod
    def _mkpath(selected_storage):
        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%Y%m%d')
        vehicle_id = os.getenv('VEHICLE_ID', 'T-CAR')

        path = f'{selected_storage}/{formatted_date}/{vehicle_id}'
        os.makedirs(path, exist_ok=True)

        return path
