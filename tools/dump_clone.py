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

"""Capture a raw RT-950 Pro clone dump over the serial interface."""
from __future__ import annotations

import argparse
import random
from datetime import datetime
from pathlib import Path

import serial

HANDSHAKE_STRING = b"PROGRAMBT9000U"
ACK = b"\x06"
READ_BLOCK = 0x80
ENCRYPT_STRINGS = [
    b"BHT ",
    b"CO 7",
    b"A ES",
    b" EIY",
    b"M PQ",
    b"XN Y",
    b"RVB ",
    b" HQP",
    b"W RC",
    b"MS N",
    b" SAT",
    b"K DH",
    b"ZO R",
    b"C SL",
    b"6RB ",
    b" JCG",
    b"PN V",
    b"J PK",
    b"EK L",
    b"I LZ",
]


def xor_keystream() -> tuple[bytes, bytearray]:
    """Reproduce the CPS encryption negotiation frame and key."""

    seed = int(datetime.now().microsecond / 1000)
    rng = random.Random(seed)
    frame = bytearray(25)
    frame[0:4] = b"SEND"
    frame[4] = (rng.randint(1, 2) << 4) | rng.randint(0, 4)
    for index in range(19):
        frame[5 + index] = rng.randint(0, 19)
    code = frame[4]
    if code & 0x20:
        idx = (code - 0x20) * 2 + 1
    else:
        idx = (code - 0x10) * 2
    idx += 1
    symbol_index = frame[4 + idx]
    key = bytearray(ENCRYPT_STRINGS[symbol_index])
    return bytes(frame), key


def decrypt_block(data: bytearray, key: bytearray) -> bytearray:
    """Decrypt a clone payload block using the XOR keystream."""

    key_idx = 0
    for i in range(len(data)):
        k = key[key_idx]
        key_idx = (key_idx + 1) % len(key)
        b = data[i]
        if k != 0x20 and b not in (0x00, 0xFF) and b != k and b != (k ^ 0xFF):
            data[i] = b ^ k
    return data


def read_clone_dump(port: str, baud: int, output: Path) -> None:
    """Perform a clone-read and write the decrypted image to ``output``."""

    with serial.Serial(port, baudrate=baud, timeout=1.0) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        ser.write(HANDSHAKE_STRING)
        if ser.read(1) != ACK:
            raise RuntimeError("Handshake ACK not received")

        ser.write(b"F")
        handshake_blob = ser.read(16)
        if len(handshake_blob) != 16:
            raise RuntimeError("Handshake response incomplete")

        ser.write(b"M")
        model = ser.read(12).decode("ascii", errors="ignore").strip("\x00 ")
        if "RT-950" not in model:
            raise RuntimeError(f"Unexpected model: {model!r}")

        frame, key = xor_keystream()
        ser.write(frame)
        if ser.read(1) != ACK:
            raise RuntimeError("Encryption ACK not received")

        raw = bytearray()
        mode = 0x52
        addr = 0
        while True:
            cmd = bytes((mode, (addr >> 8) & 0xFF, addr & 0xFF, READ_BLOCK))
            ser.write(cmd)
            block = ser.read(4 + READ_BLOCK)
            if len(block) != 4 + READ_BLOCK:
                raise RuntimeError("Timeout while reading block")
            payload = decrypt_block(bytearray(block[4:]), key)
            raw.extend(payload)
            addr += READ_BLOCK
            if mode == 0x52:
                if addr == 30720:
                    addr = 32768
                elif addr == 32896:
                    addr = 36864
                elif addr == 36992:
                    addr = 40960
                elif addr == 41344:
                    addr = 45056
                elif addr == 45312:
                    addr = 53248
                elif addr == 54016:
                    mode = 0x54
                    addr = 0
            else:
                break

        ser.write(b"E")
        output.write_bytes(bytes(raw))
        print(f"Wrote {len(raw)} bytes to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a raw RT-950 Pro clone image")
    parser.add_argument("--port", default="COM5", help="Serial port presented by the radio (default: COM5)")
    parser.add_argument("--baud", type=int, default=115200, help="Clone baud rate (default: 115200)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("rt950pro_clone.bin"),
        help="Output file for the decrypted clone image",
    )
    args = parser.parse_args()

    try:
        read_clone_dump(args.port, args.baud, args.output)
    except KeyboardInterrupt:
        print("Interrupted")


if __name__ == "__main__":
    main()
