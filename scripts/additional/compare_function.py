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
