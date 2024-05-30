import logging

from htpc_cec_client.remote_logger import RemoteHandler
from power_management import WindowsPowerManagement


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    logger.addHandler(logging.FileHandler("client.log"))
    logger.addHandler(RemoteHandler())
    WindowsPowerManagement().listen()
