import logging
import os.path
from datetime import datetime

import h5py

if __name__ == '__main__':
    HDF5_FILENAME = 'thumbnail.hdf5'
    with h5py.File(os.path.join('storage', 'a', HDF5_FILENAME), 'r') as hdf5:
        total_entries = len(hdf5['timestamps'])
        for index in range(total_entries):
            timestamp = hdf5['timestamps'][index]
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            tail_of_file = datetime.fromtimestamp(timestamp).strftime('%H.%M.%S.%f')[:-3]

            for device_key in hdf5.keys():
                if device_key == 'timestamps':
                    continue

                ds_device = hdf5[device_key]
                for sensor_key in ds_device.keys():
                    ds_sensors = ds_device[sensor_key]

                    content_type = ds_sensors['type'][index].decode('utf-8')
                    data = ds_sensors['data'][index].tobytes()
                    if content_type == 'application/json':
                        file_ext = 'json'
                    elif content_type == 'image/jpeg':
                        file_ext = 'jpg'
                    elif content_type == 'image/png':
                        file_ext = 'png'
                    else:
                        logging.warning(f'Unknown content type: {content_type}, Data: {data}')
                        continue

                    with open(f'tmp/{index}_{sensor_key}_{tail_of_file}.{file_ext}', 'wb') as file:
                        file.write(data)
