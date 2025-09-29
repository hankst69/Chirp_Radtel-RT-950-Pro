"""High-level settings API for RT-950 Pro."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .sections import APRSSettings, DTMFSettings, FunctionSettings

__all__ = [
    "SettingsError",
    "get_function_value",
    "set_function_value",
    "function_keys",
    "get_aprs_value",
    "set_aprs_value",
    "aprs_keys",
    "get_dtmf_current_id",
    "set_dtmf_current_id",
    "get_dtmf_code_group",
    "set_dtmf_code_group",
    "get_dtmf_ptt_mode",
    "set_dtmf_ptt_mode",
]


class SettingsError(ValueError):
    """Raised when callers attempt to set an invalid value."""


@dataclass(frozen=True)
class SettingSpec:
    kind: str  # "bool", "int", "enum", "string"
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    choices: Optional[Iterable[int]] = None
    max_length: Optional[int] = None


# ---------------------------------------------------------------------------
# Function block helpers ----------------------------------------------------
# ---------------------------------------------------------------------------

_FUNCTION_SPECS: Dict[str, SettingSpec] = {
    "sql": SettingSpec("int", 0, 9),
    "save_mode": SettingSpec("int", 0, 3),
    "vox": SettingSpec("int", 0, 9),
    "auto_backlight": SettingSpec("int", 0, 9),
    "tdr": SettingSpec("bool"),
    "tot": SettingSpec("int", 0, 9),
    "beep_prompt": SettingSpec("bool"),
    "voice_prompt": SettingSpec("enum", choices=tuple(range(0, 3))),
    "language": SettingSpec("enum", choices=tuple(range(0, 3))),
    "dtmf_mode": SettingSpec("enum", choices=tuple(range(0, 4))),
    "scan_mode": SettingSpec("enum", choices=tuple(range(0, 3))),
    "ptt_id": SettingSpec("enum", choices=tuple(range(0, 4))),
    "send_id_delay": SettingSpec("int", 0, 9),
    "display_mode_a": SettingSpec("enum", choices=(0, 1, 2)),
    "display_mode_b": SettingSpec("enum", choices=(0, 1, 2)),
    "display_mode_c": SettingSpec("enum", choices=(0, 1, 2)),
    "auto_key_lock": SettingSpec("bool"),
    "alarm_mode": SettingSpec("enum", choices=tuple(range(0, 3))),
    "alarm_sound": SettingSpec("enum", choices=tuple(range(0, 3))),
    "tail_noise_clear": SettingSpec("bool"),
    "pass_repeater_noise_clear": SettingSpec("bool"),
    "pass_repeater_noise_detect": SettingSpec("bool"),
    "sound_tx_end": SettingSpec("bool"),
    "current_work_mode": SettingSpec("enum", choices=(0, 1, 2)),
    "fm_radio": SettingSpec("bool"),
    "work_mode_a": SettingSpec("enum", choices=(0, 1, 2, 3)),
    "work_mode_b": SettingSpec("enum", choices=(0, 1, 2, 3)),
    "work_mode_c": SettingSpec("enum", choices=(0, 1, 2, 3)),
    "lock_keyboard": SettingSpec("bool"),
    "power_on_message": SettingSpec("enum", choices=tuple(range(0, 3))),
    "bt_write_switch": SettingSpec("bool"),
    "rtone": SettingSpec("enum", choices=tuple(range(0, 3))),
    "vox_delay": SettingSpec("int", 0, 9),
    "timer_menu_quit": SettingSpec("int", 0, 9),
    "weather_channel": SettingSpec("enum", choices=tuple(range(0, 10))),
    "divide_channel": SettingSpec("bool"),
    "subaudio_scan_save": SettingSpec("bool"),
    "vox_switch": SettingSpec("bool"),
    "key_side1_short": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key_side1_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key_side2_short": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key_side2_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "current_work_area_a": SettingSpec("enum", choices=tuple(range(0, 16))),
    "current_work_area_b": SettingSpec("enum", choices=tuple(range(0, 16))),
    "current_work_area_c": SettingSpec("enum", choices=tuple(range(0, 16))),
    "ab_uv_transfer": SettingSpec("bool"),
    "sound_transfer": SettingSpec("bool"),
    "key0_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key1_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key2_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key3_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key4_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key5_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key6_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key7_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key8_long": SettingSpec("enum", choices=tuple(range(0, 32))),
    "key9_long": SettingSpec("enum", choices=tuple(range(0, 32))),
}


def function_keys() -> Iterable[str]:
    """Return all supported function-setting keys."""

    return _FUNCTION_SPECS.keys()


def _coerce_bool(value) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if value in (0, 1):
        return int(value)
    raise SettingsError("Boolean setting expects True/False or 0/1")


def _validate(spec: SettingSpec, value) -> int:
    if spec.kind == "bool":
        return _coerce_bool(value)
    if not isinstance(value, int):
        raise SettingsError("Setting expects integer value")
    if spec.kind == "int":
        if spec.min_value is not None and value < spec.min_value:
            raise SettingsError(f"Value {value} below minimum {spec.min_value}")
        if spec.max_value is not None and value > spec.max_value:
            raise SettingsError(f"Value {value} above maximum {spec.max_value}")
        return value
    if spec.kind == "enum":
        if spec.choices is not None and value not in spec.choices:
            raise SettingsError(f"Value {value} not in allowed choices {tuple(spec.choices)}")
        return value
    raise SettingsError(f"Unsupported setting kind {spec.kind}")


def get_function_value(settings: FunctionSettings, key: str):
    """Return a user-friendly value for ``key`` (or ``None`` if unset)."""

    if key not in _FUNCTION_SPECS:
        raise KeyError(key)
    value = settings.values.get(key)
    if value is None:
        return None
    spec = _FUNCTION_SPECS[key]
    if spec.kind == "bool":
        return bool(value)
    return value


def set_function_value(settings: FunctionSettings, key: str, value) -> None:
    """Update ``key`` within ``settings`` after validating the input."""

    if key not in _FUNCTION_SPECS:
        raise KeyError(key)
    if value is None:
        settings.values[key] = None
        return
    spec = _FUNCTION_SPECS[key]
    encoded = _validate(spec, value)
    settings.values[key] = encoded


# ---------------------------------------------------------------------------
# APRS helpers --------------------------------------------------------------
# ---------------------------------------------------------------------------

_APRS_SPECS: Dict[str, SettingSpec] = {
    "aprs_switch": SettingSpec("bool"),
    "gps_switch": SettingSpec("bool"),
    "latlon_unit": SettingSpec("enum", choices=(0, 1)),
    "speed_unit": SettingSpec("enum", choices=(0, 1)),
    "distance_unit": SettingSpec("enum", choices=(0, 1)),
    "altitude_unit": SettingSpec("enum", choices=(0, 1)),
    "time_zone": SettingSpec("int", 0, 23),
    "north_south": SettingSpec("enum", choices=(0, 1)),
    "latitude_minute": SettingSpec("int", 0, 59),
    "latitude_degree": SettingSpec("int", 0, 90),
    "latitude_second": SettingSpec("int", 0, 59),
    "east_west": SettingSpec("enum", choices=(0, 1)),
    "longitude_minute": SettingSpec("int", 0, 59),
    "longitude_degree": SettingSpec("int", 0, 180),
    "longitude_second": SettingSpec("int", 0, 59),
    "altitude": SettingSpec("int", -10000, 10000),
    "call_sign": SettingSpec("string", max_length=6),
    "ssid": SettingSpec("enum", choices=tuple(range(0, 16))),
    "routing_select": SettingSpec("enum", choices=tuple(range(0, 6))),
    "my_position": SettingSpec("enum", choices=tuple(range(0, 6))),
    "radio_symbol": SettingSpec("enum", choices=tuple(range(0, 100))),
    "user_defined_icon": SettingSpec("enum", choices=tuple(range(0, 128))),
    "aprs_priority": SettingSpec("enum", choices=tuple(range(0, 3))),
    "data_tx_delay": SettingSpec("int", 0, 9),
    "aprs_decode_prompt_tone": SettingSpec("bool"),
    "aprs_rx_auto_popup": SettingSpec("bool"),
    "beacon_tx_type": SettingSpec("enum", choices=tuple(range(0, 3))),
    "timed_beacon_time": SettingSpec("int", 0, 60),
    "mice_type": SettingSpec("enum", choices=tuple(range(0, 4))),
    "tnc_data_type": SettingSpec("enum", choices=tuple(range(0, 4))),
    "aprs_forward_channel": SettingSpec("enum", choices=tuple(range(0, 16))),
    "aprs_forward_routing": SettingSpec("enum", choices=tuple(range(0, 6))),
    "aprs_wait_forward": SettingSpec("int", 0, 9),
    "custom_routing_one": SettingSpec("string", max_length=6),
    "custom_routing_one_ssid": SettingSpec("enum", choices=tuple(range(0, 16))),
    "custom_routing_two": SettingSpec("string", max_length=6),
    "custom_routing_two_ssid": SettingSpec("enum", choices=tuple(range(0, 16))),
    "send_custom_messages": SettingSpec("bool"),
    "custom_messages": SettingSpec("string", max_length=40),
}


def aprs_keys() -> Iterable[str]:
    return _APRS_SPECS.keys()


def get_aprs_value(settings: APRSSettings, key: str):
    if key not in _APRS_SPECS:
        raise KeyError(key)
    value = settings.fields.get(key)
    spec = _APRS_SPECS[key]
    if value is None:
        return None
    if spec.kind == "bool":
        return bool(value)
    return value


def set_aprs_value(settings: APRSSettings, key: str, value) -> None:
    if key not in _APRS_SPECS:
        raise KeyError(key)
    if value is None:
        settings.fields[key] = None
        return
    spec = _APRS_SPECS[key]
    if spec.kind == "string":
        if not isinstance(value, str):
            raise SettingsError("String setting expects str value")
        if spec.max_length is not None and len(value) > spec.max_length:
            raise SettingsError(
                f"String '{value}' longer than allowed {spec.max_length} characters"
            )
        settings.fields[key] = value
        return
    encoded = _validate(spec, value)
    settings.fields[key] = encoded


# ---------------------------------------------------------------------------
# DTMF helpers --------------------------------------------------------------
# ---------------------------------------------------------------------------

_ALLOWED_DTMF = set("0123456789ABCD*#")


def _validate_dtmf_string(value: str, max_len: int) -> str:
    if not isinstance(value, str):
        raise SettingsError("DTMF sequence must be a string")
    filtered = value.strip()
    if len(filtered) > max_len:
        raise SettingsError(f"DTMF value '{value}' exceeds {max_len} characters")
    if not all(ch in _ALLOWED_DTMF for ch in filtered):
        raise SettingsError("DTMF value contains invalid characters")
    return filtered


def get_dtmf_current_id(settings: DTMFSettings) -> str:
    return settings.current_id


def set_dtmf_current_id(settings: DTMFSettings, value: str) -> None:
    settings.current_id = _validate_dtmf_string(value, 5)


def get_dtmf_ptt_mode(settings: DTMFSettings) -> Optional[int]:
    return settings.ptt_id_mode


def set_dtmf_ptt_mode(settings: DTMFSettings, value: Optional[int]) -> None:
    if value is None:
        settings.ptt_id_mode = None
        return
    if value not in (0, 1, 2, 3):
        raise SettingsError("DTMF PTT mode must be 0-3")
    settings.ptt_id_mode = value


def get_dtmf_code_group(settings: DTMFSettings, index: int) -> str:
    return settings.code_groups[index]


def set_dtmf_code_group(settings: DTMFSettings, index: int, value: str) -> None:
    if not 0 <= index < len(settings.code_groups):
        raise IndexError(index)
    settings.code_groups[index] = _validate_dtmf_string(value, 6)
