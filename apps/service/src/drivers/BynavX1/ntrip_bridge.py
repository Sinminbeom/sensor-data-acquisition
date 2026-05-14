import base64
import logging
import socket
import threading
import time

import select

from interface import DriverError


class RtkReader:
    """
    NTRIP 서버로부터 RTCM 데이터를 수신하는 클래스
    """

    def __init__(self, config: dict):
        if 'ip' not in config:
            raise ValueError('ip is required in from config.')
        self.ip = config['ip']

        if 'port' not in config:
            raise ValueError('port is required in from config.')
        self.port = config['port']

        if 'mount_point' not in config:
            raise ValueError('mount_point is required in from config.')
        mount_point = config['mount_point']

        if 'user' not in config:
            raise ValueError('user is required in from config.')
        user = config['user']

        if 'password' not in config:
            raise ValueError('password is required in from config.')
        password = config['password']

        auth_id_pw = base64.b64encode(f"{user}:{password}".encode())
        auth_str = (f"GET /{mount_point} "
                    f"HTTP/1.0\r\n "
                    f"User-Agent: NTRIP gnss_driver/0.0\r\n "
                    f"accept: */* \r\n "
                    f"Authorization: Basic {auth_id_pw} \r\n\r\n")

        self.auth_info: bytes = bytes(auth_str, 'utf-8')

        self.socket_timeout = config.get('socket_timeout', 5)
        self.read_retry = config.get('read_retry', 6)

        self._socket = None

    def read(self) -> bytes:
        buffer_size = 1024 * 1024
        # socket 이 연결 되어 있지 않다면 연결
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.socket_timeout)
            try:
                self._socket.connect((self.ip, self.port))
                cur_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
                logging.info(f'NTRIP connected to {self.ip}:{self.port} at {cur_time}')

            except Exception as e:
                logging.error(f'NTRIP failed to connect to {self.ip}:{self.port} - {e}')
                self._socket = None
                return b''

            try:
                self._login()
            except DriverError as e:
                logging.error(f'NTRIP failed to login: {e}')
                return self._close()

        try:
            retry_count = 0
            while True:
                ready_to_read, _ = self._select()
                if ready_to_read:
                    return self._socket.recv(buffer_size)
                else:
                    if retry_count > self.read_retry:
                        return self._close()
                    retry_count += 1
                    time.sleep(1)

        except select.error:
            return self._close()

    def _login(self):
        buffer_size = 1024 * 1024

        # 로그인 요청
        try:
            _, ready_to_write = self._select()
            if ready_to_write:
                self._socket.sendall(self.auth_info)
            else:
                time.sleep(1)

        except select.error:
            raise DriverError('Login request connection failed')

        # 로그인 응답
        try:
            ready_to_read, _ = self._select()
            if ready_to_read:
                data = self._socket.recv(buffer_size)

                # 로그인 성공시 'ICY 200 OK' 메시지 수신
                if b'ICY 200 OK' in data:
                    return

                # 마운트 포인트를 찾을 수 없을 경우 에러 발생
                if b'SOURCETABLE 200 OK' in data:
                    raise DriverError('Mount point not found')

                # 인증 실패시 에러 발생
                if b'HTTP/' in data:
                    raise DriverError('Authentication failed')
            else:
                time.sleep(1)

        except select.error:
            raise DriverError('Login response connection failed')

    def _select(self) -> (bool, bool):
        ready_to_read, ready_to_write, in_error = \
            select.select([self._socket, ], [self._socket, ], [], 1)
        return len(ready_to_read) > 0, len(ready_to_write) > 0

    def _close(self) -> bytes:
        cur_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        logging.info(f'NTRIP disconnected from {self.ip}:{self.port} at {cur_time}')
        self._socket.shutdown(2)  # 0 = done receiving, 1 = done sending, 2 = both
        self._socket.close()
        self._socket = None
        self._retry = 0
        return b''


class RtkWriter:
    """
    RTCM 데이터를 장비로 전송하는 클래스
    """

    def __init__(self, config: dict):
        if 'ip' not in config:
            raise ValueError('ip is required in from config.')
        self.ip = config['ip']

        if 'port' not in config:
            raise ValueError('port is required in from config.')
        self.port = config['port']

        self._socket = None

    def write(self, data: bytes) -> None:
        if not data:
            return

        # socket 이 연결 되어 있지 않다면 연결
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(1)
            try:
                self._socket.connect((self.ip, self.port))
                logging.info(f'BynavX1 connected to {self.ip}:{self.port}')

            except Exception as e:
                logging.error(f'BynavX1 failed to connect to {self.ip}:{self.port} - {e}')
                self._socket = None
                return

        try:
            _, ready_to_write = self._select()
            if ready_to_write:
                self._socket.sendall(data)

        except select.error:
            self._close()

    def _select(self) -> (bool, bool):
        ready_to_read, ready_to_write, in_error = \
            select.select([self._socket, ], [self._socket, ], [], 1)
        return len(ready_to_read) > 0, len(ready_to_write) > 0

    def _close(self):
        logging.info(f'BynavX1 disconnected from {self.ip}:{self.port}')
        self._socket.shutdown(2)  # 0 = done receiving, 1 = done sending, 2 = both
        self._socket.close()
        self._socket = None


class NtripBridge(threading.Thread):
    def __init__(self, from_config: dict, to_config: dict):
        super().__init__()
        self.event = threading.Event()
        self.reader = RtkReader(from_config)
        self.writer = RtkWriter(to_config)

    def run(self):
        while not self.event.is_set():
            self.writer.write(self.reader.read())
        logging.info('NtripBridge stopped')

    def stop(self):
        self.event.set()
        self.join()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    from_config = {
        "ip": "115.84.164.202",
        "port": 2101,
        "mount_point": "YONS-RTCM32-M5",
        "user": "seoul",
        "password": "seoul",
        "timeout_s": 5
    }
    to_config = {
        "ip": "192.168.20.50",
        "port": 2222
    }

    bridge = NtripBridge(from_config, to_config)
    bridge.start()
    while True:
        time.sleep(1)
