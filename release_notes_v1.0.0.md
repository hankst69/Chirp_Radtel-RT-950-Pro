# Release Summary — v1.0.0

- First stable driver for Radtel RT‑950 Pro with end‑to‑end image parsing, settings, and CHIRP compatibility.
- Adds modular driver package (`rt950pro/*`) and a monolithic CHIRP driver (`chirp_driver/radtel_rt950pro.py`).

## Features
- RT950Pro driver: channel, sections, image model, and clone transport.
- CHIRP integration: monolithic driver artifact and modular `rt950pro/chirp_driver.py`.
- Settings UI: adds `display_mode_a/b/c` (Channel/Frequency/Name).
- Convenience APIs: `RadioSettingGroup.get()`, `__getitem__()`, and `RadioSetting.get_name()`.
- Frequency helpers: `parse_freq()` and `format_freq()` (Hz/kHz/MHz).

## Fixes
- Encryption value validation corrected to accepted range `(0, 1, 2)`.
- Test expectations aligned for frequency defaults and BOM-stripping.

## CLI / Tools
- Module entrypoint: `python -m rt950pro --help`.
- Utilities: `tools/dump_clone.py` and scripts under `scripts/additional/*`.
- Monolith build helper: `scripts/build_monolith.py`.

## Tests
- Adds coverage for driver, transport, settings API, roundtrip behavior.
- Ensures deterministic frequency parsing/formatting and settings mutations.

## Documentation
- Implementation notes, protocol WIP, settings inventory, and agent guidance updated.
- README quickstart refined for developers.

## Breaking Changes / Layout
- Monolithic driver resides at `chirp_driver/radtel_rt950pro.py`.
- Modular driver and support code live under `rt950pro/`.

## Usage
- Run tests: `pytest -q`
- CLI: `python -m rt950pro --help`
- CHIRP driver import (modular): `from rt950pro import chirp_driver`

## Known Issues / Notes
- On-radio validation pending; coordinate tests with Nathan before protocol-affecting changes.
- Frequency parsing raises on invalid input; callers should validate user text.
