from abc import abstractmethod, ABC
from typing import Tuple

from core.const import AcqState


class IAcquisitable(ABC):
    @abstractmethod
    def check_acquisition(self) -> Tuple[AcqState, str]:
        raise NotImplementedError

    @abstractmethod
    def start_acquisition(self) -> Tuple[AcqState, str]:
        raise NotImplementedError

    @abstractmethod
    def stop_acquisition(self) -> Tuple[AcqState, str]:
        raise NotImplementedError
