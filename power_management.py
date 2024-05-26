import ctypes
import os
import platform
import subprocess
import sys
import traceback

import requests
import win32con
import win32api
import win32gui
import time
from ctypes import POINTER, windll, Structure, cast, CFUNCTYPE, c_int, c_uint, c_void_p, c_bool
from comtypes import GUID
from ctypes.wintypes import HANDLE, DWORD
from constants import EventTypes, EventTargets, EVENT_TYPE_KEY, EVENT_TARGET_KEY, EVENT_VALUE_KEY
from requests import HTTPError

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


PBT_POWERSETTINGCHANGE = 0x8013
GUID_CONSOLE_DISPLAY_STATE = "{6FE69556-704A-47A0-8F24-C28D936FDA47}"
GUID_ACDC_POWER_SOURCE = "{5D3E9A59-E9D5-4B00-A6BD-FF34FF516548}"
GUID_BATTERY_PERCENTAGE_REMAINING = "{A7AD8041-B45A-4CAE-87A3-EECBB468A9E1}"
GUID_MONITOR_POWER_ON = "{02731015-4510-4526-99E6-E5A17EBD1AEA}"
GUID_SYSTEM_AWAYMODE = "{98A7F580-01F7-48AA-9C0F-44352C29E5C0}"


SERVER_ADDRESS = "http://192.168.0.6:5000"


def send_message_to_server(message):
    try:
        resp = requests.post(f"{SERVER_ADDRESS}/on-client-message/", json={"message": message})
    except ConnectionError:
        print(f"Failed establishing connection to server. Cannot send message. Exception:\n{traceback.format_exc()}")
        return
    try:
        resp.raise_for_status()
    except HTTPError:
        print(f"Request failed: [{resp.status_code}] {resp.content}")


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


def wndproc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_POWERBROADCAST:
        request_payload = {
            EVENT_TYPE_KEY: wparam_dict.get(wparam, "N/A"),
            EVENT_TARGET_KEY: "N/A",
            EVENT_VALUE_KEY: "N/A",
        }
        if wparam == win32con.PBT_APMPOWERSTATUSCHANGE:
            print("Power status has changed")
        if wparam == win32con.PBT_APMRESUMEAUTOMATIC:
            print("System resume")
        if wparam == win32con.PBT_APMRESUMESUSPEND:
            print("System resume by user input")
        if wparam == win32con.PBT_APMSUSPEND:
            print("System suspend")
        if wparam == PBT_POWERSETTINGCHANGE:
            print("Power setting changed...")
            settings = cast(lparam, POINTER(POWERBROADCAST_SETTING)).contents
            power_setting = str(settings.PowerSetting)
            data_length = settings.DataLength
            data = settings.Data
            request_payload[EVENT_TARGET_KEY] = power_settings_dict.get(power_setting, "N/A")
            try:
                request_payload[EVENT_VALUE_KEY] = int(data)
            except ValueError:
                pass  # Do nothing, value will be N/A if it's not an int
            if power_setting == GUID_CONSOLE_DISPLAY_STATE:
                if data == 0:
                    print("Display off")
                if data == 1:
                    print("Display on")
                if data == 2:
                    print("Display dimmed")
            elif power_setting == GUID_ACDC_POWER_SOURCE:
                if data == 0:
                    print("AC power")
                if data == 1:
                    print("Battery power")
                if data == 2:
                    print("Short term power")
            elif power_setting == GUID_BATTERY_PERCENTAGE_REMAINING:
                print("battery remaining: %s" % data)
            elif power_setting == GUID_MONITOR_POWER_ON:
                if data == 0:
                    print("Monitor off")
                if data == 1:
                    print("Monitor on")
            elif power_setting == GUID_SYSTEM_AWAYMODE:
                if data == 0:
                    print("Exiting away mode")
                if data == 1:
                    print("Entering away mode")
            else:
                print("unknown GUID")

        send_message_to_server(request_payload)
        return True

    return False


class POWERBROADCAST_SETTING(Structure):
    _fields_ = [("PowerSetting", GUID),
                ("DataLength", DWORD),
                ("Data", DWORD)]


class WindowsPowerManagement:
    def __init__(self):
        self._last_update_check = time.monotonic()

    def listen(self):

        print("*** STARTING ***")
        hinst = win32api.GetModuleHandle(None)
        wndclass = win32gui.WNDCLASS()
        wndclass.hInstance = hinst
        wndclass.lpszClassName = "testWindowClass"
        CMPFUNC = CFUNCTYPE(c_bool, c_int, c_uint, c_uint, c_void_p)
        wndproc_pointer = CMPFUNC(wndproc)
        wndclass.lpfnWndProc = {win32con.WM_POWERBROADCAST: wndproc_pointer}
        try:
            myWindowClass = win32gui.RegisterClass(wndclass)
            hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LEFT,
                                           myWindowClass,
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
            print("Exception: %s" % str(e))

        if hwnd is None:
            print("hwnd is none!")
        else:
            print("hwnd: %s" % hwnd)

        guids_info = {
            "GUID_MONITOR_POWER_ON": GUID_MONITOR_POWER_ON,
            "GUID_SYSTEM_AWAYMODE": GUID_SYSTEM_AWAYMODE,
            "GUID_CONSOLE_DISPLAY_STATE": GUID_CONSOLE_DISPLAY_STATE,
            # "GUID_ACDC_POWER_SOURCE": GUID_ACDC_POWER_SOURCE,
            # "GUID_BATTERY_PERCENTAGE_REMAINING": GUID_BATTERY_PERCENTAGE_REMAINING
        }
        for name, guid_info in guids_info.items():
            result = windll.user32.RegisterPowerSettingNotification(HANDLE(hwnd), GUID(guid_info), DWORD(0))
            print("registering", name)
            print("result:", hex(result))
            print("lastError:", win32api.GetLastError())
            print()

        print("\nEntering loop")
        while True:
            win32gui.PumpWaitingMessages()
            # Testing
            self.check_for_updates()
            time.sleep(1)

    def check_for_updates(self):
        if time.monotonic() - self._last_update_check < 30:
            return

        print("Checking for updates...", end="")
        subprocess.check_output(["git", "fetch"], stderr=subprocess.DEVNULL)
        # subprocess.check_output(["git", "reset", "--hard"])
        # subprocess.check_output(["git", "checkout", "master"])
        output = subprocess.check_output(["git", "pull"], stderr=subprocess.DEVNULL)
        print(" [Done]")
        if output.startswith(b"Updating "):
            print("Update available, installing requirements...", end="")
            subprocess.check_output(
                [sys.executable, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"],
                stderr=subprocess.DEVNULL
            )
            print(" [Done]")
            print("Restarting process...")
            os.execl(sys.executable, sys.executable, *sys.argv)
        self._last_update_check = time.monotonic()

    def _set_thread_execution(self, state):
        ctypes.windll.kernel32.SetThreadExecutionState(state)


    # def prevent_standby(self):
    #     if platform.system() == "Windows":
    #         self._set_thread_execution(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    #
    #
    # def allow_standby(self):
    #     if platform.system() == "Windows":
    #         self._set_thread_execution(ES_CONTINUOUS)
