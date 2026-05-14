import logging
from abc import ABC, abstractmethod

import numpy
import platform

os_type = platform.system()


class IPcdGettable(ABC):
    display = (800, 800)
    view_point_height = 70.0

    @abstractmethod
    def pcd(self) -> numpy.ndarray:
        raise NotImplementedError

    def debug_render(self, file_path: str, points: numpy.ndarray):
        if os_type == 'Windows':
            self.debug_render_win32(file_path, points)
        elif os_type == 'Linux':
            self.debug_render_linux(file_path, points)
        else:
            logging.warning(f'Unsupported OS: {os_type}')

    def debug_render_win32(self, file_path: str, points: numpy.ndarray):
        import cv2
        import pygame
        from pygame.locals import DOUBLEBUF, OPENGL
        from OpenGL.GLU import gluPerspective
        from OpenGL.GL import \
            glTranslatef, glClear, glColor3f, glPointSize, glBegin, glVertex3fv, glEnd, glReadBuffer, glReadPixels, \
            GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_POINTS, GL_FRONT, GL_RGB, GL_UNSIGNED_BYTE

        # Initialize Pygame and open an OpenGL window
        pygame.init()
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL | pygame.HIDDEN)

        # Set the perspective of the OpenGL camera
        gluPerspective(45, (self.display[0] / self.display[1]), 0.1, self.view_point_height + 10)
        glTranslatef(0.0, 0.0, -self.view_point_height)

        # Render the point cloud
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glColor3f(1, 1, 1)  # Set point color to white
        glPointSize(1)  # Set point size
        glBegin(GL_POINTS)
        for point in points:
            glVertex3fv(point)
        glEnd()

        # Grab the image from the OpenGL buffer
        pygame.display.flip()
        pygame.time.wait(10)
        glReadBuffer(GL_FRONT)
        pixels = glReadPixels(0, 0, self.display[0], self.display[1], GL_RGB, GL_UNSIGNED_BYTE)
        image = numpy.frombuffer(pixels, dtype=numpy.uint8).reshape(self.display[1], self.display[0], 3)

        # Convert the image from BGR to RGB and flip it vertically
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.flip(image, 0)

        # Save the image
        cv2.imwrite(file_path, image)

        # Close the OpenGL window
        pygame.quit()

    def debug_render_linux(self, file_path: str, points: numpy.ndarray):
        from OpenGL.GL import glTranslatef, glClear, glColor3f, glPointSize, glBegin, glVertex3fv, glEnd, \
            glReadPixels, glFlush, glPixelStorei, \
            GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_POINTS, GL_PACK_ALIGNMENT, GL_RGBA, GL_UNSIGNED_BYTE
        from OpenGL.GLU import gluPerspective
        from OpenGL.GLUT import glutInit, glutInitDisplayMode, glutInitWindowSize, glutCreateWindow, glutHideWindow, \
            GLUT_DOUBLE, GLUT_RGB
        from xvfbwrapper import Xvfb
        from PIL import Image
        from PIL import ImageOps

        vdisplay = Xvfb(width=self.display[0], height=self.display[1])
        vdisplay.start()

        # Initialize and open an OpenGL window
        glutInit()

        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
        glutInitWindowSize(self.display[0], self.display[1])
        glutCreateWindow(b"OpenGL Offscreen")
        glutHideWindow()

        # Set the perspective of the OpenGL camera
        gluPerspective(45, (self.display[0] / self.display[1]), 0.1, self.view_point_height + 10)
        glTranslatef(0.0, 0.0, -self.view_point_height)

        # Render the point cloud
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glColor3f(1, 1, 1)  # Set point color to white
        glPointSize(1)  # Set point size
        glBegin(GL_POINTS)
        for point in points:
            glVertex3fv(point)
        glEnd()

        glFlush()

        # Grab the image from the OpenGL buffer
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, self.display[0], self.display[1], GL_RGBA, GL_UNSIGNED_BYTE)

        image = Image.frombytes("RGBA", self.display, data)
        image = ImageOps.flip(image)  # flip image vertically
        image.save(file_path, 'PNG')
