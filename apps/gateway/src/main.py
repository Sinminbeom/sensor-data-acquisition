import logging
import os
import sys

from core import GatewayServer

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    config_file_path = os.getenv('CONFIG_FILE_PATH')
    if not config_file_path:
        logging.error('CONFIG_FILE_PATH environment variable is not set.')
        sys.exit(1)

    try:
        GatewayServer(config_file_path).run()

    except KeyboardInterrupt:
        logging.info('Gateway Server stopped by user.')

    except Exception as e:
        logging.error(e)
