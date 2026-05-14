import threading

from scapy.all import *


class PacketCounter(threading.Thread):
    lock = threading.Lock()
    total_bytes: int = 0

    def __init__(self, src_ip: str, dst_port: int):
        super().__init__()
        self.src_ip = src_ip
        self.dst_port = dst_port
        self.event = threading.Event()

    def start(self) -> 'PacketCounter':
        super().start()
        return self

    def run(self):
        packet_filter = f'src host {self.src_ip} and tcp port {self.dst_port}'

        while not self.event.is_set():
            sniffed = sniff(iface=get_if_list(), filter=packet_filter, timeout=1)
            with self.lock:
                self.total_bytes = sum(len(packet) for packet in sniffed)

    def stop(self):
        self.event.set()
        self.join()

    def bytes_per_sec(self) -> int:
        with self.lock:
            return self.total_bytes
