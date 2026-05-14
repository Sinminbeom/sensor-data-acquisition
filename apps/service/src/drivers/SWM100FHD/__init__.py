import platform

if 'aarch64' == platform.processor():
    # This is for Jetson Orin
    from .driver import SWM100FHD
