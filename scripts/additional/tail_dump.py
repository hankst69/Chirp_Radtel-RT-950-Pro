"""Print the raw 0x7A80 tail segment for selected dump files."""

from pathlib import Path
FILES = [
    'clean.bin',
    'loop_postwrite.bin',
    'loop_postwrite2.bin',
    'loop_restored.bin',
    'loop_after_edit.bin'
]
start = 0x7A80
length = 0x80
for name in FILES:
    data = (Path('dumps')/name).read_bytes()
    segment = data[start:start+length]
    print(name, 'offset 0x7A80:', segment.hex())
