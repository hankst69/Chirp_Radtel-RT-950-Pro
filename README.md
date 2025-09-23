# RT-950 Pro CHIRP Driver Workspace

This repository tracks reverse-engineering notes, tooling, and implementation work for adding Baofeng Tech RT-950 Pro clone-mode support to [CHIRP](https://chirp.danplanet.com/).

## Repository Layout
- `DESIGN.md` ? fixed definition of done, protocol notes, and memory map.
- `IMPLEMENTATION.md` ? living status log and task board tied to the design.
- `AGENTS.md` ? primary contacts and collaboration expectations.
- `Reference/` ? vendor CPS decompilation and clean-room export utility from prior work.

## Development Environment
1. Create and activate a Python 3.11 virtual environment:
   ```powershell
   c:\Python\python_3.11\python.exe -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   ```
2. Dependencies will be listed in `requirements.txt` once the harness is implemented.
3. Keep tooling Python-only so tests can run without a CHIRP install; CHIRP integration will reference the same modules.

## Planned Tooling
- Standalone harness to decode/encode RT-950 Pro `.dat` images.
- CSV translator compatible with `Reference/950Pro Export` artifacts for regression checks.
- Optional serial transport wrapper for talking to a physical radio when connected.

## Testing Philosophy
- Prefer end-to-end binary comparisons over mocks; when mocking is unavoidable, log a warning so the shim can be revisited.
- Validate against known-good `.dat` files before exercising a physical radio.
- Document every new test command in `IMPLEMENTATION.md` to keep alignment with the design.

## Contributing
- Review `DESIGN.md` for scope; propose design changes before editing that file.
- Update `IMPLEMENTATION.md` with progress notes and open questions as work advances.
- Coordinate on-radio experiments with Nathan (_2E0NBS_).
