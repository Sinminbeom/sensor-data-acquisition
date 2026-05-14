from enum import IntEnum


class HealthStatus(IntEnum):
    UNKNOWN = 0
    GOOD = 1
    WARN = 2
    BAAD = 3  # bad 의 강조
