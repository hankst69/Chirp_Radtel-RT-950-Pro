"""RT-950 Pro utility package."""
from __future__ import annotations

from .channel import (
    Bandwidth,
    ChannelRecord,
    Modulation,
    PowerLevel,
    ToneMode,
    ToneSetting,
)
from .dat_loader import CPSLoaderError, load_cps_radio
from .image import RadioImage
from .regression import ComparisonError, ComparisonResult, Difference, compare_dat_to_csv
from .transport import (
    CloneSegment,
    CloneSerialConfig,
    CloneSerialTransport,
    CloneTransportError,
)
from .settings_api import (
    SettingsError,
    function_keys,
    get_function_value,
    set_function_value,
    aprs_keys,
    get_aprs_value,
    set_aprs_value,
    get_dtmf_current_id,
    set_dtmf_current_id,
    get_dtmf_code_group,
    set_dtmf_code_group,
    get_dtmf_ptt_mode,
    set_dtmf_ptt_mode,
)

__all__ = [
    "Bandwidth",
    "ChannelRecord",
    "Modulation",
    "PowerLevel",
    "ToneMode",
    "ToneSetting",
    "RadioImage",
    "CPSLoaderError",
    "load_cps_radio",
    "ComparisonError",
    "ComparisonResult",
    "Difference",
    "compare_dat_to_csv",
    "CloneSerialTransport",
    "CloneSerialConfig",
    "CloneTransportError",
    "CloneSegment",
    "SettingsError",
    "function_keys",
    "get_function_value",
    "set_function_value",
    "aprs_keys",
    "get_aprs_value",
    "set_aprs_value",
    "get_dtmf_current_id",
    "set_dtmf_current_id",
    "get_dtmf_code_group",
    "set_dtmf_code_group",
    "get_dtmf_ptt_mode",
    "set_dtmf_ptt_mode",
]
