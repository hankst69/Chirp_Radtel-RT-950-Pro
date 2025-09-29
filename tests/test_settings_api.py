# MIT License
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

﻿from pathlib import Path

import pytest

from rt950pro import (
    RadioImage,
    SettingsError,
    get_aprs_value,
    get_dtmf_code_group,
    get_dtmf_current_id,
    get_dtmf_ptt_mode,
    get_function_value,
    set_aprs_value,
    set_dtmf_code_group,
    set_dtmf_current_id,
    set_dtmf_ptt_mode,
    set_function_value,
)

FIXTURE = Path('dumps/clean.bin')


def _round_trip(image: RadioImage) -> RadioImage:
    rebuilt = image.to_bytes()
    return RadioImage.from_bytes(rebuilt)


def test_function_setting_round_trip():
    image = RadioImage.from_file(FIXTURE)
    func = image.function
    assert func is not None

    original_vox = get_function_value(func, 'vox')
    set_function_value(func, 'vox', 7)
    set_function_value(func, 'tdr', True)

    rebuilt = _round_trip(image)
    rebuilt_func = rebuilt.function
    assert rebuilt_func is not None
    assert get_function_value(rebuilt_func, 'vox') == 7
    assert get_function_value(rebuilt_func, 'tdr') is True

    # Restore original to keep image consistent
    set_function_value(func, 'vox', original_vox)
    set_function_value(func, 'tdr', False)


def test_function_setting_validation():
    image = RadioImage.from_file(FIXTURE)
    func = image.function
    assert func is not None
    with pytest.raises(SettingsError):
        set_function_value(func, 'vox', 20)
    with pytest.raises(SettingsError):
        set_function_value(func, 'tdr', 3)


def test_aprs_setting_round_trip():
    image = RadioImage.from_file(FIXTURE)
    aprs = image.aprs
    assert aprs is not None

    original_switch = get_aprs_value(aprs, 'aprs_switch')
    original_callsign = get_aprs_value(aprs, 'call_sign')

    set_aprs_value(aprs, 'aprs_switch', True)
    set_aprs_value(aprs, 'call_sign', 'N0CALL')

    rebuilt = _round_trip(image)
    rebuilt_aprs = rebuilt.aprs
    assert rebuilt_aprs is not None
    assert get_aprs_value(rebuilt_aprs, 'aprs_switch') is True
    assert get_aprs_value(rebuilt_aprs, 'call_sign') == 'N0CALL'

    # cleanup
    set_aprs_value(aprs, 'aprs_switch', original_switch)
    set_aprs_value(aprs, 'call_sign', original_callsign)


def test_dtmf_helpers_round_trip():
    image = RadioImage.from_file(FIXTURE)
    dtmf = image.dtmf
    assert dtmf is not None

    original_id = get_dtmf_current_id(dtmf)
    original_mode = get_dtmf_ptt_mode(dtmf)
    original_group = get_dtmf_code_group(dtmf, 0)

    set_dtmf_current_id(dtmf, '12345')
    set_dtmf_ptt_mode(dtmf, 2)
    set_dtmf_code_group(dtmf, 0, '5101')

    rebuilt = _round_trip(image)
    rebuilt_dtmf = rebuilt.dtmf
    assert rebuilt_dtmf is not None
    assert get_dtmf_current_id(rebuilt_dtmf) == '12345'
    assert get_dtmf_ptt_mode(rebuilt_dtmf) == 2
    assert get_dtmf_code_group(rebuilt_dtmf, 0) == '5101'

    # reset
    set_dtmf_current_id(dtmf, original_id)
    set_dtmf_ptt_mode(dtmf, original_mode)
    set_dtmf_code_group(dtmf, 0, original_group)


def test_dtmf_validation():
    image = RadioImage.from_file(FIXTURE)
    dtmf = image.dtmf
    assert dtmf is not None
    with pytest.raises(SettingsError):
        set_dtmf_current_id(dtmf, 'ABCDEF')  # too long
    with pytest.raises(SettingsError):
        set_dtmf_code_group(dtmf, 0, 'HELLO')  # invalid characters
    with pytest.raises(SettingsError):
        set_dtmf_ptt_mode(dtmf, 7)
