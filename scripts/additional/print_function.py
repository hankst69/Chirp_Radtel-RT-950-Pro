"""Display decoded function settings from the reference dump."""

from pathlib import Path
from rt950pro.sections import parse_function_section

blob = Path('dumps/clean.bin').read_bytes()[0x9000:0x9100]
func = parse_function_section(blob)
for key, value in sorted(func.values.items()):
    print(f"{key}: {value}")
