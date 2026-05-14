from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel

from dbg_flag import CAM
from image_invorker import ImageInvoker


class MainWindow(QMainWindow):
    label = None

    def __init__(self):
        super().__init__()
        # self.setupUi(self)
        self.pixmap = QPixmap()
        self.image = None
        self.init_ui()
        self.image_invoker = ImageInvoker(0.1).open(self.on_png)

    def init_ui(self):
        self.setWindowTitle("Image Viewer")
        self.resize(800, 800)

        # Create a QLabel for image display
        self.label = QLabel(self)
        self.label.resize(800, 800)

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        timer.timeout.connect(self.update_image)
        timer.start(10)

    def on_close(self):
        self.image_invoker.close()

    def on_png(self, image):
        try:
            if CAM:
                self.pixmap.loadFromData(image, 'JPEG')
            else:
                self.pixmap.loadFromData(image, 'PNG')
        except Exception as e:
            print(e)

    def update_image(self):
        self.label.setPixmap(self.pixmap)
