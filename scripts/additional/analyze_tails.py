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

"""Compute hashes and diffs for the tail region of radio dump files."""

from pathlib import Path
import hashlib

SEGMENT_LIMIT = 0x8080  # bytes under CPS control
ROOT = Path("dumps")

binaries = sorted([p for p in ROOT.glob("*.bin") if p.is_file()])
print("Found", len(binaries), "bin files")
reference = None
for path in binaries:
    data = path.read_bytes()
    sha_known = hashlib.sha256(data[:SEGMENT_LIMIT]).hexdigest()
    sha_full = hashlib.sha256(data).hexdigest()
    print(f"{path.name:>24} size={len(data):5} known<=8080={sha_known} full={sha_full}")
    if reference is None:
        reference = data
        continue
    if len(data) != len(reference):
        print(f"  length mismatch vs {binaries[0].name}")
        continue
    diffs = [i for i,(a,b) in enumerate(zip(reference, data)) if a!=b]
    if diffs:
        first = diffs[0]
        last = diffs[-1]
        print(f"  diffs: {len(diffs)} first=0x{first:04X} last=0x{last:04X}")
    else:
        print("  identical to reference")
