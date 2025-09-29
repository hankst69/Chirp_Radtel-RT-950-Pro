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

from pathlib import Path

from rt950pro.image import CHANNEL_SECTION_BYTES, RadioImage

TAIL_START = 0x7A80
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "dumps" / "clean.bin"


def test_clone_bin_round_trip():
    raw = FIXTURE_PATH.read_bytes()
    image = RadioImage.from_bytes(raw)
    rebuilt = image.to_bytes()
    rebuilt_image = RadioImage.from_bytes(rebuilt)

    assert rebuilt[:TAIL_START] == raw[:TAIL_START]
    assert rebuilt_image.channels == image.channels
    assert rebuilt_image.vfo == image.vfo
    assert rebuilt_image.function == image.function
    assert rebuilt_image.dtmf == image.dtmf
    assert rebuilt_image.modulation is not None
    assert image.modulation is not None
    assert rebuilt_image.modulation.fm_current_channel == image.modulation.fm_current_channel
    assert rebuilt_image.modulation.am_current_channel == image.modulation.am_current_channel
    assert rebuilt_image.modulation.ssb_current_channel == image.modulation.ssb_current_channel
    assert rebuilt_image.modulation.work_mode == image.modulation.work_mode
    assert rebuilt_image.modulation.modulation_mode == image.modulation.modulation_mode
    assert rebuilt_image.modulation.am_step_index == image.modulation.am_step_index
    assert rebuilt_image.modulation.am_rx_gain == image.modulation.am_rx_gain
    assert rebuilt_image.modulation.ssb_step_index == image.modulation.ssb_step_index
    assert rebuilt_image.modulation.ssb_rx_gain == image.modulation.ssb_rx_gain

    for rebuilt_entry, original_entry in zip(rebuilt_image.modulation.channels, image.modulation.channels):
        assert rebuilt_entry.fm_frequency == original_entry.fm_frequency
        assert rebuilt_entry.am_frequency == original_entry.am_frequency
        assert rebuilt_entry.ssb_frequency == original_entry.ssb_frequency
        assert rebuilt_entry.ssb_bandwidth == original_entry.ssb_bandwidth
        assert rebuilt_entry.ssb_beat_offset == original_entry.ssb_beat_offset

    assert rebuilt_image.aprs == image.aprs


def test_round_trip_with_mutations():
    image = RadioImage.from_file(FIXTURE_PATH)

    assert image.vfo
    new_rx = 146_520_000
    image.vfo[0].rx_hz = new_rx
    image.vfo[0].offset_hz = 5000

    assert image.function
    image.function.values["vox"] = 3
    image.function.values["auto_key_lock"] = 1

    assert image.dtmf
    image.dtmf.current_id = "12345"
    if image.dtmf.code_groups:
        image.dtmf.code_groups[0] = "12"

    assert image.modulation
    expected_mod_freq = (image.modulation.channels[0].fm_frequency + 5) % 65536
    image.modulation.channels[0].fm_frequency = expected_mod_freq
    image.modulation.channels[0].fm_name = "LOCAL FM"

    assert image.aprs
    image.aprs.fields["call_sign"] = "N0CALL"
    image.aprs.fields["user_defined_icon"] = 17

    rebuilt = image.to_bytes()
    rebuilt_image = RadioImage.from_bytes(rebuilt)

    assert rebuilt_image.vfo
    assert rebuilt_image.vfo[0].rx_hz == new_rx
    assert rebuilt_image.vfo[0].offset_hz == 5000

    assert rebuilt_image.function
    assert rebuilt_image.function.values.get("vox") == 3
    assert rebuilt_image.function.values.get("auto_key_lock") == 1

    assert rebuilt_image.dtmf
    assert rebuilt_image.dtmf.current_id == "12345"
    if rebuilt_image.dtmf.code_groups:
        assert rebuilt_image.dtmf.code_groups[0].startswith("12")

    assert rebuilt_image.modulation
    assert rebuilt_image.modulation.channels[0].fm_frequency == expected_mod_freq
    assert rebuilt_image.modulation.channels[0].fm_name == "LOCAL FM"

    assert rebuilt_image.aprs
    assert rebuilt_image.aprs.fields.get("call_sign") == "N0CALL"
    assert rebuilt_image.aprs.fields.get("user_defined_icon") == 17

