from abc import abstractmethod, ABC
from typing import Tuple

from core.const import HealthStatus


class IHealthCheckable(ABC):
    @abstractmethod
    def check_health(self) -> Tuple[HealthStatus, str]:
        raise NotImplementedError
