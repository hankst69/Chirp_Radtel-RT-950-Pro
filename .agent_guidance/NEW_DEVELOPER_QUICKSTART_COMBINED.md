# CHIRP Driver Development Quickstart (UTF‑8, Combined)

This combined quickstart merges our training manual with the latest lessons from the RT‑950 Pro effort. The original file `NEW_DEVELOPER_QUICKSTART.md` remains (legacy encoding). Use this UTF‑8 version going forward.

## Contents
- Fundamentals and architecture
- Reverse‑engineering workflow
- Implementation outline (features, sync_in/out, memory mapping)
- Testing strategy
- Practical patterns validated on RT‑950 Pro
- Monolith build workflow

## Fundamentals (very short)
- A CHIRP driver is a `CloneModeRadio` subclass that declares features, converts between the radio’s binary image and `chirp_common.Memory`, and implements `sync_in/sync_out`.
- UI shows progress when the driver reports `chirp_common.Status` updates via `self.status_fn(status)`.

## Implementation outline
- `get_features()`: set `memory_bounds`, `valid_bands`, `valid_modes`, steps, tone/DTCS support, etc.
- `sync_in()`: serial handshake → read blocks → build `RadioImage` → `self._mmap = memmap.MemoryMapBytes(raw)`.
- `sync_out()`: build raw payload from `RadioImage` → write blocks (verify ACKs).
- `get_memory()/set_memory()`: translate between `RadioImage` channel structures and `chirp_common.Memory`.

## Testing checklist
- Round‑trip decode/encode of sections (unit tests where feasible).
- Minimal on‑radio writes first; re‑read and compare.
- CSV import/export works; no exporter errors.

## Practical Patterns (from RT‑950 Pro)

1) CSV DtcsCode defaults
- CSV exporter validates `DtcsCode`/`RxDtcsCode` even when `tmode` is blank.
- Initialize non‑DTCS rows to the first valid DCS code: `chirp_common.DTCS_CODES[0]` (023).
- If `tmode == 'DTCS'` but either code is 0, normalize to OFF when applying back to the channel.

2) UI progress updates
- Before cloning: `status = chirp_common.Status(); status.cur=0; status.max=total; status.msg='Cloning from/to radio…'; self.status_fn(status)`.
- Per block: increment `status.cur`; call `self.status_fn(status)`.
- If block loops live in a transport helper, expose `progress_cb(done, total, phase)` and adapt in the driver to `Status`.

3) Serial timeout floor
- Avoid spurious “Serial read timed out” after a successful clone by raising the floor in the transport constructor to 3.0s when the serial object has unset/too‑low timeouts. Do not override higher values set upstream.

4) Band/mode enforcement
- Expand `valid_bands` to reflect actual behavior (e.g., 18–64 MHz FM/NFM; 118–137 MHz AM RX only).
- When mapping Memory → channel:
  - Airband: force AM; disable TX.
  - 18–64 MHz: enforce FM; allow NFM/WFM bandwidth selection.

5) Bandwidth bit conventions
- Confirm image flag semantics. For RT‑950 Pro: bit6=1 → NARROW; bit6=0 → WIDE.
- Keep channel and VFO encode/decode consistent; map `NFM` ↔ NARROW, `FM` ↔ WIDE.

## Monolith build workflow
- Make changes under `rt950pro/*`.
- Rebuild: `py -3 scripts/build_monolith.py --output chirp_driver/radtel_rt950pro.py`
- Load in CHIRP (Developer Mode) via File → Load Module…

## Notes
- The legacy quickstart file is in a non‑UTF‑8 encoding; retain it for historical context. This combined file supersedes it.
