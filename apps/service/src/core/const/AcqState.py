from enum import Enum


class AcqState(Enum):
    UNKNOWN = 0  # 확인 불가
    ACQUIRING = 1  # 수집중
    NOT_ACQUIRING = 2  # 수집중 아님
