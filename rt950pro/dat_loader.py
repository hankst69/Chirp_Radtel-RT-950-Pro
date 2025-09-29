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

"""Helpers for loading vendor CPS .dat files."""
from __future__ import annotations

__all__ = ["load_cps_radio", "CPSLoaderError"]

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional
import logging

from .channel import Bandwidth, ChannelRecord, Modulation, PowerLevel, ToneSetting
from .image import RadioImage
from .logging import get_logger
from .sections import (
    APRSSettings,
    DTMFSettings,
    FunctionSettings,
    ModulationChannelEntry,
    ModulationSettings,
    VFOSettings,
)

try:
    import clr  # type: ignore
except ImportError:  # pragma: no cover - pythonnet not installed
    clr = None

_LOG = get_logger("dat_loader")


class CPSLoaderError(RuntimeError):
    """Raised when a CPS .dat file cannot be converted."""


@dataclass(frozen=True)
class _LoaderConfig:
    assembly_path: Optional[Path]


_ASSEMBLY_LOADED = False
_CACHED_CONFIG: Optional[_LoaderConfig] = None


def _default_assembly_candidates() -> List[Path]:
    base = Path(__file__).resolve().parent.parent
    candidates: List[Path] = []
    candidates.append(base / "Reference" / "BT-RT950PRO_CPS" / "BT-RT950PRO_CPS.exe")
    candidates.append(base / "Reference" / "BT-RT950PRO_CPS" / "bin" / "BT-RT950PRO_CPS.exe")
    for exe in (base / "Reference" / "BT-RT950PRO_CPS").glob("**/BT-RT950PRO_CPS.exe"):
        if exe not in candidates:
            candidates.append(exe)
    return candidates


def _load_cps_assembly(assembly_path: Optional[Path] = None) -> None:
    global _ASSEMBLY_LOADED, _CACHED_CONFIG
    if _ASSEMBLY_LOADED:
        return
    if clr is None:
        raise CPSLoaderError(
            "pythonnet is required to load CPS .dat files. Install via pip install pythonnet."
        )
    candidates: Iterable[Path]
    if assembly_path is not None:
        candidates = [assembly_path]
    else:
        candidates = _default_assembly_candidates()
    for candidate in candidates:
        if candidate.exists():
            clr.AddReference(str(candidate))  # type: ignore[attr-defined]
            _ASSEMBLY_LOADED = True
            _CACHED_CONFIG = _LoaderConfig(candidate)
            return
    raise CPSLoaderError(
        "Unable to locate BT-RT950PRO CPS assembly. Provide a path to BT-RT950PRO_CPS.exe."
    )


def load_cps_radio(path: Path, *, assembly_path: Optional[Path] = None) -> RadioImage:
    """Load a vendor CPS .dat file and convert it to a :class:RadioImage."""

    _load_cps_assembly(assembly_path)
    if not path.exists():
        raise CPSLoaderError(f"CPS .dat file not found: {path}")

    from System.IO import FileAccess, FileMode, FileShare, FileStream  # type: ignore
    from System.Runtime.Serialization.Formatters.Binary import BinaryFormatter  # type: ignore

    formatter = BinaryFormatter()
    stream = FileStream(str(path), FileMode.Open, FileAccess.Read, FileShare.Read)
    try:
        radio_data = formatter.Deserialize(stream)
    except Exception as exc:  # noqa: BLE001
        raise CPSLoaderError(f"Failed to deserialize CPS file {path}: {exc}") from exc
    finally:
        stream.Close()

    try:
        import KDH  # type: ignore  # pylint: disable=import-error
    except ImportError as exc:  # pragma: no cover - unexpected if assembly loaded
        raise CPSLoaderError("Assembly loaded but namespace KDH unavailable") from exc

    if not isinstance(radio_data, KDH.RadioData):  # type: ignore[attr-defined]
        raise CPSLoaderError(
            f"Unexpected object type {type(radio_data)} when loading CPS data"
        )

    channels = [
        _convert_channel(channel)
        for channel in radio_data.channelData  # type: ignore[attr-defined]
    ]

    vfo = _convert_vfo_section(getattr(radio_data, "freqModeData", None))
    function = _convert_function_section(getattr(radio_data, "funConfigData", None))
    dtmf = _convert_dtmf_section(getattr(radio_data, "dtmfData", None))
    modulation = _convert_modulation_section(getattr(radio_data, "modulationData", None))
    aprs = _convert_aprs_section(getattr(radio_data, "aprsData", None))

    return RadioImage(
        channels=channels,
        vfo=vfo,
        function=function,
        dtmf=dtmf,
        modulation=modulation,
        aprs=aprs,
        remainder=b"",
    )


def _convert_channel(channel) -> ChannelRecord:  # type: ignore[return-type]
    """Convert a KDH.Channel instance into a ChannelRecord."""
    rx_hz = _parse_frequency(getattr(channel, "RxFreq", ""))
    tx_hz = _parse_frequency(getattr(channel, "TxFreq", ""))
    rx_tone = _parse_tone(getattr(channel, "RxQT", ""))
    tx_tone = _parse_tone(getattr(channel, "TxQT", ""))
    signalling_group = int(getattr(channel, "SignallingGroup", 0))
    ptt_id = int(getattr(channel, "PttId", 0))
    power = PowerLevel(min(max(int(getattr(channel, "TxPower", 0)), 0), 2))
    scrambler = int(getattr(channel, "Scram", 0)) & 0x0F
    learn_fhss = bool(int(getattr(channel, "LearnFHSS", 0)))
    bandwidth = Bandwidth.WIDE if int(getattr(channel, "BandWide", 0)) else Bandwidth.NARROW
    encryption = int(getattr(channel, "Encrypt", 0)) & 0x03
    busy_lockout = bool(int(getattr(channel, "BusyLockout", 0)))
    scan_add = bool(int(getattr(channel, "ScanAdd", 0)))
    tx_enabled = bool(int(getattr(channel, "EnableTx", 1)))
    rx_modulation = Modulation.AM if int(getattr(channel, "RxModulation", 0)) else Modulation.FM
    fhss_code = getattr(channel, "FHSSCode", None) or None
    name = (getattr(channel, "ChName", "") or "").strip()

    return ChannelRecord(
        rx_hz=rx_hz,
        tx_hz=tx_hz,
        rx_tone=rx_tone,
        tx_tone=tx_tone,
        signalling_group=signalling_group,
        ptt_id=ptt_id,
        power=power,
        scrambler=scrambler,
        learn_fhss=learn_fhss,
        bandwidth=bandwidth,
        encryption=encryption,
        busy_lockout=busy_lockout,
        scan_add=scan_add,
        tx_enabled=tx_enabled,
        rx_modulation=rx_modulation,
        fhss_code=fhss_code,
        name=name,
    )


def _convert_vfo_section(freq_mode_data) -> Optional[List[VFOSettings]]:  # type: ignore[valid-type]
    if freq_mode_data is None:
        return None
    vfo_entries = []
    for vfo in [freq_mode_data.VfoA, freq_mode_data.VfoB, freq_mode_data.VfoC]:  # type: ignore[attr-defined]
        rx_hz = _parse_frequency(getattr(vfo, "TB_RxFreq", ""))
        offset_hz = _parse_offset(getattr(vfo, "TB_OffsetFreq", ""))
        rx_tone = _parse_tone(getattr(vfo, "CbB_RxQT", ""))
        tx_tone = _parse_tone(getattr(vfo, "CbB_TxQT", ""))
        offset_dir = int(getattr(vfo, "CbB_OffsetDir", 0))
        signalling_group = int(getattr(vfo, "CbB_SignallingGroup", 0))
        busy_lockout = bool(int(getattr(vfo, "CbB_BusyLockout", 0)))
        tx_power = PowerLevel(min(max(int(getattr(vfo, "CbB_TxPower", 0)), 0), 2))
        scrambler = int(getattr(vfo, "CbB_Scram", 0)) & 0x0F
        learn_fhss = bool(int(getattr(vfo, "CbB_LearnFHSS", 0)))
        bandwidth = Bandwidth.WIDE if int(getattr(vfo, "CbB_BandWide", 0)) else Bandwidth.NARROW
        encryption = int(getattr(vfo, "CbB_Encrypt", 0)) & 0x03
        rx_modulation = Modulation.AM if int(getattr(vfo, "CbB_RxModulation", 0)) else Modulation.FM
        freq_band = int(getattr(vfo, "CbB_FreqBand", 0))
        step_idx = int(getattr(vfo, "CbB_StepFreq", 0))
        vfo_entries.append(
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
                step_freq_index=step_idx,
            )
        )
    return vfo_entries


def _convert_function_section(fun_config) -> Optional[FunctionSettings]:  # type: ignore[valid-type]
    if fun_config is None:
        return None
    values = {
        "sql": int(getattr(fun_config, "CbB_SQL", 0)),
        "save_mode": int(getattr(fun_config, "CbB_SaveMode", 0)),
        "vox": int(getattr(fun_config, "CbB_VOX", 0)),
        "auto_backlight": int(getattr(fun_config, "CbB_AutoBacklight", 0)),
        "tdr": int(getattr(fun_config, "CbB_TDR", 0)),
        "tot": int(getattr(fun_config, "CbB_TOT", 0)),
        "beep_prompt": int(getattr(fun_config, "CbB_BeepPrompt", 0)),
        "voice_prompt": int(getattr(fun_config, "CbB_VoicePrompt", 0)),
        "language": int(getattr(fun_config, "CbB_Language", 0)),
        "dtmf_mode": int(getattr(fun_config, "CbB_DTMF", 0)),
        "scan_mode": int(getattr(fun_config, "CbB_Scan", 0)),
        "ptt_id": int(getattr(fun_config, "CbB_PTTID", 0)),
        "send_id_delay": int(getattr(fun_config, "CbB_SendIDDelay", 0)),
        "display_mode_a": int(getattr(fun_config, "CbB_DisplayModeA", 0)),
        "display_mode_b": int(getattr(fun_config, "CbB_DisplayModeB", 0)),
        "display_mode_c": int(getattr(fun_config, "CbB_DisplayModeC", 0)),
        "auto_key_lock": int(getattr(fun_config, "CbB_AutoKeyLock", 0)),
        "alarm_mode": int(getattr(fun_config, "CbB_AlarmMode", 0)),
        "alarm_sound": int(getattr(fun_config, "CbB_AlarmSound", 0)),
        "tail_noise_clear": int(getattr(fun_config, "CbB_TailNoiseClear", 0)),
        "pass_repeater_noise_clear": int(getattr(fun_config, "CbB_PassRepetNoiseClear", 0)),
        "pass_repeater_noise_detect": int(getattr(fun_config, "CbB_PassRepetNoiseDetect", 0)),
        "sound_tx_end": int(getattr(fun_config, "CbB_SoundTxEnd", 0)),
        "current_work_mode": int(getattr(fun_config, "CbB_CurWorkMode", 0)),
        "fm_radio": int(getattr(fun_config, "CbB_FMRadio", 0)),
        "work_mode_a": int(getattr(fun_config, "CbB_WorkModeA", 0)),
        "work_mode_b": int(getattr(fun_config, "CbB_WorkModeB", 0)),
        "work_mode_c": int(getattr(fun_config, "CbB_WorkModeC", 0)),
        "lock_keyboard": int(getattr(fun_config, "CbB_LockKeyBoard", 0)),
        "power_on_message": int(getattr(fun_config, "CbB_PowerMsg", 0)),
        "bt_write_switch": int(getattr(fun_config, "CbB_BTWriteSwitch", 0)),
        "rtone": int(getattr(fun_config, "CbB_RTone", 0)),
        "vox_delay": int(getattr(fun_config, "CbB_VoxDelay", 0)),
        "timer_menu_quit": int(getattr(fun_config, "CbB_TimerMenuQuit", 0)),
        "weather_channel": int(getattr(fun_config, "CbB_WeatherCH", 0)),
        "divide_channel": int(getattr(fun_config, "CbB_DivideCH", 0)),
        "subaudio_scan_save": int(getattr(fun_config, "CbB_SubaudioScanSave", 0)),
        "vox_switch": int(getattr(fun_config, "CbB_VOXSwitch", 0)),
        "key_side1_short": int(getattr(fun_config, "CbB_KeySide1", 0)),
        "key_side1_long": int(getattr(fun_config, "CbB_KeySide1L", 0)),
        "key_side2_short": int(getattr(fun_config, "CbB_KeySide2", 0)),
        "key_side2_long": int(getattr(fun_config, "CbB_KeySide2L", 0)),
        "current_work_area_a": int(getattr(fun_config, "CbB_CurWorkAreaA", 0)),
        "current_work_area_b": int(getattr(fun_config, "CbB_CurWorkAreaB", 0)),
        "current_work_area_c": int(getattr(fun_config, "CbB_CurWorkAreaC", 0)),
        "ab_uv_transfer": int(getattr(fun_config, "CbB_ABUVTransfer", 0)),
        "sound_transfer": int(getattr(fun_config, "CbB_SoundTransfer", 0)),
        "key0_long": int(getattr(fun_config, "CbB_Key0L", 0)),
        "key1_long": int(getattr(fun_config, "CbB_Key1L", 0)),
        "key2_long": int(getattr(fun_config, "CbB_Key2L", 0)),
        "key3_long": int(getattr(fun_config, "CbB_Key3L", 0)),
        "key4_long": int(getattr(fun_config, "CbB_Key4L", 0)),
        "key5_long": int(getattr(fun_config, "CbB_Key5L", 0)),
        "key6_long": int(getattr(fun_config, "CbB_Key6L", 0)),
        "key7_long": int(getattr(fun_config, "CbB_Key7L", 0)),
        "key8_long": int(getattr(fun_config, "CbB_Key8L", 0)),
        "key9_long": int(getattr(fun_config, "CbB_Key9L", 0)),
    }
    return FunctionSettings(values=values)


def _convert_dtmf_section(dtmf_data) -> Optional[DTMFSettings]:  # type: ignore[valid-type]
    if dtmf_data is None:
        return None
    current_id = _strip(getattr(dtmf_data, "TB_DTMFCurId", ""))
    ptt_mode = int(getattr(dtmf_data, "CbB_PTTID", 0))
    last_send = int(getattr(dtmf_data, "CbB_LastTimeSend", 0))
    last_stop = int(getattr(dtmf_data, "CbB_LastTimeStop", 0))
    code_groups = [_strip(code) for code in getattr(dtmf_data, "DTMFCodeGroup", [])]
    return DTMFSettings(
        current_id=current_id,
        ptt_id_mode=ptt_mode,
        last_time_send=last_send,
        last_time_stop=last_stop,
        code_groups=code_groups,
    )


def _convert_modulation_section(modulation_data) -> Optional[ModulationSettings]:  # type: ignore[valid-type]
    if modulation_data is None:
        return None
    channels: List[ModulationChannelEntry] = []
    for channel in getattr(modulation_data, "ModulationChannels", []):
        channels.append(
            ModulationChannelEntry(
                fm_frequency=_to_int(getattr(channel, "FMFreq", 0), allow_none=True) or 0,
                fm_name=_strip(getattr(channel, "FMName", "")),
                am_frequency=_to_int(getattr(channel, "AMFreq", 0), allow_none=True) or 0,
                am_name=_strip(getattr(channel, "AMName", "")),
                ssb_frequency=_to_int(getattr(channel, "SSBFreq", 0), allow_none=True) or 0,
                ssb_bandwidth=_to_int(getattr(channel, "SSBBandwidth", 0), allow_none=True) or 0,
                ssb_beat_offset=_to_int(getattr(channel, "SSBBeatFreqOffset", 0), allow_none=True) or 0,
                ssb_name=_strip(getattr(channel, "SSBName", "")),
            )
        )
    return ModulationSettings(
        fm_current_channel=int(getattr(modulation_data, "CbB_FMCurChID", 0)),
        am_current_channel=int(getattr(modulation_data, "CbB_AMCurChID", 0)),
        ssb_current_channel=int(getattr(modulation_data, "CbB_SSBCurChID", 0)),
        work_mode=int(getattr(modulation_data, "CbB_WorkMode", 0)),
        modulation_mode=int(getattr(modulation_data, "CbB_ModulationMode", 0)),
        am_step_index=int(getattr(modulation_data, "CbB_AMStepFreq", 0)),
        am_rx_gain=int(getattr(modulation_data, "CbB_AMRxGain", 0)),
        ssb_step_index=int(getattr(modulation_data, "CbB_SSBStepFreq", 0)),
        ssb_rx_gain=int(getattr(modulation_data, "CbB_SSBRxGain", 0)),
        channels=channels,
    )


def _convert_aprs_section(aprs_data) -> Optional[APRSSettings]:  # type: ignore[valid-type]
    if aprs_data is None:
        return None
    fields = {
        "aprs_switch": int(getattr(aprs_data, "CbB_AprsSwitch", 0)),
        "gps_switch": int(getattr(aprs_data, "CbB_GpsSwitch", 0)),
        "latlon_unit": int(getattr(aprs_data, "CbB_LatitudeLongitudeUnit", 0)),
        "speed_unit": int(getattr(aprs_data, "CbB_SpeedUnit", 0)),
        "distance_unit": int(getattr(aprs_data, "CbB_DistanceUnit", 0)),
        "altitude_unit": int(getattr(aprs_data, "CbB_AltitudeUnit", 0)),
        "time_zone": int(getattr(aprs_data, "CbB_TimeZone", 0)),
        "north_south": int(getattr(aprs_data, "CbB_NorthSouthLatitude", 0)),
        "latitude_degree": _to_int(getattr(aprs_data, "NUD_LatitudeDegree", 0), allow_none=True),
        "latitude_minute": _to_int(getattr(aprs_data, "NUD_LatitudeMinute", 0), allow_none=True),
        "latitude_second": _to_int(getattr(aprs_data, "NUD_LatitudeSecond", 0), allow_none=True),
        "east_west": int(getattr(aprs_data, "CbB_EastWestLongitude", 0)),
        "longitude_degree": _to_int(getattr(aprs_data, "NUD_LongitudeDegree", 0), allow_none=True),
        "longitude_minute": _to_int(getattr(aprs_data, "NUD_LongitudeMinute", 0), allow_none=True),
        "longitude_second": _to_int(getattr(aprs_data, "NUD_LongitudeSecond", 0), allow_none=True),
        "altitude": _to_int(getattr(aprs_data, "NUD_Altitude", 0), allow_none=True),
        "call_sign": _strip(getattr(aprs_data, "TB_CallSign", "")),
        "ssid": int(getattr(aprs_data, "CbB_SSID", 0)),
        "routing_select": int(getattr(aprs_data, "CbB_RoutingSelect", 0)),
        "my_position": int(getattr(aprs_data, "CbB_MyPosition", 0)),
        "radio_symbol": int(getattr(aprs_data, "CbB_RadioSymbol", 0)),
        "user_defined_icon": int(getattr(aprs_data, "CbB_UserDefinedIcon", 0)),
        "aprs_priority": int(getattr(aprs_data, "CbB_AprsPriority", 0)),
        "data_tx_delay": int(getattr(aprs_data, "CbB_DataTxDelay", 0)),
        "aprs_decode_prompt_tone": int(getattr(aprs_data, "CbB_AprsDecodePromptTone", 0)),
        "aprs_rx_auto_popup": int(getattr(aprs_data, "CbB_AprsRxAutoPopUp", 0)),
        "beacon_tx_type": int(getattr(aprs_data, "CbB_BeaconTxType", 0)),
        "timed_beacon_time": int(getattr(aprs_data, "CbB_TimedBeaconTime", 0)),
        "mice_type": int(getattr(aprs_data, "CbB_MicEType", 0)),
        "tnc_data_type": int(getattr(aprs_data, "CbB_TncDataType", 0)),
        "aprs_forward_channel": int(getattr(aprs_data, "CbB_AprsForwardChannel", 0)),
        "aprs_forward_routing": int(getattr(aprs_data, "CbB_AprsForwardRouting", 0)),
        "aprs_wait_forward": int(getattr(aprs_data, "CbB_AprsWaitForward", 0)),
        "custom_routing_one": _strip(getattr(aprs_data, "TB_CustomRoutingOne", "")),
        "custom_routing_one_ssid": int(getattr(aprs_data, "CbB_CustomRoutingOneSSID", 0)),
        "custom_routing_two": _strip(getattr(aprs_data, "TB_CustomRoutingTwo", "")),
        "custom_routing_two_ssid": int(getattr(aprs_data, "CbB_CustomRoutingTwoSSID", 0)),
        "send_custom_messages": int(getattr(aprs_data, "CbB_SendCustomMessages", 0)),
        "custom_messages": _strip(getattr(aprs_data, "TB_CustomMessages", "")),
    }
    return APRSSettings(fields=fields)


def _parse_frequency(value: Optional[str]) -> Optional[int]:
    """Parse a frequency string (MHz) into integer Hertz."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        hz = int((Decimal(text) * Decimal("1000000")).to_integral_value())
    except Exception:
        _LOG.warning("Unable to parse frequency string '%s'", value)
        return None
    return hz


def _parse_offset(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        hz = int((Decimal(text) * Decimal("1000000")).to_integral_value())
    except Exception:
        return None
    return None if hz == 0 else hz


def _parse_tone(value: Optional[str]) -> ToneSetting:
    """Convert a CPS tone string into a ToneSetting."""
    if not value:
        return ToneSetting.off()
    text = value.strip().upper()
    if not text or text == "OFF":
        return ToneSetting.off()
    if text.startswith("D") and len(text) >= 5:
        try:
            code = int(text[1:4])
        except ValueError:
            _LOG.warning("Invalid DCS format '%s'", value)
            return ToneSetting.off()
        polarity = text[4]
        try:
            return ToneSetting.dcs(code, polarity)
        except ValueError:
            _LOG.warning("Unsupported DCS code '%s'", value)
            return ToneSetting.off()
    try:
        hz = float(text)
    except ValueError:
        _LOG.warning("Invalid CTCSS value '%s'", value)
        return ToneSetting.off()
    return ToneSetting.ctcss(hz)


def _to_int(value, *, allow_none: bool = False):
    if value is None:
        return None if allow_none else 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(float(value))
    except Exception:
        return None if allow_none else 0


def _strip(value) -> str:
    if value is None:
        return ""
    return str(value).strip()
