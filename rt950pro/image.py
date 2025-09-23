"""Representation of RT-950 Pro radio images."""
from __future__ import annotations

__all__ = ["CHANNEL_COUNT", "CHANNEL_SIZE", "CHANNEL_SECTION_BYTES", "RadioImage"]

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
import logging

from .channel import ChannelRecord
from .logging import get_logger

_CHANNEL_LOG = get_logger("image")

CHANNEL_COUNT = 960
"""Total number of memory channels supported by the radio."""

CHANNEL_SIZE = 32
"""Size in bytes of a single channel record."""

CHANNEL_SECTION_BYTES = CHANNEL_COUNT * CHANNEL_SIZE
"""Total byte length of the channel section within the clone image."""


def _chunk(iterable: Sequence[int], size: int) -> Iterable[bytes]:
    """Yield fixed-size chunks from ``iterable`` using the provided ``size``."""

    for i in range(0, len(iterable), size):
        chunk = iterable[i : i + size]
        if len(chunk) == size:
            yield bytes(chunk)


@dataclass
class RadioImage:
    """Container for channel records and the untouched remainder bytes."""

    channels: List[ChannelRecord]
    remainder: bytes

    @classmethod
    def from_bytes(
        cls,
        blob: bytes,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> "RadioImage":
        """Parse a raw clone image into structured data."""

        logger = logger or _CHANNEL_LOG
        if len(blob) < CHANNEL_SECTION_BYTES:
            raise ValueError(
                f"Clone image is too small ({len(blob)} bytes); expected at least {CHANNEL_SECTION_BYTES}"
            )

        channel_bytes = memoryview(blob)[:CHANNEL_SECTION_BYTES]
        channels = []
        for index, chunk in enumerate(_chunk(channel_bytes, CHANNEL_SIZE)):
            try:
                record = ChannelRecord.from_bytes(chunk, logger=logger)
            except ValueError as exc:
                raise ValueError(f"Failed to decode channel {index}: {exc}") from exc
            channels.append(record)
        remainder = bytes(blob[CHANNEL_SECTION_BYTES:])
        return cls(channels=channels, remainder=remainder)

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> "RadioImage":
        """Load an image from ``path`` then parse it via :meth:`from_bytes`."""

        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"Unable to read image file {path}: {exc}") from exc
        return cls.from_bytes(data, logger=logger)

    def to_bytes(self, *, logger: Optional[logging.Logger] = None) -> bytes:
        """Serialise the image back into clone format."""

        logger = logger or _CHANNEL_LOG
        if len(self.channels) != CHANNEL_COUNT:
            raise ValueError(
                f"Image must contain {CHANNEL_COUNT} channels; has {len(self.channels)}"
            )
        buffer = bytearray(CHANNEL_SECTION_BYTES + len(self.remainder))
        for index, channel in enumerate(self.channels):
            start = index * CHANNEL_SIZE
            buffer[start : start + CHANNEL_SIZE] = channel.to_bytes(logger=logger)
        buffer[CHANNEL_SECTION_BYTES:] = self.remainder
        return bytes(buffer)

    def empty_slot_indexes(self) -> List[int]:
        """Return indexes of channels that contain no receive frequency."""

        return [idx for idx, channel in enumerate(self.channels) if channel.rx_hz is None]

    def iter_populated_channels(self) -> Iterable[tuple[int, ChannelRecord]]:
        """Iterate over channels that have a defined receive frequency."""

        for index, channel in enumerate(self.channels):
            if channel.rx_hz is not None:
                yield index, channel

    def save(self, path: Path, *, logger: Optional[logging.Logger] = None) -> None:
        """Write the current image representation to ``path``."""

        data = self.to_bytes(logger=logger)
        try:
            path.write_bytes(data)
        except OSError as exc:
            raise ValueError(f"Unable to write image file {path}: {exc}") from exc
