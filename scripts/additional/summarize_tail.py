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

"""Summarise unique byte values within the 0x7A80 tail for multiple dumps."""

from pathlib import Path

start = 0x7A80
length = 0x40
files = [
    'clean.bin',
    'loop_original.bin',
    'loop_postwrite.bin',
    'loop_postwrite2.bin',
    'loop_restored.bin',
    'loop_after_edit.bin',
    'loop_channel4_ABCDEF.bin'
]
for name in files:
    data = (Path('dumps')/name).read_bytes()
    segment = data[start:start+length]
    unique = sorted(set(segment))
    print(f"{name:>24} unique bytes: {[f'0x{b:02X}' for b in unique]}")
    print(f"  dump: {segment.hex()}")
