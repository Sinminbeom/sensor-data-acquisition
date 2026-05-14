import threading
import time

import numpy

from drivers.RSBP.rsbp_converter import RSBPConverter  # type: ignore
from interface import IPcdGettable


class RSBPPcdConv(IPcdGettable, threading.Thread):
    def __init__(self, params: dict):
        super().__init__()
        self.event = threading.Event()
        self.converter = RSBPConverter(params)

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
        'msop_port': 6701,
        'difop_port': 7789,
        'min_distance': 0,
        'max_distance': 200,
        'start_angle': 0,
        'end_angle': 360,
    }
    pcd_conv = RSBPPcdConv(params)
    pcd_conv.start()

    counter = 0
    while True:
        if counter == 20:
            break
        time.sleep(0.1)
        pcd = pcd_conv.pcd()
        pcd_conv.debug_render(f'./tmp/rsbp_{counter}.png', pcd)
        counter += 1

    pcd_conv.stop()
