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
