"""Compare the function-settings block across dump files."""

from pathlib import Path

start = 0x9000
length = 0x0100
dumps = sorted(Path('dumps').glob('*.bin'))
ref = dumps[0]
ref_data = ref.read_bytes()[start:start+length]
print(f'reference: {ref.name}')
for path in dumps:
    data = path.read_bytes()[start:start+length]
    if data != ref_data:
        diffs = [i for i,(a,b) in enumerate(zip(ref_data, data)) if a!=b]
        first, last = diffs[0], diffs[-1]
        print(f'{path.name}: diffs {len(diffs)} first=0x{first:02X} last=0x{last:02X}')
    else:
        print(f'{path.name}: identical')
