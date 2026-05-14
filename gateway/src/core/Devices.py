import json

import jsons

from core.Device import Device
from core.DeviceError import DeviceError
from gateway_pb2 import Connections, Healths, Acquisitions
from service_pb2 import Connection, Health, Acquisition, Sensors, SensorSnapshot, SensorSnapshots


class Devices:
    __devices: dict = {}

    def is_dev_connected(self, dev_name: str) -> Connection:
        try:
            return Connection(name=dev_name, state=self.__devices[dev_name].check_connection())
        except KeyError:
            return Connection(name=dev_name, state=Connection.State.UNKNOWN)

    def is_all_dev_connected(self) -> Connections:
        _connections: Connections = Connections()
        for dev_name in self.__devices.keys():
            _connections.list.append(self.is_dev_connected(dev_name))
        return _connections

    def is_dev_healthy(self, dev_name: str) -> Health:
        try:
            status, reason = self.__devices[dev_name].check_health()
            return Health(name=dev_name, status=status, reason=reason)
        except KeyError:
            return Health(name=dev_name, status=Health.Status.UNKNOWN, reason='This device is not found.')

    def is_all_dev_healthy(self) -> Healths:
        _healths: Healths = Healths()
        for key in self.__devices.keys():
            _healths.list.append(self.is_dev_healthy(key))
        return _healths

    def get_sensors(self) -> Sensors:
        _sensors: Sensors = Sensors()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _sensors.list.append(f'{dev_name}/{sensor_name}')
        return _sensors

    def is_sensor_connected(self, sensor_path: str) -> Connection:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return Connection(name=sensor_path, state=Connection.State.UNKNOWN)
        try:
            dev_name, sensor_name = params
            return Connection(name=sensor_path, state=self.__devices[dev_name].check_sensor_connection(sensor_name))
        except KeyError:
            return Connection(name=sensor_path, state=Connection.State.UNKNOWN)

    def is_all_sensor_connected(self) -> Connections:
        _connections: Connections = Connections()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _connections.list.append(self.is_sensor_connected(f'{dev_name}/{sensor_name}'))
        return _connections

    def is_sensor_healthy(self, sensor_path: str) -> Health:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return Health(name=sensor_path, status=Health.Status.UNKNOWN, reason='Invalid sensor path.')
        try:
            dev_name, sensor_name = params
            status, reason = self.__devices[dev_name].check_sensor_health(sensor_name)
            return Health(name=sensor_path, status=status, reason=reason)
        except KeyError:
            return Health(name=sensor_path, status=Health.Status.UNKNOWN, reason='This device is not found.')

    def is_all_sensor_healthy(self) -> Healths:
        _healths: Healths = Healths()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _healths.list.append(self.is_sensor_healthy(f'{dev_name}/{sensor_name}'))
        return _healths

    def get_sensor_snapshot(self, sensor_path: str) -> SensorSnapshot:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return SensorSnapshot(name=sensor_path, content_type='unknown')
        try:
            dev_name, sensor_name = params
            content_type, data = self.__devices[dev_name].get_sensor_snapshot(sensor_name)
            return SensorSnapshot(name=sensor_path, content_type=content_type, data=data)
        except KeyError:
            return SensorSnapshot(name=sensor_path, content_type='unknown')

    def get_all_sensor_snapshot(self) -> SensorSnapshots:
        _sensor_snapshots: SensorSnapshots = SensorSnapshots()
        for dev_name in self.__devices.keys():
            try:
                snapshots = self.__devices[dev_name].get_all_sensor_snapshot()
                # snapshots 각각의 name에 dev_name을 추가
                for snapshot in snapshots.list:
                    snapshot.name = f'{dev_name}/{snapshot.name}'
                _sensor_snapshots.list.extend(snapshots.list)
            except DeviceError as e:
                continue
        return _sensor_snapshots

    def is_sensor_acquiring(self, sensor_path: str) -> Acquisition:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)
        try:
            dev_name, sensor_name = params
            state, reason = self.__devices[dev_name].check_sensor_acquisition(sensor_name)
            return Acquisition(name=sensor_path, state=state, reason=reason)
        except KeyError:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)

    def is_all_sensor_acquiring(self) -> Acquisitions:
        _acquisitions: Acquisitions = Acquisitions()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _acquisitions.list.append(self.is_sensor_acquiring(f'{dev_name}/{sensor_name}'))
        return _acquisitions

    def start_sensor_acquisition(self, sensor_path: str) -> Acquisition:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)
        try:
            dev_name, sensor_name = params
            state, reason = self.__devices[dev_name].start_sensor_acquisition(sensor_name)
            return Acquisition(name=sensor_path, state=state, reason=reason)
        except KeyError:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)

    def start_all_sensor_acquisition(self) -> Acquisitions:
        _acquisitions: Acquisitions = Acquisitions()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _acquisitions.list.append(self.start_sensor_acquisition(f'{dev_name}/{sensor_name}'))
        return _acquisitions

    def stop_sensor_acquisition(self, sensor_path: str) -> Acquisition:
        # return UNKNOWN if the length of params is not 2, it's invalid path.
        params = sensor_path.split('/')
        if params[0] == '':
            params.pop(0)

        if len(params) != 2:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)
        try:
            dev_name, sensor_name = params
            state, reason = self.__devices[dev_name].stop_sensor_acquisition(sensor_name)
            return Acquisition(name=sensor_path, state=state, reason=reason)
        except KeyError:
            return Acquisition(name=sensor_path, state=Acquisition.State.UNKNOWN)

    def stop_all_sensor_acquisition(self) -> Acquisitions:
        _acquisitions: Acquisitions = Acquisitions()
        for dev_name in self.__devices.keys():
            for sensor_name in self.__devices[dev_name].sensors:
                _acquisitions.list.append(self.stop_sensor_acquisition(f'{dev_name}/{sensor_name}'))
        return _acquisitions

    @classmethod
    def load(cls, config_file_path):
        _cls: Devices = cls()

        # load dict from json file
        _config: dict = {}
        with open(config_file_path, "r") as config_json:
            _config = json.load(config_json)

        # get devices
        for key in _config.keys():
            _cls.__devices[key] = jsons.load(_config[key], Device)
            _cls.__devices[key].post_init()

        return _cls
