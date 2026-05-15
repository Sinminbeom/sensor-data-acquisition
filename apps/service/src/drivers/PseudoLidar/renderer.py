import threading
import time

import numpy as np
from xvfbwrapper import Xvfb

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from interface import LiDARDriver, DriverError

from PIL import Image
from PIL import ImageOps
from io import BytesIO


class PseudoLidarRenderer(threading.Thread):
    render_duration = 0.1  # seconds

    drivers: dict = {}
    image_width: int
    image_height: int
    zFar: float

    image_lock = threading.Lock()
    image: bytes = b''

    vbo: int = 0

    is_init = False

    def __init__(self, is_init_ref: list, drivers: dict, image_width: int = 800, image_height: int = 800,
                 z_far: float = 70):
        super().__init__()
        self.event = threading.Event()

        self.is_init_ref = is_init_ref
        self.drivers = drivers
        self.image_width = image_width
        self.image_height = image_height
        self.zFar = z_far

    def start(self) -> 'PseudoLidarRenderer':
        super().start()
        return self

    def run(self):
        duration = self.render_duration

        while not self.is_init_ref[0]:
            time.sleep(duration)

        vdisplay = Xvfb(width=self.image_width, height=self.image_height)
        vdisplay.start()

        while not self.event.is_set():
            start_time = time.time()
            self.render()
            end_time = time.time()
            time_diff = end_time - start_time
            if time_diff < duration:
                time.sleep(duration - time_diff)

        # Delete the buffer
        glDeleteBuffers(1, [self.vbo])

        vdisplay.stop()

    def stop(self):
        self.event.set()
        self.join()

    snapshot_counter = 0

    def snapshot(self):
        while len(self.image) == 0:
            if self.snapshot_counter > 100:
                self.snapshot_counter = 0
                raise DriverError("Failed to get snapshot")
            time.sleep(0.01)
            self.snapshot_counter += 1

        self.snapshot_counter = 0

        with self.image_lock:
            return self.image

    def gl_init(self):
        # Initialize and open an OpenGL window
        glutInit()
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
        glutInitWindowSize(self.image_width, self.image_height)
        glutCreateWindow(b"OpenGL Offscreen")
        glutHideWindow()

        # Set the perspective of the OpenGL camera
        gluPerspective(45, (self.image_width / self.image_height), 0.1, self.zFar + 10)
        glTranslatef(0.0, 0.0, -self.zFar)

        # Create a buffer (VBO)
        self.vbo = glGenBuffers(1)

        self.is_init = True

    def render(self):
        if not self.is_init:
            self.gl_init()

        # Get the points from the drivers
        points = self.points()
        if len(points) == 1:
            return

        # Render the point cloud
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glColor3f(1, 1, 1)  # Set point color to white
        glPointSize(1)  # Set point size

        ##################################
        # Create a numpy array from the points
        points_array = np.array(points, dtype=np.float32)

        # Create a buffer (VBO)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, points_array.nbytes, points_array, GL_STATIC_DRAW)

        # Enable the vertex array and set the buffer data
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        glVertexPointer(3, GL_FLOAT, 6 * 4, None)  # The stride is 6 * sizeof(float) because of x, y, z, r, g, b
        glColorPointer(3, GL_FLOAT, 6 * 4, ctypes.c_void_p(12))  # Pointer to the intensity value in the array

        # Draw the points
        glDrawArrays(GL_POINTS, 0, len(points))

        # Disable the vertex array and unbind the buffer
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        ##################################

        glFlush()

        # Insert a fence sync object and wait for the GPU to complete the drawing
        fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
        glClientWaitSync(fence, GL_SYNC_FLUSH_COMMANDS_BIT, GLuint64(-1))  # Wait indefinitely
        glDeleteSync(fence)

        # Grab the image from the OpenGL buffer
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, self.image_width, self.image_height, GL_RGBA, GL_UNSIGNED_BYTE)
        # logging.debug(f"GL: data bytes: {len(data)}")

        image = Image.frombytes("RGBA", (self.image_width, self.image_height), data)
        image = ImageOps.flip(image)  # flip image vertically
        # logging.debug(f"GL: image size: {image.size}")

        with BytesIO() as byte_stream:
            image.save(byte_stream, 'PNG')
            # logging.debug(f"GL: byte_stream size: {byte_stream.tell()}")
            # byte_stream.seek(0)
            with self.image_lock:
                self.image = byte_stream.getvalue()

    def points(self) -> np.ndarray:
        points = np.array([[0, 0, 0, 0, 0, 0]])

        for driver_name, driver in self.drivers.items():
            if isinstance(driver, LiDARDriver):
                try:
                    new_pcd = driver.pcd()
                    points = np.vstack([points, new_pcd])
                except Exception as e:
                    print(f"Failed to get pcd from {driver_name}: {e}")

        return points
