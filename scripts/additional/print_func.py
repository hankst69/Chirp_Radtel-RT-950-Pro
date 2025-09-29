"""Quick debug helper to dump function-setting key/value pairs."""

from pathlib import Path
from rt950pro.sections import parse_function_section

blob = Path('dumps/clean.bin').read_bytes()[0x9000:0x9100]
print(len(blob))
func = parse_function_section(blob)
for k, v in func.values.items():
    print(k, v)
