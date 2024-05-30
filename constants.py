from enum import Enum


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
