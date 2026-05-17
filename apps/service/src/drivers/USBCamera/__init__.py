import logging

try:
    from .driver import USBCamera
except ImportError as e:
    # GStreamer/python-gi 미설치 환경(Dockerfile.cpu 등)에서는 USBCamera 비활성화
    logging.warning(f'Skipping USBCamera: {e}')
