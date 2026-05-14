from abc import abstractmethod, ABC

from core.const import ConnState


class IConnectable(ABC):
    @abstractmethod
    def check_connection(self) -> ConnState:
        raise NotImplementedError
