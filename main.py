import logging
import time

from remote_logger import RemoteHandler
from power_management import WindowsPowerManagement


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    logger.addHandler(logging.FileHandler("client.log"))
    logger.addHandler(RemoteHandler())
    while True:
        try:
            WindowsPowerManagement.disable_sleep()
            WindowsPowerManagement().listen()
        except Exception:
            logger.exception("Critical error occurred, checking for updates, maybe it was fixed...")
            try:
                WindowsPowerManagement().check_for_updates(force=True)
            except Exception:
                logger.exception("Critical error occurred while checking for updates, exiting...")
                exit(1)
            time.sleep(30)
        finally:
            WindowsPowerManagement.enable_sleep()
