import logging
import socket
import threading


class FakeReceiver(threading.Thread):
    """
    FakeDriverBynavX1은 BynavX1 장비의 가상 드라이버.
    설정된 data port로 들어오는 데이터를 수신하여, 드라이버가 packet을 수집할 수 있도록 한다.
    또한 설정된 NTRIP 서버로부터 RTCM 데이터를 수신하여, BynavX1 장비로 전송한다.
    """

    def __init__(self, ip: str, port: int):
        super().__init__()
        self.addr = (ip, port)
        self.socket = None
        self.event = threading.Event()

    def run(self):
        buffer_size = 1024 * 1024

        while not self.event.is_set():
            if not self.socket:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 1초 동안 응답이 없으면 timeout
                self.socket.settimeout(1)
                try:
                    self.socket.connect(self.addr)
                    logging.info(f'FakeReceiver connected to {self.addr}')

                except Exception as e:
                    logging.warning(f'FakeReceiver failed to connect to {self.addr} - {e}')
                    self.socket = None
                    continue

            try:
                # 동일하게 timeout이 적용됨
                self.socket.recv(buffer_size)
            except socket.timeout:
                self.socket.close()
                self.socket = None
                logging.info(f'FakeReceiver disconnected from {self.addr}')

        self.socket.close()
        logging.info(f'FakeReceiver disconnected from {self.addr}')

    def stop(self):
        self.event.set()
        self.join()
