import ctypes
import logging
import os
import subprocess
import sys

import requests
import win32con
import win32api
import win32gui
import time
from ctypes import POINTER, windll, Structure, cast, CFUNCTYPE, c_int, c_uint, c_void_p, c_bool
from comtypes import GUID
from ctypes.wintypes import HANDLE, DWORD
from constants import EventTypes, EventTargets, EVENT_TYPE_KEY, EVENT_TARGET_KEY, EVENT_VALUE_KEY, SERVER_ADDRESS, \
    PBT_POWERSETTINGCHANGE, GUID_CONSOLE_DISPLAY_STATE, GUID_MONITOR_POWER_ON, GUID_SYSTEM_AWAYMODE, \
    GUID_ACDC_POWER_SOURCE, GUID_BATTERY_PERCENTAGE_REMAINING
from requests import HTTPError


wparam_dict = {
    win32con.PBT_APMPOWERSTATUSCHANGE: EventTypes.POWER_STATUS_CHANGE.value,
    win32con.PBT_APMRESUMEAUTOMATIC: EventTypes.POWER_RESUME_AUTOMATIC.value,
    win32con.PBT_APMRESUMESUSPEND: EventTypes.POWER_RESUME_MANUALLY.value,
    win32con.PBT_APMSUSPEND: EventTypes.POWER_SUSPEND.value,
    PBT_POWERSETTINGCHANGE: EventTypes.POWER_OTHER_EVENT.value,
}

power_settings_dict = {
    GUID_CONSOLE_DISPLAY_STATE: EventTargets.DISPLAY_STATE.value,
    GUID_MONITOR_POWER_ON: EventTargets.MONITOR_STATE.value,
    GUID_SYSTEM_AWAYMODE: EventTargets.AWAY_STATE.value,
}


logger = logging.getLogger()


def _send_event(event):
    try:
        resp = requests.post(f"{SERVER_ADDRESS}/on-client-message/", json={"message": event})
    except ConnectionError:
        logger.exception("Failed establishing connection to server. Cannot send message.")
        return
    try:
        resp.raise_for_status()
    except HTTPError:
        logger.exception(f"Request failed: [{resp.status_code}] {resp.content}")


def wndproc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_POWERBROADCAST:
        request_payload = {
            EVENT_TYPE_KEY: wparam_dict.get(wparam, "N/A"),
            EVENT_TARGET_KEY: "N/A",
            EVENT_VALUE_KEY: "N/A",
        }
        if wparam == win32con.PBT_APMPOWERSTATUSCHANGE:
            logger.debug("Power status has changed")
        if wparam == win32con.PBT_APMRESUMEAUTOMATIC:
            logger.debug("System resume")
        if wparam == win32con.PBT_APMRESUMESUSPEND:
            logger.debug("System resume by user input")
        if wparam == win32con.PBT_APMSUSPEND:
            logger.debug("System suspend")
        if wparam == PBT_POWERSETTINGCHANGE:
            logger.debug("Power setting changed...")
            settings = cast(lparam, POINTER(PowerBroadcastSetting)).contents
            power_setting = str(settings.PowerSetting)
            data = settings.Data
            request_payload[EVENT_TARGET_KEY] = power_settings_dict.get(power_setting, "N/A")
            try:
                request_payload[EVENT_VALUE_KEY] = int(data)
            except ValueError:
                pass  # Do nothing, value will be N/A if it's not an int
            if power_setting == GUID_CONSOLE_DISPLAY_STATE:
                if data == 0:
                    logger.debug("Display off")
                if data == 1:
                    logger.debug("Display on")
                if data == 2:
                    logger.debug("Display dimmed")
            elif power_setting == GUID_ACDC_POWER_SOURCE:
                if data == 0:
                    logger.debug("AC power")
                if data == 1:
                    logger.debug("Battery power")
                if data == 2:
                    logger.debug("Short term power")
            elif power_setting == GUID_BATTERY_PERCENTAGE_REMAINING:
                logger.debug("battery remaining: %s" % data)
            elif power_setting == GUID_MONITOR_POWER_ON:
                if data == 0:
                    logger.debug("Monitor off")
                if data == 1:
                    logger.debug("Monitor on")
            elif power_setting == GUID_SYSTEM_AWAYMODE:
                if data == 0:
                    logger.debug("Exiting away mode")
                if data == 1:
                    logger.debug("Entering away mode")
            else:
                logger.debug("unknown GUID")

        _send_event(request_payload)
        return True

    return False


class PowerBroadcastSetting(Structure):
    _fields_ = [("PowerSetting", GUID),
                ("DataLength", DWORD),
                ("Data", DWORD)]


class WindowsPowerManagement:
    def __init__(self):
        self._last_update_check = time.monotonic()

    def listen(self):
        logger.debug("*** STARTING ***")
        if os.path.exists("updated"):
            os.remove("updated")
        else:
            _send_event({
                EVENT_TYPE_KEY: EventTypes.CLIENT_STATUS_CHANGE.value,
                EVENT_TARGET_KEY: "started",
                EVENT_VALUE_KEY: 1,
            })
        hinst = win32api.GetModuleHandle(None)
        wndclass = win32gui.WNDCLASS()
        wndclass.hInstance = hinst
        wndclass.lpszClassName = "testWindowClass"
        cmp_func = CFUNCTYPE(c_bool, c_int, c_uint, c_uint, c_void_p)
        wndproc_pointer = cmp_func(wndproc)
        wndclass.lpfnWndProc = {win32con.WM_POWERBROADCAST: wndproc_pointer}
        try:
            my_window_class = win32gui.RegisterClass(wndclass)
            hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LEFT,
                                           my_window_class,
                                           "testMsgWindow",
                                           0,
                                           0,
                                           0,
                                           win32con.CW_USEDEFAULT,
                                           win32con.CW_USEDEFAULT,
                                           0,
                                           0,
                                           hinst,
                                           None)
        except Exception as e:
            logger.exception("Exception occurred while creating Capturing Window")
            raise

        if hwnd is None:
            logger.debug("hwnd is none!")
        else:
            logger.debug(f"hwnd: {hwnd}")

        guids_info = {
            "GUID_MONITOR_POWER_ON": GUID_MONITOR_POWER_ON,
            "GUID_SYSTEM_AWAYMODE": GUID_SYSTEM_AWAYMODE,
            "GUID_CONSOLE_DISPLAY_STATE": GUID_CONSOLE_DISPLAY_STATE,
            # "GUID_ACDC_POWER_SOURCE": GUID_ACDC_POWER_SOURCE,
            # "GUID_BATTERY_PERCENTAGE_REMAINING": GUID_BATTERY_PERCENTAGE_REMAINING
        }
        for name, guid_info in guids_info.items():
            result = windll.user32.RegisterPowerSettingNotification(HANDLE(hwnd), GUID(guid_info), DWORD(0))
            logger.debug(f"registering: {name}")
            logger.debug(f"result: {hex(result)}")
            logger.debug(f"lastError: {win32api.GetLastError()}")

        logger.debug("Entering loop")
        while True:
            win32gui.PumpWaitingMessages()
            # Testing
            self.check_for_updates()
            time.sleep(1)

    def check_for_updates(self):
        if time.monotonic() - self._last_update_check < 30:
            return

        logger.debug("Checking for updates...")
        subprocess.check_output(["git", "fetch"], stderr=subprocess.DEVNULL)
        output = subprocess.check_output(["git", "pull"], stderr=subprocess.DEVNULL)
        logger.debug("Finished checking for updates")
        if output.startswith(b"Updating "):
            logger.debug("Update available, installing requirements...")
            _send_event({
                EVENT_TYPE_KEY: EventTypes.CLIENT_STATUS_CHANGE.value,
                EVENT_TARGET_KEY: "update_available",
                EVENT_VALUE_KEY: 1,
            })
            subprocess.check_output(
                [sys.executable, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"],
                stderr=subprocess.DEVNULL
            )
            logger.debug("Requirements installed")
            _send_event({
                EVENT_TYPE_KEY: EventTypes.CLIENT_STATUS_CHANGE.value,
                EVENT_TARGET_KEY: "update_installed",
                EVENT_VALUE_KEY: 1,
            })
            with open("updated", "w") as fd:
                fd.write("1")
            logger.debug("Restarting process...")
            os.execl(sys.executable, sys.executable, *sys.argv)
        self._last_update_check = time.monotonic()

    @classmethod
    def _set_thread_execution(cls, state):
        ctypes.windll.kernel32.SetThreadExecutionState(state)
