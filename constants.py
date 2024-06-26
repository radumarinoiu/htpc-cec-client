from enum import Enum

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

PBT_POWERSETTINGCHANGE = 0x8013
GUID_CONSOLE_DISPLAY_STATE = "{6FE69556-704A-47A0-8F24-C28D936FDA47}"
GUID_ACDC_POWER_SOURCE = "{5D3E9A59-E9D5-4B00-A6BD-FF34FF516548}"
GUID_BATTERY_PERCENTAGE_REMAINING = "{A7AD8041-B45A-4CAE-87A3-EECBB468A9E1}"
GUID_MONITOR_POWER_ON = "{02731015-4510-4526-99E6-E5A17EBD1AEA}"
GUID_SYSTEM_AWAYMODE = "{98A7F580-01F7-48AA-9C0F-44352C29E5C0}"

SERVER_ADDRESS = "http://192.168.0.6:5000"

EVENT_TYPE_KEY = "event_type"
EVENT_TARGET_KEY = "event_target"
EVENT_VALUE_KEY = "event_value"


class EventTypes(Enum):
    CLIENT_STATUS_CHANGE = "client_status"
    POWER_STATUS_CHANGE = "power_status"
    POWER_RESUME_AUTOMATIC = "system_resume_automatic"
    POWER_RESUME_MANUALLY = "system_resume_manual"
    POWER_SUSPEND = "system_suspend"
    POWER_OTHER_EVENT = "other"


class EventTargets(Enum):
    DISPLAY_STATE = "display_state"
    MONITOR_STATE = "monitor_state"
    AWAY_STATE = "away_state"
    POWER_STATE = "power_state"
