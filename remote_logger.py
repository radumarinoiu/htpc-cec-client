import logging
import requests
from requests import HTTPError

from constants import SERVER_ADDRESS


logger = logging.getLogger()


class RemoteHandler(logging.Handler):
    def __init__(self):
        logging.getLogger("urllib3").propagate = False
        super().__init__()

    @classmethod
    def _send_request(cls, message):
        try:
            resp = requests.post(f"{SERVER_ADDRESS}/on-log-emitted/", json={"message": message})
        except ConnectionError:
            print("Failed establishing connection to server. Cannot send message.")
            return
        try:
            resp.raise_for_status()
        except HTTPError:
            print(f"Request failed: [{resp.status_code}] {resp.content}")

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then sent to the remote server.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            self._send_request(msg)
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)
