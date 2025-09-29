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

"""Parsed data structures and codecs for RT-950 Pro clone sections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .channel import Bandwidth, Modulation, PowerLevel, ToneSetting

__all__ = [
    "VFOSettings",
    "FunctionSettings",
    "DTMFSettings",
    "ModulationChannelEntry",
    "ModulationSettings",
    "APRSSettings",
    "parse_vfo_section",
    "parse_function_section",
    "parse_dtmf_section",
    "parse_modulation_sections",
    "parse_aprs_section",
    "encode_vfo_section",
    "encode_function_section",
    "encode_dtmf_section",
    "encode_modulation_sections",
    "encode_aprs_section",
]

_DTMF_DIGITS = "0123456789ABCD*#"


@dataclass(slots=True)
class VFOSettings:
    """Decoded VFO entry."""

    rx_hz: Optional[int]
    offset_hz: Optional[int]
    rx_tone: ToneSetting
    tx_tone: ToneSetting
    busy_lockout: bool
    offset_direction: int
    signalling_group: int
    tx_power: PowerLevel
    scrambler: int
    learn_fhss: bool
    bandwidth: Bandwidth
    encryption: int
    rx_modulation: Modulation
    freq_band: int
    step_freq_index: int
    _raw_bytes: bytes = field(default=b"", repr=False, compare=False)
    _original_state: Optional[tuple] = field(default=None, repr=False, compare=False)

    def _state_tuple(self) -> tuple:
        return (
            self.rx_hz,
            self.offset_hz,
            self.rx_tone._state_tuple(),
            self.tx_tone._state_tuple(),
            self.busy_lockout,
            self.offset_direction,
            self.signalling_group,
            self.tx_power,
            self.scrambler,
            self.learn_fhss,
            self.bandwidth,
            self.encryption,
            self.rx_modulation,
            self.freq_band,
            self.step_freq_index,
        )


@dataclass(slots=True)
class FunctionSettings:
    """Flat mapping of function configuration values."""

    values: Dict[str, Optional[int]] = field(default_factory=dict)


@dataclass(slots=True)
class DTMFSettings:
    """Decoded DTMF settings and code groups."""

    current_id: str
    ptt_id_mode: Optional[int]
    last_time_send: Optional[int]
    last_time_stop: Optional[int]
    code_groups: List[str]


@dataclass(slots=True)
class ModulationChannelEntry:
    """Single modulation channel entry across FM/AM/SSB."""

    fm_frequency: int
    fm_name: str
    am_frequency: int
    am_name: str
    ssb_frequency: int
    ssb_bandwidth: int
    ssb_beat_offset: int
    ssb_name: str


@dataclass(slots=True)
class ModulationSettings:
    """Full modulation section contents."""

    fm_current_channel: Optional[int]
    am_current_channel: Optional[int]
    ssb_current_channel: Optional[int]
    work_mode: Optional[int]
    modulation_mode: Optional[int]
    am_step_index: Optional[int]
    am_rx_gain: Optional[int]
    ssb_step_index: Optional[int]
    ssb_rx_gain: Optional[int]
    channels: List[ModulationChannelEntry]


@dataclass(slots=True)
class APRSSettings:
    """Decoded APRS settings."""

    fields: Dict[str, Optional[object]] = field(default_factory=dict)


def parse_vfo_section(section: bytes) -> List[VFOSettings]:
    if len(section) % 32 != 0:
        raise ValueError("VFO section must be a multiple of 32 bytes")
    entries: List[VFOSettings] = []
    for offset in range(0, len(section), 32):
        chunk = section[offset : offset + 32]
        rx_hz = _decode_vfo_frequency(chunk[0:8])
        rx_tone = ToneSetting.from_bytes(bytes(chunk[8:10]))
        tx_tone = ToneSetting.from_bytes(bytes(chunk[10:12]))
        busy_lockout = bool(chunk[13] & 0x01)
        offset_dir = (chunk[14] >> 4) & 0x03
        signalling_group = chunk[14] & 0x0F
        tx_power_raw = chunk[16] & 0x0F
        tx_power = PowerLevel(min(tx_power_raw, PowerLevel.HIGH.value))
        scrambler = (chunk[16] >> 4) & 0x0F
        learn_fhss = bool((chunk[17] >> 7) & 0x01)
        bandwidth = Bandwidth.WIDE if ((chunk[17] >> 6) & 0x01) else Bandwidth.NARROW
        encryption = (chunk[17] >> 4) & 0x03
        rx_modulation = Modulation.AM if (chunk[17] & 0x01) else Modulation.FM
        freq_band = chunk[18] & 0x0F
        step_freq = chunk[19] & 0x0F
        offset_hz = _decode_offset_frequency(chunk[20:27])
        entry = VFOSettings(
            rx_hz=rx_hz,
            offset_hz=offset_hz,
            rx_tone=rx_tone,
            tx_tone=tx_tone,
            busy_lockout=busy_lockout,
            offset_direction=offset_dir,
            signalling_group=signalling_group,
            tx_power=tx_power,
            scrambler=scrambler,
            learn_fhss=learn_fhss,
            bandwidth=bandwidth,
            encryption=encryption,
            rx_modulation=rx_modulation,
            freq_band=freq_band,
            step_freq_index=step_freq,
        )
        entry._raw_bytes = bytes(chunk)
        entry._original_state = entry._state_tuple()
        entries.append(entry)
    return entries


def parse_function_section(section: bytes) -> FunctionSettings:
    if len(section) != 96:
        raise ValueError("Function config section must be 96 bytes")
    part1 = section[0:32]
    part2 = section[32:64]
    part3 = section[64:96]
    values: Dict[str, Optional[int]] = {}

    def _masked(byte: int, mask: int = 0x0F, shift: int = 0) -> Optional[int]:
        if byte == 0xFF:
            return None
        return (byte >> shift) & mask

    def _set(name: str, byte: int, mask: int = 0x0F, shift: int = 0) -> None:
        values[name] = _masked(byte, mask, shift)

    _set("sql", part1[0])
    _set("save_mode", part1[1])
    _set("vox", part1[2])
    _set("auto_backlight", part1[3])
    _set("tdr", part1[4])
    _set("tot", part1[5])
    _set("beep_prompt", part1[6])
    _set("voice_prompt", part1[7])
    _set("language", part1[8])
    _set("dtmf_mode", part1[9])
    _set("scan_mode", part1[10])
    _set("ptt_id", part1[11])
    _set("send_id_delay", part1[12])
    _set("display_mode_a", part1[13])
    _set("display_mode_b", part1[14])
    _set("display_mode_c", part1[15])
    _set("auto_key_lock", part1[16])
    _set("alarm_mode", part1[17])
    _set("alarm_sound", part1[18])
    _set("tail_noise_clear", part1[20])
    _set("pass_repeater_noise_clear", part1[21])
    _set("pass_repeater_noise_detect", part1[22])
    _set("sound_tx_end", part1[23])
    _set("current_work_mode", part1[24])
    _set("fm_radio", part1[25])
    if part1[26] == 0xFF:
        values["work_mode_a"] = None
        values["work_mode_b"] = None
        values["work_mode_c"] = None
    else:
        values["work_mode_a"] = part1[26] & 0x03
        values["work_mode_b"] = (part1[26] >> 2) & 0x03
        values["work_mode_c"] = (part1[26] >> 4) & 0x03
    _set("lock_keyboard", part1[27])
    _set("power_on_message", part1[28])
    _set("bt_write_switch", part1[29])
    _set("rtone", part1[30])

    _set("vox_delay", part2[0])
    _set("timer_menu_quit", part2[1])
    _set("weather_channel", part2[5])
    _set("divide_channel", part2[6])
    _set("subaudio_scan_save", part2[7])
    _set("vox_switch", part2[8])
    _set("key_side1_short", part2[9])
    _set("key_side1_long", part2[10])
    _set("key_side2_short", part2[11])
    _set("key_side2_long", part2[12])
    _set("current_work_area_a", part2[13])
    _set("current_work_area_b", part2[14])
    _set("current_work_area_c", part2[15])
    _set("ab_uv_transfer", part2[25])
    _set("sound_transfer", part2[26])
    _set("key0_long", part2[27], mask=0x1F)
    _set("key1_long", part2[28], mask=0x1F)
    _set("key2_long", part2[29], mask=0x1F)
    _set("key3_long", part2[30], mask=0x1F)
    _set("key4_long", part2[31], mask=0x1F)

    _set("key5_long", part3[0], mask=0x1F)
    _set("key6_long", part3[1], mask=0x1F)
    _set("key7_long", part3[2], mask=0x1F)
    _set("key8_long", part3[3], mask=0x1F)
    _set("key9_long", part3[4], mask=0x1F)

    return FunctionSettings(values=values)




def parse_dtmf_section(section: bytes) -> DTMFSettings:
    if len(section) != 384:
        raise ValueError("DTMF section must be 384 bytes")
    info = section[0:32]
    groups = section[32:]
    current_id = _decode_dtmf_sequence(info[0:5])
    ptt_id = info[6] & 0x0F if info[6] != 0xFF else None
    last_send = info[7] & 0x0F if info[7] != 0xFF else None
    last_stop = info[8] & 0x0F if info[8] != 0xFF else None
    code_groups: List[str] = []
    for offset in range(0, len(groups), 16):
        code_groups.append(_decode_dtmf_sequence(groups[offset : offset + 16], max_len=6))
    return DTMFSettings(
        current_id=current_id,
        ptt_id_mode=ptt_id,
        last_time_send=last_send,
        last_time_stop=last_stop,
        code_groups=code_groups,
    )




def parse_modulation_sections(mod_block: bytes, name_block: bytes) -> ModulationSettings:
    if len(mod_block) != 256:
        raise ValueError("Modulation parameter block must be 256 bytes")
    if len(name_block) != 768:
        raise ValueError("Modulation name block must be 768 bytes")

    channels: List[ModulationChannelEntry] = []

    def _optional(value: int, modulus: int) -> Optional[int]:
        if value == 0xFF:
            return None
        return value % modulus

    fm_freqs = [_decode_le_uint16(mod_block, idx * 2) for idx in range(16)]
    fm_current = _optional(mod_block[32], 15)
    work_mode = _optional(mod_block[33], 2)
    am_freqs = [_decode_le_uint16(mod_block, 34 + idx * 2) for idx in range(16)]
    am_current = _optional(mod_block[66], 15)
    modulation_mode = _optional(mod_block[67], 5)
    am_rx_gain = _optional(mod_block[68], 37)
    ssb_freqs = []
    ssb_bandwidths = []
    ssb_offsets = []
    for idx in range(16):
        base = 69 + idx * 5
        ssb_freqs.append(_decode_le_uint16(mod_block, base))
        ssb_bandwidths.append(mod_block[base + 2])
        ssb_offsets.append(_decode_le_int16(mod_block, base + 3))
    ssb_current = _optional(mod_block[149], 15)
    ssb_step = _optional(mod_block[150], 6)
    am_step = _optional(mod_block[151], 4)
    ssb_rx_gain = _optional(mod_block[152], 37)

    fm_names = [_decode_gb2312(name_block, idx * 16) for idx in range(16)]
    am_names = [_decode_gb2312(name_block, 256 + idx * 16) for idx in range(16)]
    ssb_names = [_decode_gb2312(name_block, 512 + idx * 16) for idx in range(16)]

    for idx in range(16):
        channels.append(
            ModulationChannelEntry(
                fm_frequency=fm_freqs[idx],
                fm_name=fm_names[idx],
                am_frequency=am_freqs[idx],
                am_name=am_names[idx],
                ssb_frequency=ssb_freqs[idx],
                ssb_bandwidth=ssb_bandwidths[idx],
                ssb_beat_offset=ssb_offsets[idx],
                ssb_name=ssb_names[idx],
            )
        )

    return ModulationSettings(
        fm_current_channel=fm_current,
        am_current_channel=am_current,
        ssb_current_channel=ssb_current,
        work_mode=work_mode,
        modulation_mode=modulation_mode,
        am_step_index=am_step,
        am_rx_gain=am_rx_gain,
        ssb_step_index=ssb_step,
        ssb_rx_gain=ssb_rx_gain,
        channels=channels,
    )


def parse_aprs_section(section: bytes) -> APRSSettings:
    if len(section) != 128:
        raise ValueError("APRS section must be 128 bytes")
    data = section
    fields: Dict[str, Optional[object]] = {}

    def _set(name: str, idx: int, mask: int = 0x0F) -> None:
        byte = data[idx]
        if byte == 0xFF:
            fields[name] = None
        else:
            fields[name] = byte & mask

    _set("aprs_switch", 0)
    _set("gps_switch", 1)
    _set("latlon_unit", 2)
    _set("speed_unit", 3)
    _set("distance_unit", 4)
    _set("altitude_unit", 5)
    _set("time_zone", 6, mask=0x1F)
    north_byte = data[7]
    if north_byte == 0xFF:
        fields["north_south"] = None
    else:
        fields["north_south"] = 0 if north_byte == 0x4E else 1
    fields["latitude_minute"] = None if data[8] == 0xFF else min(59, data[8])
    fields["latitude_degree"] = None if data[9] == 0xFF else min(90, data[9])
    fields["latitude_second"] = None if data[10] == 0xFF else min(59, data[10])
    east_byte = data[11]
    if east_byte == 0xFF:
        fields["east_west"] = None
    else:
        fields["east_west"] = 0 if east_byte == 0x57 else 1
    fields["longitude_minute"] = None if data[12] == 0xFF else min(59, data[12])
    fields["longitude_degree"] = None if data[13] == 0xFF else min(180, data[13])
    fields["longitude_second"] = None if data[14] == 0xFF else min(59, data[14])
    alt_bytes = data[15:17]
    if all(b == 0xFF for b in alt_bytes):
        fields["altitude"] = None
    else:
        altitude = int.from_bytes(bytes(alt_bytes), "little", signed=True)
        fields["altitude"] = max(-10000, min(10000, altitude))

    fields["call_sign"] = _decode_ascii(data, 17, 6)
    _set("ssid", 23)
    _set("routing_select", 24)
    _set("my_position", 25)
    _set("radio_symbol", 26)
    if data[27] == 0xFF:
        fields["user_defined_icon"] = None
    else:
        fields["user_defined_icon"] = data[27] & 0x7F
    _set("aprs_priority", 29)
    _set("data_tx_delay", 30)
    _set("aprs_decode_prompt_tone", 32)
    _set("aprs_rx_auto_popup", 33)
    _set("beacon_tx_type", 34)
    _set("timed_beacon_time", 36)
    _set("mice_type", 38)
    _set("tnc_data_type", 39)
    _set("aprs_forward_channel", 40)
    _set("aprs_forward_routing", 41)
    _set("aprs_wait_forward", 42)
    fields["custom_routing_one"] = _decode_ascii(data, 43, 6)
    _set("custom_routing_one_ssid", 49)
    fields["custom_routing_two"] = _decode_ascii(data, 50, 6)
    _set("custom_routing_two_ssid", 56)
    _set("send_custom_messages", 78)
    fields["custom_messages"] = _decode_gb2312(data, 79, max_len=40)

    return APRSSettings(fields=fields)





# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def encode_vfo_section(vfos: Optional[List[VFOSettings]], raw: Optional[bytes]) -> bytes:
    """Encode the VFO section into its 96-byte representation."""

    if raw and len(raw) == 96:
        buffer = bytearray(raw)
    else:
        buffer = bytearray(b"\xFF" * 96)
    if not vfos:
        return bytes(buffer)
    mv = memoryview(buffer)
    for idx, entry in enumerate(vfos[:3]):
        start = idx * 32
        current_state = entry._state_tuple()
        if (
            entry._original_state is not None
            and current_state == entry._original_state
            and entry._raw_bytes
        ):
            mv[start : start + 32] = entry._raw_bytes
            continue
        source = (
            entry._raw_bytes if len(entry._raw_bytes) == 32 else bytes(mv[start : start + 32])
        )
        chunk = bytearray(source)
        if entry.rx_hz is not None:
            chunk[0:8] = _encode_vfo_frequency(entry.rx_hz)
        chunk[8:10] = entry.rx_tone.to_bytes()
        chunk[10:12] = entry.tx_tone.to_bytes()
        base13 = 0 if chunk[13] == 0xFF else chunk[13] & ~0x01
        chunk[13] = base13 | (0x01 if entry.busy_lockout else 0x00)
        preserved14 = 0 if chunk[14] == 0xFF else chunk[14] & 0xC0
        chunk[14] = (
            preserved14
            | ((entry.offset_direction & 0x03) << 4)
            | (entry.signalling_group & 0x0F)
        )
        chunk[16] = ((entry.scrambler & 0x0F) << 4) | (entry.tx_power.value & 0x0F)
        flags = 0 if chunk[17] == 0xFF else chunk[17] & ~(0x80 | 0x40 | 0x30 | 0x01)
        if entry.learn_fhss:
            flags |= 0x80
        if entry.bandwidth is Bandwidth.WIDE:
            flags |= 0x40
        flags |= (entry.encryption & 0x03) << 4
        if entry.rx_modulation is Modulation.AM:
            flags |= 0x01
        chunk[17] = flags
        preserved18 = 0 if chunk[18] == 0xFF else chunk[18] & 0xF0
        chunk[18] = preserved18 | (entry.freq_band & 0x0F)
        preserved19 = 0 if chunk[19] == 0xFF else chunk[19] & 0xF0
        chunk[19] = preserved19 | (entry.step_freq_index & 0x0F)
        if entry.offset_hz is not None:
            chunk[20:27] = _encode_offset_frequency(entry.offset_hz)
        encoded = bytes(chunk)
        mv[start : start + 32] = encoded
        entry._raw_bytes = encoded
        entry._original_state = entry._state_tuple()
    return bytes(buffer)


def encode_function_section(settings: Optional[FunctionSettings], raw: Optional[bytes]) -> bytes:
    """Serialise the 96-byte function configuration block."""

    if raw and len(raw) == 96:
        buffer = bytearray(raw)
    else:
        buffer = bytearray(b"\xFF" * 96)
    if settings is None:
        return bytes(buffer)
    part1 = memoryview(buffer)[0:32]
    part2 = memoryview(buffer)[32:64]
    part3 = memoryview(buffer)[64:96]
    values = settings.values

    def _set(part: memoryview, index: int, key: str, mask: int = 0x0F, shift: int = 0) -> None:
        value = values.get(key)
        if value is None:
            part[index] = 0xFF
            return
        encoded = (int(value) & mask) << shift
        current = part[index]
        if current == 0xFF:
            base = 0
        else:
            base = current & ~(mask << shift)
        part[index] = base | encoded

    _set(part1, 0, "sql")
    _set(part1, 1, "save_mode")
    _set(part1, 2, "vox")
    _set(part1, 3, "auto_backlight")
    _set(part1, 4, "tdr")
    _set(part1, 5, "tot")
    _set(part1, 6, "beep_prompt")
    _set(part1, 7, "voice_prompt")
    _set(part1, 8, "language")
    _set(part1, 9, "dtmf_mode")
    _set(part1, 10, "scan_mode")
    _set(part1, 11, "ptt_id")
    _set(part1, 12, "send_id_delay")
    _set(part1, 13, "display_mode_a")
    _set(part1, 14, "display_mode_b")
    _set(part1, 15, "display_mode_c")
    _set(part1, 16, "auto_key_lock")
    _set(part1, 17, "alarm_mode")
    _set(part1, 18, "alarm_sound")
    _set(part1, 20, "tail_noise_clear")
    _set(part1, 21, "pass_repeater_noise_clear")
    _set(part1, 22, "pass_repeater_noise_detect")
    _set(part1, 23, "sound_tx_end")
    _set(part1, 24, "current_work_mode")
    _set(part1, 25, "fm_radio")
    a = values.get("work_mode_a")
    b = values.get("work_mode_b")
    c = values.get("work_mode_c")
    if any(v is None for v in (a, b, c)):
        part1[26] = 0xFF
    else:
        preserved = 0 if part1[26] == 0xFF else part1[26] & 0xC0
        part1[26] = preserved | ((int(c) & 0x03) << 4) | ((int(b) & 0x03) << 2) | (int(a) & 0x03)
    _set(part1, 27, "lock_keyboard")
    _set(part1, 28, "power_on_message")
    _set(part1, 29, "bt_write_switch")
    _set(part1, 30, "rtone")

    _set(part2, 0, "vox_delay")
    _set(part2, 1, "timer_menu_quit")
    _set(part2, 5, "weather_channel")
    _set(part2, 6, "divide_channel")
    _set(part2, 7, "subaudio_scan_save")
    _set(part2, 8, "vox_switch")
    _set(part2, 9, "key_side1_short")
    _set(part2, 10, "key_side1_long")
    _set(part2, 11, "key_side2_short")
    _set(part2, 12, "key_side2_long")
    _set(part2, 13, "current_work_area_a")
    _set(part2, 14, "current_work_area_b")
    _set(part2, 15, "current_work_area_c")
    _set(part2, 25, "ab_uv_transfer")
    _set(part2, 26, "sound_transfer")
    _set(part2, 27, "key0_long", mask=0x1F)
    _set(part2, 28, "key1_long", mask=0x1F)
    _set(part2, 29, "key2_long", mask=0x1F)
    _set(part2, 30, "key3_long", mask=0x1F)
    _set(part2, 31, "key4_long", mask=0x1F)

    _set(part3, 0, "key5_long", mask=0x1F)
    _set(part3, 1, "key6_long", mask=0x1F)
    _set(part3, 2, "key7_long", mask=0x1F)
    _set(part3, 3, "key8_long", mask=0x1F)
    _set(part3, 4, "key9_long", mask=0x1F)

    return bytes(buffer)


def encode_dtmf_section(settings: Optional[DTMFSettings], raw: Optional[bytes]) -> bytes:
    """Encode DTMF identifiers and code groups into the 384-byte block."""

    if raw and len(raw) == 384:
        buffer = bytearray(raw)
    else:
        buffer = bytearray(b"\xFF" * 384)
    if settings is None:
        return bytes(buffer)
    info = memoryview(buffer)[0:32]
    groups = memoryview(buffer)[32:384]

    current_raw_id = _decode_dtmf_sequence(bytes(info[0:5]))
    if settings.current_id != current_raw_id:
        info[0:5] = _encode_dtmf_sequence(settings.current_id, 5)

    def _write_mode(index: int, value: Optional[int]) -> None:
        if value is None:
            info[index] = 0xFF
        else:
            current = info[index]
            base = 0 if current == 0xFF else current & 0xF0
            info[index] = base | (int(value) & 0x0F)

    _write_mode(6, settings.ptt_id_mode)
    _write_mode(7, settings.last_time_send)
    _write_mode(8, settings.last_time_stop)

    for idx in range(22):
        start = idx * 16
        seq = settings.code_groups[idx] if idx < len(settings.code_groups) else ""
        encoded = _encode_dtmf_sequence(seq, 6)
        chunk = bytearray(groups[start : start + 16])
        raw_sequence = _decode_dtmf_sequence(bytes(chunk[:16]), max_len=6)
        if seq == raw_sequence:
            continue
        chunk[0:6] = encoded
        chunk[6:16] = b"\xFF" * 10
        groups[start : start + 16] = chunk

    return bytes(buffer)


def encode_modulation_sections(
    settings: Optional[ModulationSettings],
    params_raw: Optional[bytes],
    names_raw: Optional[bytes],
) -> tuple[bytes, bytes]:
    """Serialise modulation parameter and name blocks."""

    params = bytearray(params_raw) if params_raw and len(params_raw) == 256 else bytearray(b"\xFF" * 256)
    names = bytearray(names_raw) if names_raw and len(names_raw) == 768 else bytearray(b"\xFF" * 768)
    if settings is None:
        return bytes(params), bytes(names)

    channels = settings.channels[:16]

    for idx, channel in enumerate(channels):
        start = idx * 2
        fm_bytes = _encode_le_uint16(channel.fm_frequency)
        if params[start : start + 2] != fm_bytes:
            params[start : start + 2] = fm_bytes

        am_start = 34 + idx * 2
        am_bytes = _encode_le_uint16(channel.am_frequency)
        if params[am_start : am_start + 2] != am_bytes:
            params[am_start : am_start + 2] = am_bytes

        base = 69 + idx * 5
        ssb_bytes = _encode_le_uint16(channel.ssb_frequency)
        if params[base : base + 2] != ssb_bytes:
            params[base : base + 2] = ssb_bytes
        bandwidth = channel.ssb_bandwidth & 0xFF
        if params[base + 2] != bandwidth:
            params[base + 2] = bandwidth
        beat_bytes = _encode_le_int16(channel.ssb_beat_offset)
        if params[base + 3 : base + 5] != beat_bytes:
            params[base + 3 : base + 5] = beat_bytes

        fm_name_offset = idx * 16
        fm_existing = _decode_gb2312(names, fm_name_offset, max_len=16)
        if fm_existing.rstrip('\x00') != channel.fm_name.rstrip('\x00'):
            names[fm_name_offset : fm_name_offset + 16] = _encode_gb2312(channel.fm_name, 16)

        am_name_offset = 256 + idx * 16
        am_existing = _decode_gb2312(names, am_name_offset, max_len=16)
        if am_existing.rstrip('\x00') != channel.am_name.rstrip('\x00'):
            names[am_name_offset : am_name_offset + 16] = _encode_gb2312(channel.am_name, 16)

        ssb_name_offset = 512 + idx * 16
        ssb_existing = _decode_gb2312(names, ssb_name_offset, max_len=16)
        if ssb_existing.rstrip('\x00') != channel.ssb_name.rstrip('\x00'):
            names[ssb_name_offset : ssb_name_offset + 16] = _encode_gb2312(channel.ssb_name, 16)

    for idx in range(len(channels), 16):
        params[idx * 2 : idx * 2 + 2] = b"\xFF\xFF"
        params[34 + idx * 2 : 34 + idx * 2 + 2] = b"\xFF\xFF"
        base = 69 + idx * 5
        params[base : base + 5] = b"\xFF" * 5
        names[idx * 16 : idx * 16 + 16] = b"\xFF" * 16
        names[256 + idx * 16 : 256 + idx * 16 + 16] = b"\xFF" * 16
        names[512 + idx * 16 : 512 + idx * 16 + 16] = b"\xFF" * 16

    def _write_param(index: int, value: Optional[int]) -> None:
        if value is None:
            return
        encoded_value = value & 0xFF
        if params[index] == 0xFF and encoded_value == 0:
            return
        params[index] = encoded_value

    _write_param(32, settings.fm_current_channel)
    _write_param(33, settings.work_mode)
    _write_param(66, settings.am_current_channel)
    _write_param(67, settings.modulation_mode)
    _write_param(68, settings.am_rx_gain)
    _write_param(149, settings.ssb_current_channel)
    _write_param(150, settings.ssb_step_index)
    _write_param(151, settings.am_step_index)
    _write_param(152, settings.ssb_rx_gain)

    return bytes(params), bytes(names)


def encode_aprs_section(settings: Optional[APRSSettings], raw: Optional[bytes]) -> bytes:
    """Encode APRS configuration into the 128-byte section."""

    if raw and len(raw) == 128:
        data = bytearray(raw)
    else:
        data = bytearray(b"\xFF" * 128)
    if settings is None:
        return bytes(data)

    fields = settings.fields

    def _set(idx: int, key: str, mask: int = 0x0F) -> None:
        value = fields.get(key)
        current = data[idx]
        if value is None:
            if current != 0xFF:
                data[idx] = 0xFF
            return
        encoded = int(value) & mask
        base = 0 if current == 0xFF else current & ~mask
        new_value = base | encoded
        if new_value != current:
            data[idx] = new_value

    _set(0, "aprs_switch")
    _set(1, "gps_switch")
    _set(2, "latlon_unit")
    _set(3, "speed_unit")
    _set(4, "distance_unit")
    _set(5, "altitude_unit")
    _set(6, "time_zone", mask=0x1F)

    north = fields.get("north_south")
    if north is None:
        data[7] = 0xFF
    else:
        data[7] = 0x4E if int(north) == 0 else 0x53

    data[8] = _encode_optional_bounded(fields.get("latitude_minute"), 59)
    data[9] = _encode_optional_bounded(fields.get("latitude_degree"), 90)
    data[10] = _encode_optional_bounded(fields.get("latitude_second"), 59)

    east = fields.get("east_west")
    if east is None:
        data[11] = 0xFF
    else:
        data[11] = 0x57 if int(east) == 0 else 0x45

    data[12] = _encode_optional_bounded(fields.get("longitude_minute"), 59)
    data[13] = _encode_optional_bounded(fields.get("longitude_degree"), 180)
    data[14] = _encode_optional_bounded(fields.get("longitude_second"), 59)

    altitude = fields.get("altitude")
    if altitude is None:
        data[15:17] = b"\xFF\xFF"
    else:
        alt = max(-10000, min(10000, int(altitude)))
        data[15:17] = alt.to_bytes(2, "little", signed=True)

    call_sign_value = fields.get("call_sign")
    raw_call_sign_bytes = data[17:23]
    raw_call_sign = _decode_ascii(data, 17, 6)
    if call_sign_value is None:
        if any(b != 0xFF for b in raw_call_sign_bytes):
            data[17:23] = _encode_ascii(None, 6)
    elif call_sign_value != raw_call_sign:
        data[17:23] = _encode_ascii(call_sign_value, 6)
    _set(23, "ssid")
    _set(24, "routing_select")
    _set(25, "my_position")
    _set(26, "radio_symbol")
    icon = fields.get("user_defined_icon")
    if icon is None:
        data[27] = 0xFF
    else:
        data[27] = int(icon) & 0x7F
    _set(29, "aprs_priority")
    _set(30, "data_tx_delay")
    _set(32, "aprs_decode_prompt_tone")
    _set(33, "aprs_rx_auto_popup")
    _set(34, "beacon_tx_type")
    _set(36, "timed_beacon_time")
    _set(38, "mice_type")
    _set(39, "tnc_data_type")
    _set(40, "aprs_forward_channel")
    _set(41, "aprs_forward_routing")
    _set(42, "aprs_wait_forward")
    custom_one = fields.get("custom_routing_one")
    raw_custom_one_bytes = data[43:49]
    raw_custom_one = _decode_ascii(data, 43, 6)
    if custom_one is None:
        if any(b != 0xFF for b in raw_custom_one_bytes):
            data[43:49] = _encode_ascii(None, 6)
    elif custom_one != raw_custom_one:
        data[43:49] = _encode_ascii(custom_one, 6)
    _set(49, "custom_routing_one_ssid")
    custom_two = fields.get("custom_routing_two")
    raw_custom_two_bytes = data[50:56]
    raw_custom_two = _decode_ascii(data, 50, 6)
    if custom_two is None:
        if any(b != 0xFF for b in raw_custom_two_bytes):
            data[50:56] = _encode_ascii(None, 6)
    elif custom_two != raw_custom_two:
        data[50:56] = _encode_ascii(custom_two, 6)
    _set(56, "custom_routing_two_ssid")
    _set(78, "send_custom_messages")
    custom_messages = fields.get("custom_messages")
    raw_custom_messages_bytes = data[79:119]
    raw_custom_messages = _decode_gb2312(data, 79, max_len=40)
    if custom_messages is None:
        if any(b != 0xFF for b in raw_custom_messages_bytes):
            data[79:119] = b"\xFF" * 40
    elif custom_messages != raw_custom_messages:
        data[79:119] = _encode_gb2312(custom_messages, 40)

    return bytes(data)


# ---------------------------------------------------------------------------
# Decode helpers
# ---------------------------------------------------------------------------

def _decode_vfo_frequency(digits: bytes) -> Optional[int]:
    if all(b in (0x00, 0xFF) for b in digits):
        return None
    value = int("".join(str(b) for b in digits))
    mhz = value / 100000.0
    return int(round(mhz * 1_000_000))


def _decode_offset_frequency(digits: bytes) -> Optional[int]:
    if all(b in (0x00, 0xFF) for b in digits):
        return None
    value = int("".join(str(b) for b in digits))
    mhz = value / 10000.0
    return int(round(mhz * 1_000_000))


def _decode_dtmf_sequence(data: bytes, *, max_len: int = 5) -> str:
    sequence = []
    for byte in data[:max_len]:
        if byte == 0xFF:
            break
        if 0 <= byte < len(_DTMF_DIGITS):
            sequence.append(_DTMF_DIGITS[byte])
    return "".join(sequence)


def _decode_le_uint16(buffer: bytes, offset: int) -> int:
    return int.from_bytes(buffer[offset : offset + 2], "little")


def _decode_le_int16(buffer: bytes, offset: int) -> int:
    return int.from_bytes(buffer[offset : offset + 2], "little", signed=True)


def _decode_gb2312(buffer: bytes, offset: int, max_len: int = 12) -> str:
    data = bytearray()
    consumed = 0
    buf_len = len(buffer)
    while consumed < max_len and (offset + consumed) < buf_len:
        byte = buffer[offset + consumed]
        if byte == 0xFF:
            break
        if (
            byte >= 0xA1
            and consumed + 1 < max_len
            and (offset + consumed + 1) < buf_len
        ):
            data.extend(buffer[offset + consumed : offset + consumed + 2])
            consumed += 2
        else:
            data.append(byte)
            consumed += 1
    if not data:
        return ""
    return bytes(data).decode("gb2312", errors="replace").strip()


def _decode_ascii(buffer: bytes, offset: int, max_len: int) -> str:
    length = 0
    buf_len = len(buffer)
    for idx in range(max_len):
        if (offset + idx) >= buf_len:
            break
        if buffer[offset + idx] in (0xFF, 0x00):
            break
        length += 1
    if length == 0:
        return ""
    return buffer[offset : offset + length].decode("ascii", errors="ignore").strip()


# ---------------------------------------------------------------------------
# Encode helper utilities
# ---------------------------------------------------------------------------

def _encode_vfo_frequency(hz: Optional[int]) -> bytes:
    if hz is None:
        return b"\xFF" * 8
    mhz = hz / 1_000_000.0
    digits = f"{mhz:0.5f}".replace(".", "")
    digits = digits[:8].rjust(8, "0")
    return bytes(int(ch) for ch in digits)


def _encode_offset_frequency(hz: Optional[int]) -> bytes:
    if hz is None:
        return b"\xFF" * 7
    value = int(round((hz / 1_000_000.0) * 10000))
    digits = f"{value:07d}"
    return bytes(int(ch) for ch in digits)


def _encode_dtmf_sequence(seq: str, max_len: int) -> bytes:
    out = bytearray(b"\xFF" * max_len)
    if not seq:
        return bytes(out)
    for idx, char in enumerate(seq[:max_len]):
        pos = _DTMF_DIGITS.find(char)
        if pos == -1:
            pos = _DTMF_DIGITS.find(char.upper())
        if pos == -1:
            continue
        out[idx] = pos
    return bytes(out)


def _encode_le_uint16(value: int) -> bytes:
    return int(max(0, value)).to_bytes(2, "little", signed=False)


def _encode_le_int16(value: int) -> bytes:
    return int(value).to_bytes(2, "little", signed=True)


def _encode_gb2312(text: Optional[str], max_len: int) -> bytes:
    if not text:
        return b"\xFF" * max_len
    encoded = text.encode("gb2312", errors="ignore")[:max_len]
    return encoded + b"\xFF" * (max_len - len(encoded))


def _encode_ascii(text: Optional[str], length: int) -> bytes:
    if not text:
        return b"\xFF" * length
    encoded = text.encode("ascii", errors="ignore")[:length]
    return encoded + b"\xFF" * (length - len(encoded))


def _encode_optional_bounded(value: Optional[object], maximum: int) -> int:
    if value is None:
        return 0xFF
    return min(maximum, int(value)) & 0xFF




