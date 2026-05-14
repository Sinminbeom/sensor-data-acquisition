import socket
import threading


class FakeReceiver(threading.Thread):
    def __init__(self, local_ip: str, local_port: int, remote_ip: str, remote_port: int):
        super().__init__()
        self.local_addr = (local_ip, local_port)
        self.remote_addr = (remote_ip, remote_port)
        self.socket = None
        self.event = threading.Event()

    def start(self) -> 'FakeReceiver':
        super().start()
        return self

    def stop(self):
        self.event.set()
        self.join()

    def run(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(self.local_addr)
        server_sock.listen(1)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_sock.connect(self.remote_addr)

        client_sock = None
        try:
            while not self.event.is_set():
                if not client_sock:
                    client_sock, _ = server_sock.accept()

                client_sock.recv(1024)
        finally:
            client_sock.close()
            send_sock.close()
            server_sock.close()
