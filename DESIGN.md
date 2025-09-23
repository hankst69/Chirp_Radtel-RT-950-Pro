# RT-950 Pro CHIRP Driver Design

## Objectives
- Add full clone-mode support for the RT-950 Pro handheld in CHIRP using Python.
- Maintain compatibility with stock CPS data (channel, VFO, function, DTMF, modulation, APRS blocks).
- Provide an automated, out-of-radio validation harness capable of decoding/encoding `.dat` images and comparing with known-good artifacts.

## Non-Goals
- Real-time control or live programming beyond clone operations.
- Support for radios other than the RT-950 Pro.
- Reverse engineering or reproducing the CPS UI; focus strictly on protocol compatibility.

## Clone Protocol Summary
1. Open serial connection at radio baud rate (TBD from hardware; CPS default 115200 suspected, confirm during implementation).
2. Send ASCII handshake string `PROGRAMBT9000U` and wait for ACK byte `0x06`.
3. Transmit `0x46` (`'F'`) and wait for a 16-byte response.
4. Read 12-byte model identifier (`"RT-950"` expected); if mismatch, abort.
5. If encryption enabled (default CPS behaviour):
   - Send `"SEND"` + 21 random bytes, following CPS structure (high nibble encodes lookup index into `tblEncrySymbol`).
   - Receive one-byte ACK, derive 4-byte XOR stream from selected table entry, apply cyclically to payload bytes during read/write.
6. Issue clone command:
   - Read: send `[0x52, addr_hi, addr_lo, 0x80]` requests, process 0x80-byte payloads, auto-advance addresses per CPS sequence (channels then configuration blocks). Finish with `0x45` (`'E'`).
   - Write: mirror CPS flow using `0x57` command and block buffers rebuilt from CHIRP image.

## Memory Layout (Per CPS)
- `0x0000-0x77FF`: 960 channel records (32 bytes each, four records per 0x80-byte block).
- `0x8000-0x80FF`: VFO profiles A/B/C.
- `0x9000-0x90FF`: Function configuration (3 blocks).
- `0xA000-0xA1FF`: DTMF settings and code groups.
- `0xB000-0xB0FF`: Modulation settings.
- `0xD000-0xD1FF`: Modulation channel names (0x300 bytes assembled across blocks).
- `0x0000-0x007F` (after write stage flips to `0x54` command): APRS settings (captured separately by CPS).

## Channel Record Encoding
- Bytes 0-3: RX frequency packed BCD (units of 10 Hz).
- Bytes 4-7: TX frequency packed BCD.
- Bytes 8-9 / 10-11: RX/TX sub-audio (CTCSS or DCS depending on type flag in second byte).
- Byte 12: signalling group (0-14).
- Byte 13: PTT ID (0-3).
- Byte 14: low nibble TX power (0-2), high nibble scrambler code (0-8).
- Byte 15: flags (bit7 learn FHSS, bit6 bandwidth, bits5-4 encryption (0-3), bit3 busy lockout, bit2 scan add, bit1 TX enable (1 enabled), bit0 modulation (0 FM / 1 AM)).
- Bytes 16-19: FHSS code (BCD-packed ASCII, sentinel 0xA0 at byte 19 indicates present).
- Bytes 20-31: Channel name encoded as GB2312, up to 12 bytes, 0xFF padded.

## Mapping to CHIRP Models
- CHIRP memory range: 0-959 (zones 1-15, slots 1-64).
- Memory fields:
  - `freq`, `offset`, `duplex`: derived from RX/TX pair.
  - `name`: attempt round-trip between GB2312 and Unicode; fall back to transliterated ASCII on encode and log lossy cases.
  - `rtone`, `ctone`, `dtcs`: decode from sub-audio fields.
  - `power`: map CPS levels (0=Low,1=Med,2=High) to CHIRP enums.
  - `bandwidth`: Narrow/Wide from bit6.
  - `tuning_step` etc. remain static or derived from config blocks as supported.
- Zone metadata: treat the 15 `RadioData.strAreaEN` entries as CHIRP banks; expose bank labels and membership, preserving user edits across round-trips.

## Logging Strategy
- Use Python's `logging` with namespace `rt950pro.*`; default harness output INFO to stdout and DEBUG to a rotating `logs/rt950pro.log` file.
- Allow CLI verbosity switches (`--verbose`, `--quiet`) to adjust levels; CHIRP driver defaults to WARNING to stay quiet in the UI.
- Emit `MOCK:`-prefixed WARNING logs whenever a mock transport or placeholder behavior is invoked.
- Include contextual metadata (block address, slot) via `LoggerAdapter` so traces align with clone operations.

## Test & Tooling Strategy
- Maintain reference images (`Reference/950Pro Export/*.dat`) and CSVs for regression checks.
- Implement standalone Python harness executable via venv (`c:\Python\python_3.11\python.exe`) that can:
  - Parse `.dat` images into structured objects using driver logic.
  - Re-emit `.dat` from structured data and compare to originals (round-trip within acceptable tolerances for padded bytes).
  - Import/export CSV (leveraging existing schema) for cross-validation.
  - Flag any mocked interactions with clear log output.
- Provide CLI entry points for clone read/write that can be toggled between
  - Serial transport (real radio) and
  - File-backed transport (tests).

## Definition of Done
- Driver accepted into CHIRP with read/write support verified against physical RT-950 Pro.
- Round-trip unit tests on sample `.dat` files confirm byte-identical (or documented exceptions) results.
- Harness documented in README and automated via scriptable commands.
- No permanent mocks left in code; any temporary shims removed or clearly documented for follow-up.
- Documentation updated (README, IMPLEMENTATION) with final status; DESIGN.md remains unchanged after this baseline.

## Risks & Open Questions
- Confirm radio baud rate and whether flow control is needed.
- Validate encryption toggle; determine behaviour if radio ships with encryption disabled.
- Clarify FHSS and APRS field usage; ensure CHIRP UI can expose or at least preserve them.
- Character encoding: GB2312 names vs CHIRP UTF-8?confirm transliteration rules meet user expectations.
- Determine how to expose bank operations in CHIRP UI (e.g., bank renaming, membership edits) and test across export/import cycles.
