from abc import ABC


class IDriver(ABC):
    name: str

    def on_start(self, is_init_ref: list, drivers: dict):
        pass

    def on_stop(self):
        pass
