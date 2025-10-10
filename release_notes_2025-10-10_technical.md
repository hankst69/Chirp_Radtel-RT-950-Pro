# Technical Change Log — 2025-10-10

Summary
- Improved clone robustness and added granular progress reporting.
- Wired CHIRP status updates with segment/channel-aware messages.
- Regenerated monolithic driver for Load Module testing.

Changes
- Transport (`rt950pro/transport.py`)
  - Enforce minimum serial timeouts: floors `timeout` and `write_timeout` to 3.0s.
  - Add `progress_cb(done: int, total: int, phase: str)`; invoked per 0x80-byte block for both read and write.
  - Protect clone path from progress callback exceptions.

- CHIRP driver (`rt950pro/chirp_driver.py`)
  - Hook `CloneSerialTransport.progress_cb` into `chirp_common.Status()`.
  - Derive segment/block position from `DEFAULT_SEGMENTS` and `READ_BLOCK` to build messages:
    - Channels: show channel ranges per block (4 channels per block, based on 32-byte records).
    - Other segments: label as `VFO settings`, `Function settings`, `DTMF settings`, `Modulation params`, `Modulation names`, `APRS settings`.
  - Messages reflect direction: “Reading …” vs “Writing …”.
  - No protocol changes; pure UI/status improvements.

- Monolith (`chirp_driver/radtel_rt950pro.py`)
  - Rebuilt via `scripts/build_monolith.py` to include the above changes for CHIRP Load Module.

Impact
- Reduces spurious “Serial read timed out” dialogs when the clone completes successfully.
- Provides actionable progress context for diagnostics and user feedback.

Compatibility
- `progress_cb` is optional and ignored unless set.
- Maintains existing segment layout assumptions (`DEFAULT_SEGMENTS`). Adjust label mapping if segment order/lengths change.

Verification
- Load `chirp_driver/radtel_rt950pro.py` via CHIRP File -> Load Module…
- Clone Read/Write shows:
  - Channel ranges like “Reading channels 001–004…”
  - Settings phases with segment names during later blocks.

Notes
- Tests/CI not executed here; local environment lacked `pyserial`/`pytest`. On a dev machine, run tests after installing dependencies.

