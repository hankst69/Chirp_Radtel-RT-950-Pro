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

"""Logging helpers for the RT-950 Pro tooling.

The harness configures logging via :func:`configure_logging`, which sets up a
console handler and a rotating file handler. Code paths that fall back to mock
behaviour should use :func:`log_mock_warning` so the resulting warnings are easy
to spot during cleanup.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOG_ROOT = "rt950pro"
__all__ = ["configure_logging", "get_logger", "log_mock_warning", "LOG_ROOT"]

LOG_ROOT = _LOG_ROOT


def configure_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_directory: Optional[Path] = None,
    log_filename: str = "rt950pro.log",
) -> logging.Logger:
    """Configure logging handlers for the tooling.

    Parameters
    ----------
    verbose:
        When ``True`` the console handler logs at ``DEBUG`` level.
    quiet:
        When ``True`` the console handler logs at ``WARNING`` level.
    log_directory:
        Optional base directory for log files. Defaults to ``./logs`` relative
        to the current working directory.
    log_filename:
        Filename for the rotating log file.

    Returns
    -------
    logging.Logger
        The root logger for the rt950pro namespace.
    """

    if verbose and quiet:
        raise ValueError("verbose and quiet cannot both be True")

    base_logger = logging.getLogger(_LOG_ROOT)
    base_logger.setLevel(logging.DEBUG)

    # Remove existing handlers so repeated invocations refresh configuration.
    for handler in list(base_logger.handlers):
        base_logger.removeHandler(handler)

    console_level = logging.INFO
    if verbose:
        console_level = logging.DEBUG
    elif quiet:
        console_level = logging.WARNING

    formatter = logging.Formatter(
        fmt="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(formatter)
    base_logger.addHandler(console)

    logs_dir = Path("logs" if log_directory is None else log_directory)
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / log_filename,
        maxBytes=1_000_000,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    base_logger.addHandler(file_handler)

    base_logger.debug("Logging configured (console=%s, file=%s)", console_level, file_handler.baseFilename)

    return base_logger


def get_logger(name: str, **context: object) -> logging.Logger:
    """Return a namespaced logger, optionally wrapped with contextual data."""
    logger = logging.getLogger(f"{_LOG_ROOT}.{name}")
    if context:
        return logging.LoggerAdapter(logger, context)
    return logger


def log_mock_warning(logger: logging.Logger, detail: str) -> None:
    """Emit a standardised warning when mock behaviour is used."""
    logger.warning("MOCK: %s", detail)
