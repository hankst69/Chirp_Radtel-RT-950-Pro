"""Summarise function settings extracted from the reference dump."""

from pathlib import Path
from rt950pro.sections import parse_function_section

start = 0x9000
end = 0x9100
segment = Path('dumps/clean.bin').read_bytes()[start:end]
func = parse_function_section(segment)
for key, value in sorted(func.values.items()):
    print(f"{key}: {value}")
