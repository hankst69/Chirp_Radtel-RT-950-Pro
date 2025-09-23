"""Parsed data structures for RT-950 Pro clone sections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .channel import Bandwidth, Modulation, PowerLevel, ToneSetting

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


@dataclass(slots=True)
class FunctionSettings:
    """Flat mapping of function configuration slots."""

    values: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class DTMFSettings:
    """Decoded DTMF settings and code groups."""

    current_id: str
    ptt_id_mode: int
    last_time_send: int
    last_time_stop: int
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

    fm_current_channel: int
    am_current_channel: int
    ssb_current_channel: int
    work_mode: int
    modulation_mode: int
    am_step_index: int
    am_rx_gain: int
    ssb_step_index: int
    ssb_rx_gain: int
    channels: List[ModulationChannelEntry]


@dataclass(slots=True)
class APRSSettings:
    """Decoded APRS settings."""

    fields: Dict[str, object] = field(default_factory=dict)


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
        entries.append(
            VFOSettings(
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
        )
    return entries


def parse_function_section(section: bytes) -> FunctionSettings:
    if len(section) != 96:
        raise ValueError("Function config section must be 96 bytes")
    part1 = section[0:32]
    part2 = section[32:64]
    part3 = section[64:96]
    values: Dict[str, int] = {}

    def _set(name: str, value: int) -> None:
        values[name] = value

    _set("sql", part1[0] & 0x0F)
    _set("save_mode", part1[1] & 0x0F)
    _set("vox", part1[2] & 0x0F)
    _set("auto_backlight", part1[3] & 0x0F)
    _set("tdr", part1[4] & 0x0F)
    _set("tot", part1[5] & 0x0F)
    _set("beep_prompt", part1[6] & 0x0F)
    _set("voice_prompt", part1[7] & 0x0F)
    _set("language", part1[8] & 0x0F)
    _set("dtmf_mode", part1[9] & 0x0F)
    _set("scan_mode", part1[10] & 0x0F)
    _set("ptt_id", part1[11] & 0x0F)
    _set("send_id_delay", part1[12] & 0x0F)
    _set("display_mode_a", part1[13] & 0x0F)
    _set("display_mode_b", part1[14] & 0x0F)
    _set("display_mode_c", part1[15] & 0x0F)
    _set("auto_key_lock", part1[16] & 0x0F)
    _set("alarm_mode", part1[17] & 0x0F)
    _set("alarm_sound", part1[18] & 0x0F)
    _set("tail_noise_clear", part1[20] & 0x0F)
    _set("pass_repeater_noise_clear", part1[21] & 0x0F)
    _set("pass_repeater_noise_detect", part1[22] & 0x0F)
    _set("sound_tx_end", part1[23] & 0x0F)
    _set("current_work_mode", part1[24] & 0x0F)
    _set("fm_radio", part1[25] & 0x0F)
    _set("work_mode_a", part1[26] & 0x03)
    _set("work_mode_b", (part1[26] >> 2) & 0x03)
    _set("work_mode_c", (part1[26] >> 4) & 0x03)
    _set("lock_keyboard", part1[27] & 0x0F)
    _set("power_on_message", part1[28] & 0x0F)
    _set("bt_write_switch", part1[29] & 0x0F)
    _set("rtone", part1[30] & 0x0F)

    _set("vox_delay", part2[0] & 0x0F)
    _set("timer_menu_quit", part2[1] & 0x0F)
    _set("weather_channel", part2[5] & 0x0F)
    _set("divide_channel", part2[6] & 0x0F)
    _set("subaudio_scan_save", part2[7] & 0x0F)
    _set("vox_switch", part2[8] & 0x0F)
    _set("key_side1_short", part2[9] & 0x0F)
    _set("key_side1_long", part2[10] & 0x0F)
    _set("key_side2_short", part2[11] & 0x0F)
    _set("key_side2_long", part2[12] & 0x0F)
    _set("current_work_area_a", part2[13] & 0x0F)
    _set("current_work_area_b", part2[14] & 0x0F)
    _set("current_work_area_c", part2[15] & 0x0F)
    _set("ab_uv_transfer", part2[25] & 0x0F)
    _set("sound_transfer", part2[26] & 0x0F)
    _set("key0_long", part2[27] & 0x1F)
    _set("key1_long", part2[28] & 0x1F)
    _set("key2_long", part2[29] & 0x1F)
    _set("key3_long", part2[30] & 0x1F)
    _set("key4_long", part2[31] & 0x1F)

    _set("key5_long", part3[0] & 0x1F)
    _set("key6_long", part3[1] & 0x1F)
    _set("key7_long", part3[2] & 0x1F)
    _set("key8_long", part3[3] & 0x1F)
    _set("key9_long", part3[4] & 0x1F)

    return FunctionSettings(values=values)


def parse_dtmf_section(section: bytes) -> DTMFSettings:
    if len(section) != 384:
        raise ValueError("DTMF section must be 384 bytes")
    info = section[0:32]
    groups = section[32:]
    current_id = _decode_dtmf_sequence(info[0:5])
    ptt_id = info[6] & 0x0F
    last_send = info[7] & 0x0F
    last_stop = info[8] & 0x0F
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
    fm_freqs = [_decode_le_uint16(mod_block, idx * 2) for idx in range(16)]
    fm_current = mod_block[32] % 15
    work_mode = mod_block[33] % 2
    am_freqs = [_decode_le_uint16(mod_block, 34 + idx * 2) for idx in range(16)]
    am_current = mod_block[66] % 15
    modulation_mode = mod_block[67] % 5
    am_rx_gain = mod_block[68] % 37
    ssb_freqs = []
    ssb_bandwidths = []
    ssb_offsets = []
    for idx in range(16):
        base = 69 + idx * 5
        ssb_freqs.append(_decode_le_uint16(mod_block, base))
        ssb_bandwidths.append(mod_block[base + 2] % 6)
        ssb_offsets.append(_decode_le_int16(mod_block, base + 3))
    ssb_current = mod_block[149] % 15
    ssb_step = mod_block[150] % 6
    am_step = mod_block[151] % 4
    ssb_rx_gain = mod_block[152] % 37

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
    fields: Dict[str, object] = {}

    def _set(name: str, value: object) -> None:
        fields[name] = value

    _set("aprs_switch", data[0] & 0x0F)
    _set("gps_switch", data[1] & 0x0F)
    _set("latlon_unit", data[2] & 0x0F)
    _set("speed_unit", data[3] & 0x0F)
    _set("distance_unit", data[4] & 0x0F)
    _set("altitude_unit", data[5] & 0x0F)
    _set("time_zone", data[6] & 0x1F)
    _set("north_south", 0 if data[7] == 0x4E else 1)
    _set("latitude_minute", min(59, data[8]))
    _set("latitude_degree", min(90, data[9]))
    _set("latitude_second", min(59, data[10]))
    _set("east_west", 0 if data[11] == 0x57 else 1)
    _set("longitude_minute", min(59, data[12]))
    _set("longitude_degree", min(180, data[13]))
    _set("longitude_second", min(59, data[14]))
    altitude = int.from_bytes(bytes(data[15:17]), "little", signed=True)
    altitude = max(-10000, min(10000, altitude))
    _set("altitude", altitude)
    _set("call_sign", _decode_ascii(data, 17, 6))
    _set("ssid", data[23] & 0x0F)
    _set("routing_select", data[24] & 0x0F)
    _set("my_position", data[25] & 0x0F)
    _set("radio_symbol", data[26] & 0x0F)
    _set("user_defined_icon", data[27] & 0x7F)
    _set("aprs_priority", data[29] & 0x0F)
    _set("data_tx_delay", data[30] & 0x0F)
    _set("aprs_decode_prompt_tone", data[32] & 0x0F)
    _set("aprs_rx_auto_popup", data[33] & 0x0F)
    _set("beacon_tx_type", data[34] & 0x0F)
    _set("timed_beacon_time", data[36] & 0x0F)
    _set("mice_type", data[38] & 0x0F)
    _set("tnc_data_type", data[39] & 0x0F)
    _set("aprs_forward_channel", data[40] & 0x0F)
    _set("aprs_forward_routing", data[41] & 0x0F)
    _set("aprs_wait_forward", data[42] & 0x0F)
    _set("custom_routing_one", _decode_ascii(data, 43, 6))
    _set("custom_routing_one_ssid", data[49] & 0x0F)
    _set("custom_routing_two", _decode_ascii(data, 50, 6))
    _set("custom_routing_two_ssid", data[56] & 0x0F)
    _set("send_custom_messages", data[78] & 0x0F)
    _set("custom_messages", _decode_gb2312(data, 79, max_len=40))

    return APRSSettings(fields=fields)


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
        if byte in (0xFF, 0x00):
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
        if byte in (0xFF, 0x00):
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



