# Implementation Status

## Snapshot (2025-09-23)
- Python 3.11 virtualenv created at .venv and equirements.txt now lists pythonnet for CPS .dat support.
- Core t950pro package includes logging helpers, channel record parser/encoder, RadioImage channel-section loader, CPS .dat converter, and regression comparison utilities.
- CLI harness (python -m rt950pro) exposes channel decode, raw-image summary, CPS .dat summary, and egression dat-csv comparison commands.
- Documentation directive enforced: all public functions/classes carry docstrings per AGENTS.md guidance.

## Alignment with DESIGN.md
- **Clone protocol**: analysis recorded; transport/higher-level logic still pending implementation.
- **Memory map & parsing**: channel records handled for both raw clone dumps and CPS .dat conversions; remaining sections (VFO, function, DTMF, modulation, APRS) still TODO.
- **Harness & tests**: CLI covers decode/summary/regression workflows; automated regression suite and CSV/round-trip tooling remain outstanding.
- **Round-trip validation**: Channel-level round-trips validated on synthetic data; CPS loader is currently read-only and drops non-channel sections.
- **Physical radio verification**: unchanged?deferred until after harness validation.

## Task Board
- [x] Establish Python package layout ("rt950pro" module) within repo.
- [x] Set up virtual environment (c:\Python\python_3.11\python.exe -m venv .venv) and record dependencies.
- [x] Implement binary parsing for channel records, including GB2312 handling.
- [x] Implement writers that mirror CPS bitfields without introducing drift.
- [~] Build command-line harness to:
      1. Load clone image and emit JSON/pretty summary. *(Raw dump support complete; CPS .dat and regression comparison now available. Full diff/round-trip tooling still pending.)*
      2. Re-emit .dat from intermediate representation and diff against source. *(Pending ? CPS loader is read-only.)*
      3. Convert between .dat and CSV using existing schema. *(Pending.)*
- [ ] Add integration tests over Reference/950Pro Export/Radio*.dat files once raw clone dumps or derived equivalents are available.
- [ ] Prototype serial transport (flag clearly if using mocked serial ports; emit MOCK: log prefix when no hardware).
- [ ] Implement CHIRP driver class after harness stabilises; wire encoder/decoder utilities into CloneModeRadio implementation.
- [ ] Document test commands in this file as they are created. *(Ongoing.)*

## Learnings & Notes
- CPS loader relies on pythonnet and the vendor BT-RT950PRO_CPS.exe; users must provide the assembly path when it is outside Reference/.
- CSV comparison normalises tones, power, and frequency formatting to catch real field mismatches rather than string-format differences.
- RadioImage currently retains only channel data for CPS imports; future work must capture VFO/config blocks for write-back fidelity.

## Testing Considerations
- Manual smoke tests:
  - python -m rt950pro channel decode --hex <64-hex-chars>
  - python -m rt950pro image summary sample_image.bin --limit 5
  - python -m rt950pro image dat-summary Reference/950Pro Export/Radio.dat --limit 5 --assembly "C:\Program Files (x86)\RT-950PRO_CPS\BT-RT950PRO_CPS.exe"
  - python -m rt950pro regression dat-csv Reference/950Pro Export/Radio.dat Reference/950Pro Export/channels.csv --assembly "C:\Program Files (x86)\RT-950PRO_CPS\BT-RT950PRO_CPS.exe"
- Develop scriptable assertions comparing RadioImage.to_bytes() with original blobs once we have golden raw images or CPS re-serialization.
- Maintain deterministic logging by running CLI with --quiet in automated contexts.

## Open Questions / Dependencies
- Convert vendor .dat (BinaryFormatter) back into raw clone images or implement write support to update .dat files.
- Confirm radio baud rate and flow control requirements during initial hardware session.
- Determine acceptable behaviour when encryption negotiation is disabled or rejected by the radio.
- Establish policy for FHSS/DTMF/APRS fields in CHIRP UI (preserve vs expose vs omit).
- Design JSON schema for channel definitions to feed the encoder CLI.
