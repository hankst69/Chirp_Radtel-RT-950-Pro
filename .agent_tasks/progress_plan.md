# RT-950 Pro — Work Plan and Context (Carry-Over)

This note captures the decisions and exact edits still needed so the next session can continue without hunting context.

Scope
- Do NOT push until manual verification is complete.
- Edit modular sources under `rt950pro/` first, then regenerate the monolithic CHIRP driver with `scripts/build_monolith.py`.

Decisions implemented so far
- Bands: allow 18–64 MHz (FM/NFM) and 118–137 MHz (AM RX, TX disabled).
- Band constraints:
  - Airband: force AM; disable TX.
  - Low-HF (18–64): force FM; obey NFM/FM for bandwidth.
- FM/NFM mapping: bit6 in flags is inverted vs earlier assumption.
  - Decode: bit6=1 -> NARROW, bit6=0 -> WIDE.
  - Encode: set bit6 for NARROW.
- CSV export compatibility:
  - Default non-DTCS rows to `DtcsCode=023` (first valid CHIRP DCS code) instead of `000`.
  - If `tmode == 'DTCS'` but `dtcs` or `rx_dtcs` equals 0, normalise to OFF when mapping to channel.

Next tasks (pending)
1) Serial timeout floor + progress reporting
   - File: `rt950pro/transport.py`
     - Increase minimum serial timeouts:
       - In `CloneSerialTransport.__init__`, if `serial.timeout` is None/0 or < 3.0, set `3.0`.
       - Same for `serial.write_timeout`.
     - Add optional per-block progress callback:
       - Attribute: `self.progress_cb: Optional[Callable[[int, int, str], None]] = None`.
       - Compute `total_blocks = sum(seg.length for seg in segments) // READ_BLOCK`.
       - Track `done` and after each block read/write: `if self.progress_cb: self.progress_cb(done, total_blocks, 'read'|'write')`.

2) Wire transport progress to CHIRP UI
   - File: `rt950pro/chirp_driver.py`
     - In `sync_in`:
       - Build `status = chirp_common.Status()`; set `status.max` to total blocks; `status.msg = 'Cloning from radio…'`.
       - Define `_progress(done, total, phase)` to set `status.cur = done; status.max = total; self.status_fn(status)` (guard with `hasattr`).
       - Set `transport.progress_cb = _progress`.
     - In `sync_out`:
       - Same pattern with `status.msg = 'Cloning to radio…'`.

3) Regenerate monolith for CHIRP loading
   - Command: `py -3 scripts/build_monolith.py --output chirp_driver/radtel_rt950pro.py`.
   - Test in CHIRP via File -> Load Module… using the regenerated file.

4) Enforce CSV normalisation rules in code paths
   - Files: `rt950pro/channel.py`, `rt950pro/sections.py`
     - Default non-DTCS rows to 023 during export.
     - When `tmode == 'DTCS'` but codes are 0, map to OFF during import/channel build.
     - Add small helpers to centralise tone-mode normalisation and reuse across sections.

5) Round-trip regression CLI targets
   - Files: `rt950pro/regression.py`, `rt950pro/cli.py`
     - Add `dat -> objects -> dat` round-trip with byte-compare (tolerate documented padding bytes if any).
     - Add CSV import/export verification against reference samples under `Reference/`.
     - Emit non-zero exit codes on mismatches for CI/local scripting.

6) Unit tests for bit mapping and band constraints
   - Files: `tests/test_channel.py`, `tests/test_bands.py`
     - Assert FM/NFM bit6 mapping works both directions.
     - Assert airband channels render AM and TX disabled; 18–64 obey narrow/wide and TX allowed.

7) Logging and diagnostics
   - File: `rt950pro/logging.py`
     - Ensure `LoggerAdapter` includes block/slot metadata during clone.
     - Use WARNING for any fallback/mocked behaviour prefixed with `MOCK:`.

8) Documentation pass
   - Files: `README.md`, `docs/LoadModuleInChirp.md`, `IMPLEMENTATION.md`
     - Document progress UI, timeout defaults, and how to run regression checks.
     - Add short “On-radio test checklist” and link to Nathan for coordination.

9) On-radio validation with Nathan
   - Confirm clone read/write success, progress UI behaviour, and band/AM-FM rules on-device.

10) Acceptance and upstream packaging
   - Regenerate monolith, ensure public docstrings are present, and prepare submission to CHIRP (or local module usage instructions).
   - Update `release_notes_v1.0.0.md` with finalised behaviour.

Validation checklist
- Progress bar advances during read and write; messages reflect direction.
- No more spurious “Serial read timed out” dialogs after successful clone.
- Airband entries appear AM and TX disabled on-radio.
- 18–64 MHz entries respect NFM/FM (narrow/wide) and allow TX.
- CSV export succeeds with non-DTCS rows (DtcsCode=023 placeholder).
- Round-trip `.dat` comparisons pass (byte-identical or documented padding exceptions).

Notes
- Keep all CSV defaults aligned with CHIRP patterns: non-DTCS rows carry `DtcsCode/RxDtcsCode = 023` even when `tmode` is empty.
- Avoid pushing until Nathan confirms manual testing passes.

