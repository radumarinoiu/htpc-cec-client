import logging

from power_management import WindowsPowerManagement


if __name__ == '__main__':
    logger = logging.getLogger()
    logging.basicConfig(filename='client.log', level=logging.DEBUG)
    WindowsPowerManagement().listen()
