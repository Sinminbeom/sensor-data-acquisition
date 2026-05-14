import importlib
import inspect
import json
import logging
import pkgutil
import sys
from typing import Tuple, List

import jsons

from core.const import *
from interface import DriverError


def import_all_drivers():
    dirname = 'drivers'
    for importer, package_name, _ in pkgutil.iter_modules([dirname]):
        full_package_name = '%s.%s' % (dirname, package_name)
        if full_package_name not in globals():
            module = importlib.import_module(full_package_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    globals()[name] = obj


import_all_drivers()


class Drivers:
    _is_init_ref: List[bool] = [False]
    _drivers: dict = {}

    def get_sensor_names(self) -> Tuple[List[str], str]:
        if not self._is_init_ref[0]:
            return [], 'Initializing drivers.'

        sensors = list(self._drivers.keys())
        if sensors:
            return sensors, ''
        else:
            return [], 'No sensor found.'

    def check_connection(self, driver_name: str) -> ConnState:
        if not self._is_init_ref[0]:
            return ConnState.UNKNOWN

        try:
            return self._drivers[driver_name].check_connection()
        except KeyError:
            return ConnState.UNKNOWN
        except AttributeError:
            return ConnState.UNKNOWN

    def check_health(self, driver_name: str) -> Tuple[HealthStatus, str]:
        if not self._is_init_ref[0]:
            return HealthStatus.UNKNOWN, 'Initializing drivers.'

        try:
            return self._drivers[driver_name].check_health()
        except KeyError:
            return HealthStatus.UNKNOWN, f'Sensor {driver_name} not found.'
        except AttributeError:
            return HealthStatus.UNKNOWN, 'This driver does not support health check.'

    def get_snapshot(self, driver_name: str) -> Tuple[str, bytes]:
        if not self._is_init_ref[0]:
            return 'text/plain', b'Initializing drivers.'

        try:
            return self._drivers[driver_name].snapshot()
        except KeyError:
            return 'text/plain', b'This driver does not exist.'
        except AttributeError:
            return 'text/plain', b'This driver does not support snapshot.'

    def get_snapshots(self) -> List[Tuple[str, str, bytes]]:
        if not self._is_init_ref[0]:
            return []

        snapshots = []
        for driver_name in self._drivers.keys():
            content_type, data = self.get_snapshot(driver_name)
            if content_type != 'text/plain':
                snapshots.append((driver_name, content_type, data))
        return snapshots

    def check_acquisition(self, driver_name: str) -> Tuple[AcqState, str]:
        if not self._is_init_ref[0]:
            return AcqState.UNKNOWN, 'Initializing drivers.'

        try:
            return self._drivers[driver_name].check_acquisition()
        except KeyError:
            return AcqState.UNKNOWN, f"Sensor {driver_name} not found."
        except AttributeError:
            return AcqState.UNKNOWN, f'Driver {driver_name} does not support acquisition.'

    def start_acquisition(self, driver_name: str) -> Tuple[AcqState, str]:
        if not self._is_init_ref[0]:
            return AcqState.UNKNOWN, 'Initializing drivers.'

        try:
            return self._drivers[driver_name].start_acquisition()
        except KeyError:
            logging.error(f"Sensor {driver_name} not found.")
            return AcqState.UNKNOWN, f"Sensor {driver_name} not found."
        except AttributeError:
            logging.error(f"Driver {driver_name} does not support acquisition start.")
            return AcqState.UNKNOWN, 'This driver does not support acquisition start.'

    def stop_acquisition(self, driver_name: str) -> Tuple[AcqState, str]:
        if not self._is_init_ref[0]:
            return AcqState.UNKNOWN, 'Initializing drivers.'

        try:
            return self._drivers[driver_name].stop_acquisition()
        except KeyError:
            logging.error(f"Sensor {driver_name} not found.")
            return AcqState.UNKNOWN, f"Sensor {driver_name} not found."
        except AttributeError:
            logging.error(f"Driver {driver_name} does not support acquisition stop.")
            return AcqState.UNKNOWN, 'This driver does not support acquisition stop.'

    def _register(self, driver):
        try:
            driver.on_start(self._is_init_ref, self._drivers)
            self._drivers[driver.name] = driver
        except Exception as e:
            raise DriverError(f"Failed to initialize driver {driver.name}: {e}")

    @staticmethod
    def str_to_class(classname):
        return getattr(sys.modules[__name__], classname)

    @classmethod
    def load(cls, sensors: List[dict]):
        _cls: Drivers = cls()

        # register drivers
        for sensor in sensors:
            # get driver name
            _driver_name: str = sensor["driver"]
            # remove driver name from sensor
            del sensor["driver"]
            # get driver class
            _driver_cls = _cls.str_to_class(_driver_name)

            # register driver
            _cls._register(jsons.load(sensor, _driver_cls))

        _cls._is_init_ref[0] = True
        return _cls

    def stop_all(self):
        for driver in self._drivers.values():
            driver.on_stop()
            logging.info(f"Driver {driver.name} stopped.")
