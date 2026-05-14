import logging
import math
from abc import ABC

from interface.DriverError import DriverError, DriverWarn
from interface.IAcquisitable import IAcquisitable
from interface.IConnectable import IConnectable
from interface.IDriver import IDriver
from interface.IHealthCheckable import IHealthCheckable
from interface.IPcdGettable import IPcdGettable
from interface.IShapshotable import ISnapshotable


class GNSSDriver(IDriver, IConnectable, IAcquisitable, ISnapshotable, IHealthCheckable, ABC):
    pass


class LiDARDriver(IDriver, IConnectable, IAcquisitable, IHealthCheckable, IPcdGettable, ABC):
    @staticmethod
    def parse_extrinsic(file_path: str) -> dict:
        import yaml
        try:
            # read yaml file
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = f.read()

            # parse yaml data
            extrinsic = yaml.safe_load(yaml_data)

            params = {
                'x': extrinsic['transform']['translation']['x'],
                'y': extrinsic['transform']['translation']['y'],
                'z': extrinsic['transform']['translation']['z']
            }

            qx = extrinsic['transform']['rotation']['x']
            qy = extrinsic['transform']['rotation']['y']
            qz = extrinsic['transform']['rotation']['z']
            qw = extrinsic['transform']['rotation']['w']

            # Yaw (z-axis rotation)
            siny_cosp = 2 * (qw * qz + qx * qy)
            cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
            params['yaw'] = math.atan2(siny_cosp, cosy_cosp)

            # Pitch (y-axis rotation)
            sinp = 2 * (qw * qy - qz * qx)
            if abs(sinp) >= 1:
                params['pitch'] = math.copysign(math.pi / 2, sinp)  # use 90 degrees if out of range
            else:
                params['pitch'] = math.asin(sinp)

            # Roll (x-axis rotation)
            sinr_cosp = 2 * (qw * qx + qy * qz)
            cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
            params['roll'] = math.atan2(sinr_cosp, cosr_cosp)

            return params

        except Exception as e:
            logging.warning(f'Failed to parse extrinsic file. {e}')
            return {}


class RealCamDriver(IDriver, IConnectable, ISnapshotable, ABC):
    pass


class NetCamDriver(IDriver, IAcquisitable, IHealthCheckable, ABC):
    pass


class StorageDriver(IDriver, IConnectable, ISnapshotable, ABC):
    pass


class CANDriver(IDriver, IConnectable, IAcquisitable, ISnapshotable, ABC):
    pass
