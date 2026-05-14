import logging
import sys
from os import environ

from PyQt5.QtWidgets import QApplication

from window import MainWindow


def set_auto_screen_scale():
    environ["QT_DEVICE_PIXEL_RATIO"] = "0"
    environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    environ["QT_SCALE_FACTOR"] = "1"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = QApplication([])
    window = MainWindow()
    window.show()
    code = app.exec()
    window.on_close()
    sys.exit(code)
