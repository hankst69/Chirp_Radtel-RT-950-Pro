# Implementation Status

## Snapshot (2025-09-23)
- Documentation scaffold created (DESIGN.md, README.md, AGENTS.md, IMPLEMENTATION.md).
- No Python sources yet; all work tracked as upcoming tasks.

## Alignment with DESIGN.md
- **Clone protocol**: analysis complete from CPS sources; implementation pending.
- **Memory map & parsing**: design captured; need Python structures + serializers/deserializers.
- **Harness & tests**: not started; venv instructions in README ready for activation.
- **Round-trip validation**: blocked until parser/emitter are in place.
- **Physical radio verification**: future milestone once harness proves stable.

## Task Board
- [ ] Establish Python package layout ("rt950pro" module) within repo.
- [ ] Set up virtual environment (c:\Python\python_3.11\python.exe -m venv .venv) and record dependencies.
- [ ] Implement binary parsing for channel records, including GB2312 handling.
- [ ] Implement writers that mirror CPS bitfields without introducing drift.
- [ ] Build command-line harness to:
      1. Load .dat image and emit JSON/pretty summary.
      2. Re-emit .dat from intermediate representation and diff against source.
      3. Convert between .dat and CSV using existing schema.
- [ ] Add integration tests over Reference/950Pro Export/Radio*.dat files.
- [ ] Prototype serial transport (flag clearly if using mocked serial ports; emit MOCK: log prefix when no hardware).
- [ ] Implement CHIRP driver class after harness stabilises; wire encoder/decoder utilities into CloneModeRadio implementation.
- [ ] Document test commands in this file as they are created.

## Learnings & Notes
- CPS encrypts clone blocks via a 4-byte XOR keystream chosen per session; reuse logic for both directions.
- Channel name encoding is GB2312; need deterministic transliteration or byte-preserving strategy for CHIRP's UTF-8 UI.
- Zone metadata stored in static arrays (RadioData.strAreaEN/CN); decide whether to surface as banks or ancillary metadata in CHIRP.

## Testing Considerations
- Target full binary round-trip on reference .dat files before talking to hardware.
- Automated harness should emit explicit warnings whenever a mock transport substitutes for serial I/O.
- Aim for deterministic outputs so CI comparisons remain stable.

## Open Questions / Dependencies
- Confirm radio baud rate and flow control requirements during initial hardware session.
- Determine acceptable behaviour when encryption negotiation is disabled or rejected by the radio.
- Establish policy for FHSS/DTMF/APRS fields in CHIRP UI (preserve vs expose vs omit).
