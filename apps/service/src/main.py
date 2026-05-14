import logging
import os
import sys

from core.ServiceServer import ServiceServer


def get_config(file_path):
    import json
    with open(file_path, "r") as config_json:
        return json.load(config_json)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # RSBP에서 information 제공 포맷이 잘못되어 발생하는 경고를 무시하기 위한 설정
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    config_file_path = os.getenv('CONFIG_FILE_PATH')
    if not config_file_path:
        logging.error('CONFIG_FILE_PATH environment variable is not set.')
        sys.exit(1)

    # config 파일 parsing
    config = get_config(config_file_path)

    # config 파일에 vid가 정의되어 있지 않으면 종료
    if 'vid' not in config:
        logging.error('Vehicle ID(vid: str) is not defined in the config file.')
        sys.exit(1)

    # config 파일에 정의된 vid를 환경변수에 저장
    os.environ['VEHICLE_ID'] = config['vid']

    # config 파일에 sensors가 정의되어 있지 않으면 종료
    if 'sensors' not in config:
        logging.error('Sensors(sensors: list) are not defined in the config file.')
        sys.exit(1)

    try:
        ServiceServer(config['sensors']).run()

    except Exception as e:
        logging.error(e)
