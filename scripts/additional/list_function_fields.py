"""List available function-setting fields from the reference dump."""

from pathlib import Path
from rt950pro.sections import parse_function_section

blob = Path('dumps/clean.bin').read_bytes()[0x9000:0x9000+96]
func = parse_function_section(blob)
for key, value in sorted(func.values.items()):
    print(f"{key}: {value}")
