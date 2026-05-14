import threading
import time

import numpy

from drivers.AT128.at128_converter import At128Converter  # type: ignore
from interface import IPcdGettable


class AT128PcdConv(IPcdGettable, threading.Thread):
    def __init__(self, params: dict):
        super().__init__()
        self.event = threading.Event()
        self.converter = At128Converter(params)

    def run(self):
        self.converter.start()
        while not self.event.is_set():
            time.sleep(1)

    def stop(self):
        self.converter.stop()
        self.event.set()
        self.join()

    def pcd(self) -> numpy.ndarray:
        # x, y, z, r, g, b
        return self.converter.snapshot_pcd().reshape(-1, 6)


if __name__ == '__main__':
    params = {
        'device_ip_address': '192.168.20.201',
        'udp_port': 2361,
    }
    pcd_conv = AT128PcdConv(params)
    pcd_conv.start()

    counter = 0
    while True:
        if counter == 20:
            break
        time.sleep(0.1)
        pcd = pcd_conv.pcd()
        pcd_conv.debug_render(f'./tmp/at128_{counter}.png', pcd)
        counter += 1

    pcd_conv.stop()
