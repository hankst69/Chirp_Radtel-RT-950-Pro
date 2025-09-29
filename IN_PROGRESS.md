# In-Progress Notes (RT-950 Pro write regression)

## Status
- Parser/encoder stack preserves every section and remainder byte; round-trip tests guard known scenarios (`rt950pro/image.py`, `tests/test_roundtrip.py`).
- Hardened serial transport mirrors CPS handshake/XOR/ACK flow and enforces exact payload length (`rt950pro/transport.py`, `tests/test_transport.py`).
- CHIRP driver now exposes both channel memory edits and global Function/APRS/DTMF settings; unit tests verify memory + radio-settings round trips and NFM bandwidth mapping (`rt950pro/chirp_driver.py`, `tests/test_chirp_driver.py`).
- Documentation refreshed with protocol cautions, incident post-mortem, and CHIRP integration status (`RADIO_PROTOCOL_WIP.md`, `MEMORY_OVERWRITE.md`, `IMPLEMENTATION.md`).
- Local suite `python -m pytest tests` passes on the portable Python interpreter; optional CHIRP harness `tests/test_drivers.py` also succeeds with our bridge module.

## Remaining Work (Monolith Plan)
1. **Phase 4 – Monolith Assembly** *(complete)*: `python scripts/build_monolith.py` now produces `chirp_driver/radtel_rt950pro.py`; copy or symlink it into a CHIRP checkout when running UI tests.
2. **Phase 5 – Validation Sweep**: run project + CHIRP suites against the generated driver, capture hardware read?write?read logs, and note partial-hash checks.
3. **Phase 6 – Packaging & Handoff**: document rebuild instructions, archive validation artefacts, and prepare submission/README notes for customers and CHIRP upstream.

## Supporting Files
- `dumps/clean.bin`: golden clone dump (33,152 bytes) used across tests.
- `dumps/loop_original.bin`, `dumps/loop_restored.bin`: reference validation pair from September 2025.
- `dumps/hw_loop_original.bin`, `dumps/hw_loop_postwrite.bin`: 2025-09-26 read->write->read run with zero diffs <=0x7A80.
- `logs/clone_write_verbose.log`, `logs/clone_read_postwrite_verbose.log`: verbose traces from early transport validation.
- `logs/hw_clone_read_original.log`, `logs/hw_clone_write_retry.log`, `logs/hw_clone_read_postwrite.log`: latest hardware session output.
- `Reference/CHIRP_FULL/chirp/tests/images/Radtel_RT-950_Pro.img`: sample image for CHIRP harness integration.

## Testing Strategy
- Automated: `python -m pytest tests`.
- CHIRP harness (optional): `CHIRP_TESTIMG=Radtel_RT-950_Pro.img python -m pytest tests/test_drivers.py` inside `Reference/CHIRP_FULL/chirp` (long-running; run only when needed).
- Hardware: run `python -m rt950pro image clone-read` -> `clone-write` -> `clone-read` with partial SHA-256 comparison up to `0x8080` plus an on-radio UI spot check.
- Manual: `python -m rt950pro image summary dumps/clean.bin --limit 10` before any write-back.
