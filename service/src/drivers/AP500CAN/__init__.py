import platform

if not 'aarch64' == platform.processor():
    from .driver import AP500CAN
