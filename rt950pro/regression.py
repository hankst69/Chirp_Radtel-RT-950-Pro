"""Regression helpers comparing CPS `.dat` files with CSV exports."""
from __future__ import annotations

__all__ = ["compare_dat_to_csv", "ComparisonResult", "Difference", "ComparisonError"]

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .channel import Bandwidth, ChannelRecord, Modulation
from .dat_loader import CPSLoaderError, load_cps_radio
from .logging import get_logger

_LOG = get_logger("regression")


class ComparisonError(RuntimeError):
    """Raised when inputs for a regression comparison are invalid."""


@dataclass(frozen=True)
class Difference:
    """Represents a mismatch between CSV data and parsed CPS channel."""

    zone: int
    slot: int
    field: str
    expected: Optional[str]
    actual: Optional[str]


@dataclass
class ComparisonResult:
    """Summary of a CPS `.dat` versus CSV comparison."""

    total_channels: int
    mismatched_channels: int
    differences: List[Difference]


def compare_dat_to_csv(
    dat_path: Path,
    csv_path: Path,
    *,
    assembly_path: Optional[Path] = None,
    max_differences: Optional[int] = None,
) -> ComparisonResult:
    """Compare a CPS `.dat` file with a CSV export.

    Parameters
    ----------
    dat_path:
        Path to the CPS `.dat` file.
    csv_path:
        Path to the reference CSV export (as produced by the C# tool).
    assembly_path:
        Optional explicit path to `BT-RT950PRO_CPS.exe` for pythonnet.
    max_differences:
        Optional cap on the number of differences stored in the result.
    """

    if not dat_path.exists():
        raise ComparisonError(f"CPS .dat file not found: {dat_path}")
    if not csv_path.exists():
        raise ComparisonError(f"CSV file not found: {csv_path}")

    try:
        radio = load_cps_radio(dat_path, assembly_path=assembly_path)
    except CPSLoaderError as exc:
        raise ComparisonError(str(exc)) from exc

    csv_map = _load_csv(csv_path)
    differences: List[Difference] = []

    total = len(radio.channels)
    mismatched_slots: set[Tuple[int, int]] = set()

    for index, channel in enumerate(radio.channels):
        zone = (index // 64) + 1
        slot = (index % 64) + 1
        key = (zone, slot)
        csv_row = csv_map.get(key)
        if csv_row is None:
            diff = Difference(zone=zone, slot=slot, field="missing_csv", expected=None, actual=None)
            differences = _append_difference(differences, diff, max_differences)
            mismatched_slots.add(key)
            continue
        row_diffs = _diff_channel(csv_row, channel, zone, slot)
        if row_diffs:
            mismatched_slots.add(key)
            for diff in row_diffs:
                differences = _append_difference(differences, diff, max_differences)

    result = ComparisonResult(
        total_channels=total,
        mismatched_channels=len(mismatched_slots),
        differences=differences,
    )
    return result


def _append_difference(
    differences: List[Difference],
    diff: Difference,
    limit: Optional[int],
) -> List[Difference]:
    if limit is None or len(differences) < limit:
        differences.append(diff)
    return differences


def _load_csv(csv_path: Path) -> Dict[Tuple[int, int], Dict[str, str]]:
    mapping: Dict[Tuple[int, int], Dict[str, str]] = {}
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                zone = int(row["Zone"])
                slot = int(row["Slot"])
            except (KeyError, ValueError) as exc:
                raise ComparisonError(f"Invalid Zone/Slot in CSV row: {row}") from exc
            mapping[(zone, slot)] = row
    return mapping


def _diff_channel(
    row: Dict[str, str],
    channel: ChannelRecord,
    zone: int,
    slot: int,
) -> Iterable[Difference]:
    differences: List[Difference] = []

    def _add(field: str, expected: Optional[str], actual: Optional[str]):
        if expected != actual:
            differences.append(Difference(zone=zone, slot=slot, field=field, expected=expected, actual=actual))

    expected_name = row.get("ChName", "") or ""
    actual_name = channel.name or ""
    _add("ChName", expected_name, actual_name)

    expected_rx = _hz_from_csv(row.get("RxFreq", ""))
    actual_rx = channel.rx_hz
    _add("RxFreq", _format_hz(expected_rx), _format_hz(actual_rx))

    expected_tx = _hz_from_csv(row.get("TxFreq", ""))
    actual_tx = channel.tx_hz
    _add("TxFreq", _format_hz(expected_tx), _format_hz(actual_tx))

    expected_rx_tone = _normalise_tone(row.get("RxQT", ""))
    actual_rx_tone = channel.rx_tone.to_display()
    _add("RxQT", expected_rx_tone, actual_rx_tone)

    expected_tx_tone = _normalise_tone(row.get("TxQT", ""))
    actual_tx_tone = channel.tx_tone.to_display()
    _add("TxQT", expected_tx_tone, actual_tx_tone)

    _add("SignallingGroup", row.get("SignallingGroup", "0"), str(channel.signalling_group))
    _add("PttId", row.get("PttId", "0"), str(channel.ptt_id))
    _add("TxPower", row.get("TxPower", "0"), str(channel.power.value))
    _add("Scram", row.get("Scram", "0"), str(channel.scrambler))
    _add("LearnFHSS", row.get("LearnFHSS", "0"), _bool_to_str(channel.learn_fhss))

    expected_band = row.get("BandWide", "0")
    actual_band = "1" if channel.bandwidth is Bandwidth.WIDE else "0"
    _add("BandWide", expected_band, actual_band)

    _add("Encrypt", row.get("Encrypt", "0"), str(channel.encryption))
    _add("BusyLockout", row.get("BusyLockout", "0"), _bool_to_str(channel.busy_lockout))
    _add("ScanAdd", row.get("ScanAdd", "0"), _bool_to_str(channel.scan_add))
    _add("EnableTx", row.get("EnableTx", "0"), _bool_to_str(channel.tx_enabled))

    expected_mod = row.get("RxModulation", "0")
    actual_mod = "1" if channel.rx_modulation is Modulation.AM else "0"
    _add("RxModulation", expected_mod, actual_mod)

    expected_fhss = row.get("FhssCode", "") or ""
    actual_fhss = channel.fhss_code or ""
    _add("FhssCode", expected_fhss, actual_fhss)

    return differences


def _hz_from_csv(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        hz = int(round(float(text) * 1_000_000))
    except ValueError:
        _LOG.warning("Unable to parse frequency entry '%s'", value)
        return None
    return hz


def _format_hz(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    return f"{value / 1_000_000:.5f}".rstrip("0").rstrip(".")


def _normalise_tone(value: Optional[str]) -> str:
    text = (value or "").strip().upper()
    if not text:
        return "OFF"
    return text


def _bool_to_str(value: bool) -> str:
    return "1" if value else "0"
