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
