"""Command line harness entry point for development."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .channel import ChannelRecord
from .dat_loader import CPSLoaderError, load_cps_radio
from .image import RadioImage
from .logging import configure_logging, log_mock_warning
from .regression import ComparisonError, compare_dat_to_csv


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser for the harness."""

    parser = argparse.ArgumentParser(description="RT-950 Pro development harness")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Increase logging verbosity (DEBUG on console)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce logging verbosity (WARN on console)",
    )

    subparsers = parser.add_subparsers(dest="command")

    channel_parser = subparsers.add_parser("channel", help="Channel record utilities")
    channel_sub = channel_parser.add_subparsers(dest="channel_command")

    decode_parser = channel_sub.add_parser("decode", help="Decode a 32-byte channel blob")
    decode_parser.add_argument(
        "input",
        help="Path to binary file containing 32 bytes or a hex string when --hex is supplied",
    )
    decode_parser.add_argument(
        "--hex",
        action="store_true",
        help="Treat input argument as a hex string instead of a file path",
    )

    encode_parser = channel_sub.add_parser("encode", help="Encode a channel to bytes (placeholder)")
    encode_parser.add_argument(
        "input",
        help="Path to JSON description of a channel (not yet implemented)",
    )

    image_parser = subparsers.add_parser("image", help="Radio image utilities")
    image_sub = image_parser.add_subparsers(dest="image_command")

    summary_parser = image_sub.add_parser("summary", help="Summarise a raw clone image")
    summary_parser.add_argument("input", help="Path to a raw clone image dump")
    summary_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of populated channels to include in the output (default: 10)",
    )

    dat_parser = image_sub.add_parser("dat-summary", help="Summarise a vendor CPS .dat file")
    dat_parser.add_argument("input", help="Path to a CPS .dat file")
    dat_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of populated channels to include in the output (default: 10)",
    )
    dat_parser.add_argument(
        "--assembly",
        type=str,
        default=None,
        help="Optional explicit path to BT-RT950PRO_CPS.exe",
    )

    regression_parser = subparsers.add_parser("regression", help="Regression utilities")
    regression_sub = regression_parser.add_subparsers(dest="regression_command")

    compare_parser = regression_sub.add_parser(
        "dat-csv",
        help="Compare a CPS .dat file against a CSV export",
    )
    compare_parser.add_argument("dat", help="Path to the CPS .dat file")
    compare_parser.add_argument("csv", help="Path to the reference CSV")
    compare_parser.add_argument(
        "--assembly",
        type=str,
        default=None,
        help="Optional path to BT-RT950PRO_CPS.exe",
    )
    compare_parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of differences to report (default: 25)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point used by ``python -m rt950pro``."""

    parser = build_parser()
    args = parser.parse_args(argv)

    logger = configure_logging(verbose=args.verbose, quiet=args.quiet)

    if args.command == "channel":
        if args.channel_command == "decode":
            return _cmd_channel_decode(args.input, treat_as_hex=args.hex, logger=logger)
        if args.channel_command == "encode":
            logger.warning("Channel encoding CLI not yet implemented")
            log_mock_warning(logger, "channel encode command")
            return 2
    elif args.command == "image":
        if args.image_command == "summary":
            return _cmd_image_summary(Path(args.input), limit=args.limit, logger=logger)
        if args.image_command == "dat-summary":
            assembly = Path(args.assembly) if args.assembly else None
            return _cmd_image_dat_summary(Path(args.input), limit=args.limit, assembly=assembly, logger=logger)
    elif args.command == "regression":
        if args.regression_command == "dat-csv":
            assembly = Path(args.assembly) if args.assembly else None
            return _cmd_regression_dat_csv(Path(args.dat), Path(args.csv), assembly=assembly, limit=args.limit, logger=logger)
    parser.print_help()
    return 1


def _cmd_channel_decode(input_arg: str, *, treat_as_hex: bool, logger) -> int:
    """Decode a single 32-byte channel record and dump a JSON summary."""

    try:
        data = _read_channel_bytes(input_arg, treat_as_hex)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    try:
        record = ChannelRecord.from_bytes(data, logger=logger)
    except ValueError as exc:
        logger.error("Failed to decode channel record: %s", exc)
        return 2

    payload = _channel_to_dict(record)
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_image_summary(path: Path, *, limit: int, logger) -> int:
    """Produce a JSON summary for the first populated channels in ``path``."""

    try:
        image = RadioImage.from_file(path, logger=logger)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    payload = _build_image_summary(image, limit)
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_image_dat_summary(path: Path, *, limit: int, assembly: Optional[Path], logger) -> int:
    """Summarise channels stored in a vendor CPS `.dat` file."""

    try:
        image = load_cps_radio(path, assembly_path=assembly)
    except CPSLoaderError as exc:
        logger.error("%s", exc)
        return 2

    payload = _build_image_summary(image, limit)
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_regression_dat_csv(
    dat_path: Path,
    csv_path: Path,
    *,
    assembly: Optional[Path],
    limit: int,
    logger,
) -> int:
    """Compare a CPS `.dat` file against a CSV export and report differences."""

    try:
        result = compare_dat_to_csv(dat_path, csv_path, assembly_path=assembly, max_differences=limit)
    except ComparisonError as exc:
        logger.error("%s", exc)
        return 2

    payload = {
        "total_channels": result.total_channels,
        "mismatched_channels": result.mismatched_channels,
        "differences": [
            {
                "zone": diff.zone,
                "slot": diff.slot,
                "field": diff.field,
                "expected": diff.expected,
                "actual": diff.actual,
            }
            for diff in result.differences
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _build_image_summary(image: RadioImage, limit: int) -> dict[str, object]:
    """Create a summary payload from a :class:`RadioImage`."""

    entries = []
    for index, channel in image.iter_populated_channels():
        entries.append(
            {
                "index": index,
                "rx_hz": channel.rx_hz,
                "tx_hz": channel.tx_hz,
                "name": channel.name,
                "power": channel.power.name,
                "bandwidth": channel.bandwidth.name,
            }
        )
        if limit and len(entries) >= limit:
            break

    return {
        "channels_reported": len(entries),
        "empty_slots": len(image.empty_slot_indexes()),
        "entries": entries,
    }


def _read_channel_bytes(input_arg: str, treat_as_hex: bool) -> bytes:
    """Load raw channel bytes either from a file or from a hex string."""

    if treat_as_hex:
        cleaned = "".join(ch for ch in input_arg if ch not in {" ", "\t", "\n", "\r"})
        if len(cleaned) != 64:
            raise ValueError("Hex input must contain exactly 64 characters (32 bytes)")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError("Input is not valid hexadecimal data") from exc
    path = Path(input_arg)
    if not path.exists():
        raise ValueError(f"Channel input file not found: {path}")
    data = path.read_bytes()
    if len(data) != 32:
        raise ValueError(f"Channel input must be exactly 32 bytes; got {len(data)}")
    return data


def _channel_to_dict(record: ChannelRecord) -> dict[str, object]:
    """Convert a :class:`ChannelRecord` into a JSON-friendly payload."""

    return {
        "rx_hz": record.rx_hz,
        "tx_hz": record.tx_hz,
        "rx_tone": {
            "mode": record.rx_tone.mode.value,
            "display": record.rx_tone.to_display(),
            "ctcss_hz": record.rx_tone.ctcss_hz,
            "dcs_code": record.rx_tone.dcs_code,
            "dcs_polarity": record.rx_tone.dcs_polarity,
        },
        "tx_tone": {
            "mode": record.tx_tone.mode.value,
            "display": record.tx_tone.to_display(),
            "ctcss_hz": record.tx_tone.ctcss_hz,
            "dcs_code": record.tx_tone.dcs_code,
            "dcs_polarity": record.tx_tone.dcs_polarity,
        },
        "signalling_group": record.signalling_group,
        "ptt_id": record.ptt_id,
        "power": record.power.name,
        "scrambler": record.scrambler,
        "learn_fhss": record.learn_fhss,
        "bandwidth": record.bandwidth.name,
        "encryption": record.encryption,
        "busy_lockout": record.busy_lockout,
        "scan_add": record.scan_add,
        "tx_enabled": record.tx_enabled,
        "rx_modulation": record.rx_modulation.name,
        "fhss_code": record.fhss_code,
        "name": record.name,
    }
