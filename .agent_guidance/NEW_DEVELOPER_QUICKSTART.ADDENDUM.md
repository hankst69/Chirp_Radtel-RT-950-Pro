# Addendum: CSV Defaults and UI Progress (RT‑950 Pro)

This addendum supplements `NEW_DEVELOPER_QUICKSTART.md` with concrete patterns validated during the RT‑950 Pro driver work. Keep this close to the main guide until the file can be re‑encoded to UTF‑8 and updated inline.

## CSV export compatibility (DtcsCode defaults)

- CHIRP’s CSV exporter validates `DtcsCode` and `RxDtcsCode` even when `tmode` is blank.
- To avoid “DTCS Code 000 not supported”, use the first valid DCS code (`023`) as a placeholder for non‑DTCS rows.
- Recommended when building `chirp_common.Memory`:
  - `mem.dtcs = mem.rx_dtcs = chirp_common.DTCS_CODES[0]  # 23`
  - Leave `mem.tmode = ''` unless the channel uses DCS.
  - If an incoming `Memory` has `tmode == 'DTCS'` but either code is `0`, normalize to OFF before applying back to the channel (prevents invalid states).

## UI progress updates

- Drivers should report progress via `self.status_fn(status)` where `status` is a `chirp_common.Status`.
- Typical flow:
  - Before a long operation: set `status.cur = 0`, `status.max = total_blocks`, `status.msg = 'Cloning from radio…'` (or `'Cloning to radio…'`), then call `self.status_fn(status)`.
  - During the per‑block loop: update `status.cur = blocks_done` and call `self.status_fn(status)`.
- If block processing is abstracted into a transport helper, expose a `progress_cb(done, total, phase)` and adapt it in the driver to `Status` calls.

## Serial timeout floor

- Symptom: UI shows “Serial read timed out” even though clone completes.
- Mitigation: in the transport’s constructor, if `serial.timeout`/`write_timeout` is unset or below a floor (e.g., `3.0` seconds), raise it to the floor. Do not override larger values set by CHIRP/pipe.

## Band/mode enforcement

- Expand `RadioFeatures.valid_bands` to reflect actual RX/TX capability.
- Apply constraints when mapping `Memory` ↔ channel:
  - Airband (118–137 MHz): force AM and disable TX.
  - 18–64 MHz: FM only; allow NFM/WFM bandwidth selection.

## Bandwidth bit conventions

- Confirm actual meaning of bandwidth bits in the image. For RT‑950 Pro, bit6=1 encodes NARROW, 0 encodes WIDE. Keep channel and VFO encode/decode consistent, and map `NFM` ↔ NARROW, `FM` ↔ WIDE in CHIRP.

## Monolith build workflow

- Make code changes in `rt950pro/*`.
- Regenerate the monolithic driver with:
  - `py -3 scripts/build_monolith.py --output chirp_driver/radtel_rt950pro.py`
- Load the regenerated file in CHIRP (Developer Mode) via File → Load Module… for testing.
