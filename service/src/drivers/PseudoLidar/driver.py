from typing import Tuple

from drivers.PseudoLidar.renderer import PseudoLidarRenderer
from interface.IDriver import IDriver
from interface.IShapshotable import ISnapshotable


class PseudoLidar(IDriver, ISnapshotable):
    image_width: int = 800
    image_height: int = 800
    zFar: float = 70

    renderer: PseudoLidarRenderer = None

    def on_start(self, is_init_ref: list, drivers: dict):
        self.renderer = PseudoLidarRenderer(is_init_ref, drivers, self.image_width, self.image_height, self.zFar).start()

    def on_stop(self):
        self.renderer.stop()

    def snapshot(self) -> Tuple[str, bytes]:
        try:
            return 'image/png', self.renderer.snapshot()
        except Exception as e:
            return 'exception', str(e).encode()
