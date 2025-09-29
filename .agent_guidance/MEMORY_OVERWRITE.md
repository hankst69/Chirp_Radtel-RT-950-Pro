# RT-950 Pro Potential Memory Overwrite (WIP)

_Last updated: 2025-09-25_

## 1. Incident Summary
- Our early `clone-write` implementation streamed 0x80-byte blocks without waiting for the radio’s per-block ACK.  If the radio dropped a frame, we still advanced, effectively pushing misaligned data (observed in `loop_postwrite.bin`, where channel block 0/1 were blanked).
- The CLI also re-encoded images from `RadioImage`, which appended the entire remainder region (bytes = 0x8080).  While the CPS jumps from channel space (`0x0000–0x77FF`) directly to `0x8000` and never streams the gap, we were still sending the tail extracted from the dump.
- Subsequent writes (even with the fixed ACK handling) leave bytes `0x7A87–0x7AD2` rewritten to a repeating `0x03` pattern by the radio firmware.  These bytes are all `0xFF` in `clean.bin` and other untouched dumps.
- Result: after testing, the radio no longer transmits reliably even after firmware reloads and CPS restores.  Calibration or PA tables may have been corrupted in a region the CPS does not normally expose.

## 2. Available Artifacts
| File | Size | SHA256 (=0x8080) | SHA256 (full) | Notes |
|------|------|-----------------|---------------|-------|
| `clean.bin` | 33152 | a5a04d7314dbcb114181b75bdac46f631ca292c29c95406dfe81352b67809e28 | 30f431e18806b28192a4ebe6da51c5fa16bd4294c5e1b97a84fd74a97d03ce5e | pristine dump (matches `loop_original.bin`). |
| `loop_postwrite.bin` | 33152 | a05fc6a4d466bd5f42d177d4931600e4a1eacb39b1eb0dd3f185d71516aacea4 | 777b8b9162965406a5496ffcec825114f84f61fb766f21029750c4439fa9ea48 | First failing write-back (channels 4–7 wiped). |
| `loop_postwrite2.bin` | 33152 | b7e3a864926b9dfd9512a5128feac5eefa71c93d67391f269220bab95c886653 | ea7b9f9d4c246f10ceef85b8d23148676e526b5771cd899d0fe5a88e72929bd9 | Read after failure – tail rewritten, extensive drift. |
| `loop_restored.bin` | 33152 | **same as clean** | 92595d2f36b8e5a24b49ccafbe33b3e36cad71fb7cd62af34886a7fb6eb3dc74 | Write using fixed pipeline; =0x8080 restored, tail still altered. |
| `loop_after_edit.bin` | 33152 | 35e9ac19c4d259991b6e6f1e6fa8dbee9046e9cfd53aeda80af354e930b90a9c | 15531faf016b32cd349167874e6ad0759a24d10c55959a0073ad77e2eb4aa334 | Minimal channel rename (diff confined to slot + tail). |
| `CPS_SET_FREQS.bin` | 33152 | 49d2f066763bbf45ccc8fc5c7d968f902e59859df05fe4414e408a8dceb555c4 | 0e9302f1dc5e35d6b2878a2dc73022a9bf1159ef9513c8d339233312c9fa4e74 | Factory CPS export used during early testing.

Additional files:
- `clean.dat` (BinaryFormatter, 89?kB): CPS configuration file; contains serialized `RadioData` but no raw tail bytes.
- `clean.zip` (8?kB): zipped snapshot provided by the user (content not yet examined).

## 3. Suspected Region of Damage
- Tail bytes starting at `0x7A87` transition from all `0xFF` (`clean.bin`) to the repeating `…03…` pattern after the failed write and remain altered even when we write back a pristine dump.  Example (`loop_after_edit.bin` @ `0x7A80`):
  ```
  ffffff03ffff03ffff03ffff03ffff03ffff03ffff03ffff03ffff03ffff03ff...
  ```
- The CPS never streams these addresses: both read and write branches in `RWDataOperation` jump from `0x77FF` (`case 30720`) to `0x8000`, therefore the gap must be handled internally by the firmware.  Hypothesis: it stores calibration / PA tables in a shadow area that is refreshed when a valid payload is written, and we may have pushed placeholder data when the ACK bug was present.

## 4. What the CPS Source Tells Us
- `RWDataOperation` only handles segments listed in DESIGN.md.  No calibration-specific blocks are surfaced in the UI.
- The state machine maintains a 0x80-byte buffer for four channel slots, and resets the buffer to `0xFF` after each ACK.  Our early clone path, by skipping ACK verification, progressed even when the radio rejected a block, causing the next buffer (still `0xFF`) to be sent.
- No additional read/write commands are issued outside these segments; there is no direct host access to hidden calibration data through the public API.

## 5. Action Items & Recovery Ideas
1. **Immediate Safeguards (done)**
   - CLI now rejects any input whose size doesn’t match the CPS clone payload (33,152 bytes).  This prevents accidental streaming of extended dumps.
   - Write loop enforces per-block ACKs, mirroring CPS behaviour.

2. **Assess Available Backups**
   - Review other machines for older dumps (bin/img) that might contain the original tail pattern.  A byte-for-byte match through `0x8180` would confirm we can restore with host tools.
   - Extract and archive `clean.zip` contents; document any additional calibration clues.

3. **Forensic Comparison**
   - Use `analyze_tails.py` (checked in under `scripts/`) to compute hashes and diff ranges.
   - If an earlier `*.bin` with intact tail exists, run a write using the fixed transport and confirm whether the radio still overwrites the tail to `0x03`.  If it does, the data is probably burned elsewhere (EEPROM/flash) and requires a vendor calibration procedure.

4. **CPS Hidden Hooks**
   - Continue scanning CPS assemblies for alternate commands (e.g., `RWDataOperation` subclasses, service menus).  Look for strings such as `CAL` / `ALIGN`, additional serial commands, or magic codes (e.g., `0x43`/`'C'`) that might unlock a calibration mode.
   - Inspect other namespaces in `BT-RT950PRO_CPS.dll` for “service” forms or upload routines not exposed in the main UI.

5. **Hardware Recovery Options**
   - If we can’t retrieve the original bytes, note that the tail might be repopulated during a factory alignment process.  Contacting the vendor or using a lab alignment jig may be necessary if transmit power stays degraded.

6. **Documentation Updates**
   - RADIO_PROTOCOL_WIP.md now explicitly documents the gap handling and tail behaviour.
   - Future writing tools must respect the CPS address transitions to avoid touching firmware-managed areas.

## 6. Open Questions
- Does the radio expect a checksum over the tail region, causing it to regenerate data regardless of input?  (No evidence yet.)
- Is the `0x03` pattern derived from new firmware defaults, or from degraded calibration?  Need RF tests to confirm.
- Can `clean.dat` or other CPS assets recreate the tail?  BinaryFormatter files may contain calibration parameters; needs reverse-engineering with `pythonnet` or `ILSpy`.

## 7. Next Steps Checklist
1. Locate additional historical dumps (user action).
2. Diff any newly found `*.bin`/`*.img` with `clean.bin` and record the hashes.
3. If a good tail is found, attempt a write with the fixed transport and observe whether the radio keeps it.
4. If the radio continues to rewrite the tail, escalate to vendor or service documentation for calibration procedures.
5. Keep capturing logs (`--verbose`) for every hardware interaction and archive in `logs/`.
