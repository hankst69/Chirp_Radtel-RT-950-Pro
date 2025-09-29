# Implementation Status

## Snapshot (2025-09-25)
- Portable Python 3.11 still lives in `portable_python`; `.venv` targets that interpreter and tracks dependencies in `requirements.txt` (`pythonnet`, `pyserial`, `ddt`, `requests`, `lark`).
- `rt950pro` decodes and re-encodes every clone section (channels, VFO, function, DTMF, modulation parameter/name blocks, APRS) while preserving untouched bytes.
- DTMF parsing now recognises digit `0` and avoids clobbering info bytes; modulation encoders compare against raw names/bandwidths so blank entries do not get normalised to `0xFF`.
- `RadioImage.to_bytes()` rebuilds clone images while leaving the firmware-managed tail unchanged; CLI `image clone-write` streams raw payloads verbatim when given a 33,152-byte dump.
- CHIRP driver exposes channel memories plus Function/APRS/DTMF settings groups via `RadioSettings`; tests confirm both memory edits and global settings survive round-trips (`tests/test_chirp_driver.py`).
- Bridge module `Reference/CHIRP_FULL/chirp/chirp/drivers/rt950pro.py` and sample image (`tests/images/Radtel_RT-950_Pro.img`) keep the upstream CHIRP harness green while we iterate locally.
- Targeted hardware regression (channel 4 renamed to `ABCDEF`) held steady—only the channel slot and firmware tail moved.
- CLI harness (`python -m rt950pro`) covers channel decode, clone read/write, summaries, BinaryFormatter `.dat` inspection, and regression helpers; unit tests exercise encoder, transport, and driver paths against `dumps/clean.bin`.

## Alignment with DESIGN.md
- **Clone protocol**: Serial handshake/read/write flows implemented via `CloneSerialTransport`; verbose logging captured for the most recent write and read sessions.
- **Memory map & parsing**: Complete. All sections parsed/encoded with sentinel-aware handling and raw-byte preservation.
- **Harness & tests**: CLI exposes inspection commands; pytest coverage guards round-trips, transport XOR handling, driver conversions, and settings updates; upstream CHIRP tests now execute for RT-950 Pro.
- **Round-trip validation**: Implemented. Unit tests lock bytes through `0x7A80`, and mutated structures survive encode/decode cycles.
- **Physical radio verification**: Read->write->read loop on 2025-09-26 matched byte-for-byte up to 0x7A80 (dumps/hw_loop_original.bin vs. dumps/hw_loop_postwrite.bin) while full hashes confirm tail parity at 33152 bytes.

## Task Board
- [x] Establish Python package layout (`rt950pro` module) within repo.
- [x] Set up portable Python 3.11 runtime and create `.venv` anchored to it (`portable_python/python.exe -m venv .venv`).
- [x] Implement binary parsing for channel records, including GB2312 handling.
- [x] Implement writers that mirror CPS bitfields without introducing drift.
- [x] Decode additional clone sections (VFO, function config, DTMF, modulation, APRS) for raw images.
- [x] Build command-line harness to:
      1. Load clone image and emit JSON/pretty summary.
      2. Re-emit clone data from structured objects and verify round-trips on sample dumps.
      3. Provide regression aids against CPS exports (dat/CSV) - conversion still limited to read, write support pending.
- [x] Add round-trip tests over `dumps/clean.bin` and mutated data via `pytest`.
- [ ] Add integration/regression tests against Reference `.dat` files once raw equivalents or reliable conversions exist.
- [x] Prototype serial transport (real vs mock) with explicit logging when hardware is absent.
- [x] Extend serial transport with write/upload support and integrate with the encoder pipeline.
- [x] Implement CHIRP driver class using the new encoders and hook into `CloneModeRadio`.
- [x] Register driver within CHIRP upstream and exercise targeted tests.
- [x] Generate monolithic `radtel_rt950pro.py` from the package sources (Phase 4 of CREATE_MONOLITH_PLAN) via `python scripts/build_monolith.py` (outputs `chirp_driver/radtel_rt950pro.py`).

## Learnings & Notes
- The remainder region must be padded to `KNOWN_SECTION_BYTES` so encoders can update their slices safely while preserving untouched data.
- DTMF and modulation fields interleave real zeros with sentinels; comparing against the raw buffer before writing prevents drift.
- Blank modulation names sometimes contain control bytes (`0x00`/`0x04`); skipping rewrites unless the caller alters the field keeps calibration data intact.
- CHIRP memory conversions require explicit handling for duplex/tones so the driver mirrors CPS behaviour; registering the driver with CHIRP's directory verifies parity against the upstream test suite.

## Testing
- `python -m pytest tests` - targeted suite covering encoder, transport, and driver conversions (passes on portable Python).
- `CHIRP_TESTIMG=Radtel_RT-950_Pro.img python -m pytest tests/test_drivers.py` - upstream driver suite for the RT-950 Pro (31 tests passing).
- Hardware loop: `python -m rt950pro image clone-read --port COM5 --output dumps/loop_original.bin` ? `clone-write` ? `clone-read` with SHA-256 comparison up to `0x7A80`, plus on-radio channel spot check.
- Manual inspection: `python -m rt950pro image summary dumps/clean.bin --limit 10` for quick verification before write-back.

## Open Questions / Dependencies
- Convert vendor `.dat` (BinaryFormatter) dumps back into raw clone images or extend writers to update `.dat` payloads directly.
- Confirm radio baud rate / flow control during the next hardware session and capture XOR negotiation edge cases.
- Decide how FHSS/APRS/bank metadata should surface in the CHIRP UI; ensure unknown fields remain intact by default.
- Register the driver with CHIRP's directory/tests before submitting upstream; this will require wiring into `chirp/drivers/__init__.py` and adding `tests/driver_xfails.yaml` entries if necessary.
- Define the monolith build pipeline and document how downstream consumers regenerate the single-file driver.
