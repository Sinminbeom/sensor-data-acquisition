from abc import ABC, abstractmethod
from typing import Tuple


class ISnapshotable(ABC):
    @abstractmethod
    def snapshot(self) -> Tuple[str, bytes]:  # content_type, data
        raise NotImplementedError
