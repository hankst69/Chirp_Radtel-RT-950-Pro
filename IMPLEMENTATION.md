# Implementation Status

## Snapshot (2025-09-23)
- Python 3.11 virtualenv active at .venv with pythonnet + pyserial tracked via equirements.txt.
- Core t950pro package now parses the full clone image: channels, VFO settings, function config, DTMF, modulation tables, and APRS blocks.
- CLI harness (python -m rt950pro) supports channel decode, raw-image summary, CPS .dat summary, clone-vs-CSV regression, and exposes parsed section details.
- Clone capture script (	ools/dump_clone.py) and companion README document the CDC handshake and XOR keystream.

## Alignment with DESIGN.md
- **Clone protocol**: Handshake and block map decoded; write/upload path still pending.
- **Memory map & parsing**: All major sections (channels, VFO, function, DTMF, modulation, APRS) decoded from raw clone dumps. CPS loader currently populates channels only; write-back work yet to begin.
- **Harness & tests**: CLI exercises decode/summary/regression flows. Automated regression assertions and CSV import/export tooling remain outstanding.
- **Round-trip validation**: Channel-level round-trips confirmed on synthetic data; full image round-trip (including config sections) planned once encoders exist.
- **Physical radio verification**: Deferred until post-harness validation.

## Task Board
- [x] Establish Python package layout ("rt950pro" module) within repo.
- [x] Set up virtual environment (c:\Python\python_3.11\python.exe -m venv .venv) and record dependencies.
- [x] Implement binary parsing for channel records, including GB2312 handling.
- [x] Implement writers that mirror CPS bitfields without introducing drift.
- [x] Decode additional clone sections (VFO, function config, DTMF, modulation, APRS) for raw images.
- [~] Build command-line harness to:
      1. Load clone image and emit JSON/pretty summary. *(Raw dump + CPS .dat summaries completed; richer diff tooling pending.)*
      2. Re-emit .dat from intermediate representation and diff against source. *(Pending ? CPS loader is read-only.)*
      3. Convert between .dat and CSV using existing schema. *(Pending.)*
- [ ] Add integration tests over Reference/950Pro Export/Radio*.dat files once raw clone dumps or derived equivalents are available.
- [ ] Prototype serial transport (flag clearly if using mocked serial ports; emit MOCK: log prefix when no hardware).
- [ ] Implement CHIRP driver class after harness stabilises; wire encoder/decoder utilities into CloneModeRadio implementation.
- [ ] Document test commands in this file as they are created. *(Ongoing.)*

## Learnings & Notes
- CPS loader relies on pythonnet and the vendor BT-RT950PRO_CPS.exe; users must provide the assembly path when it lives outside Reference/.
- Raw clone dumps confirm block sizes (channels 0x0000?0x77FF, VFO 0x8000, function 0x9000, DTMF 0xA000, modulation 0xB000/0xD000, APRS via 0x54 command).
- Parsed configuration data currently surfaces directly in CLI summaries; round-trip encoders will re-use these structures.

## Testing Considerations
- Manual smoke tests:
  - python -m rt950pro channel decode --hex <64-hex-chars>
  - python -m rt950pro image summary rt950pro_clone.bin --limit 5
  - python -m rt950pro image dat-summary Reference/950Pro Export/Radio.dat --limit 5 --assembly "C:\Program Files (x86)\RT-950PRO_CPS\BT-RT950PRO_CPS.exe"
  - python -m rt950pro regression dat-csv Reference/950Pro Export/Radio.dat Reference/950Pro Export/channels.csv --assembly "C:\Program Files (x86)\RT-950PRO_CPS\BT-RT950PRO_CPS.exe"
- Next steps: add automated assertions that compare parsed sections between raw dump and CPS .dat, plus eventual encode/decode round-trips once write support exists.

## Open Questions / Dependencies
- Convert vendor .dat (BinaryFormatter) back into raw clone images or implement write support to update .dat files.
- Confirm radio baud rate and flow control requirements during initial hardware session.
- Determine acceptable behaviour when encryption negotiation is disabled or rejected by the radio.
- Establish policy for FHSS/DTMF/APRS fields in CHIRP UI (preserve vs expose vs omit).
- Design JSON schema for channel definitions to feed the encoder CLI.
