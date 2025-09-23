"""Helpers for loading vendor CPS `.dat` files."""
from __future__ import annotations

__all__ = ["load_cps_radio", "CPSLoaderError"]

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional
import logging

from .channel import Bandwidth, ChannelRecord, Modulation, PowerLevel, ToneMode, ToneSetting
from .image import RadioImage
from .logging import get_logger

try:
    import clr  # type: ignore
except ImportError:  # pragma: no cover - pythonnet not installed
    clr = None

_LOG = get_logger("dat_loader")


class CPSLoaderError(RuntimeError):
    """Raised when a CPS `.dat` file cannot be converted."""


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
            "pythonnet is required to load CPS .dat files. Install via `pip install pythonnet`."
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
    """Load a vendor CPS `.dat` file and convert it to a :class:`RadioImage`.

    Parameters
    ----------
    path:
        Path to the `.dat` file produced by the vendor CPS.
    assembly_path:
        Optional explicit path to `BT-RT950PRO_CPS.exe`. When omitted the loader
        searches the repository `Reference/` directory.
    """

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
        raise CPSLoaderError("Assembly loaded but namespace `KDH` unavailable") from exc

    if not isinstance(radio_data, KDH.RadioData):  # type: ignore[attr-defined]
        raise CPSLoaderError(
            f"Unexpected object type {type(radio_data)} when loading CPS data"
        )

    channels = [
        _convert_channel(channel)
        for channel in radio_data.channelData  # type: ignore[attr-defined]
    ]
    return RadioImage(channels=channels, remainder=b"")


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
    name = getattr(channel, "ChName", "") or ""

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


def _parse_frequency(value: Optional[str]) -> Optional[int]:
    """Parse a frequency string (MHz) into integer Hertz."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        hz = int((Decimal(text) * Decimal("1000000")).to_integral_value())
    except Exception:  # noqa: BLE001
        _LOG.warning("Unable to parse frequency string '%s'", value)
        return None
    return hz


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


