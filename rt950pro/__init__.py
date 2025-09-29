# IT License
#
# Copyright (c) 2025 Nathan G. Barguss - 2E0NBS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

﻿"""RT-950 Pro utility package."""
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
