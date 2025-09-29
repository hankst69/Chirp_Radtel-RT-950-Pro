# RT-950 Pro Serial Clone Protocol (Work in Progress)

_Last updated: 2025-09-25_

This note captures the behaviour we have verified from the vendor CPS and on-radio tests.  It complements the high-level DESIGN.md summary with concrete byte-level details and timing expectations.  Treat it as a living document while we finish CHIRP integration.

## Transport Overview
- Physical link: USB CDC serial device.
- Default baud: 115200 8N1 (no hardware flow control observed).
- All transactions are synchronous request/response; the radio answers each host command before the next command is accepted.
- The CPS keeps an internal retry timer (1 s) and resends frames up to three times; so far we have not needed retries, but the state machine supports it.

## Handshake Sequence
1. **Handshake string** – host writes ASCII `PROGRAMBT9000U`; radio replies single-byte ACK `0x06`.
2. **Probe** – host sends byte `0x46` (`'F'`); radio responds with a 16-byte blob (seems to contain firmware counters, not yet decoded).
3. **Model query** – host sends byte `0x4D` (`'M'`); radio replies with 12-byte ASCII model string (`"RT-950"` padded with nulls/spaces).  If the returned string does not contain `RT-950`, abort.
4. **Encryption frame** – host sends a 25-byte frame starting with ASCII `SEND` followed by a negotiation byte and 21 bytes of random material (details below).  Radio responds with ACK `0x06`.
5. After the ACK the negotiated 4-byte XOR key is active until the session ends.  All subsequent 0x80-byte payloads are XOR-obfuscated with that key.

### XOR Negotiation Details
- Negotiation byte (`frame[4]`): high nibble chooses table row, low nibble indexes into the 20-string look-up table the CPS ships (`["BHT ", "CO 7", …, "I LZ"]`).
- CPS (and our transport) fills the remaining 19 bytes with random values (0–19).  The radio uses one of those indexes to choose a keystream symbol.
- Key selection mirrors CPS logic: if bit 5 of the negotiation byte is set, use `(code - 0x20) * 2 + 1`; otherwise `(code - 0x10) * 2`.  Increment by 1, read the byte at `frame[4 + idx]`, and use that as the table index.
- The resulting XOR key is a 4-byte ASCII string; the most common keys observed so far are `b" SAT"`, `b"XN Y"`, `b"RV B"`, etc.
- XOR rule: for each payload byte, advance through the 4-byte key in a loop.  If the key byte is `0x20` (space) or the payload byte is `0x00`, `0xFF`, equal to `key`, or equal to `key ^ 0xFF`, do nothing.  Otherwise XOR the payload byte with the key byte.  This applies symmetrically for reads and writes.

## Memory Map (Clone Segments)
The clone protocol transfers fixed 0x80-byte blocks grouped into segments.  We mirror the CPS order exactly:

| Segment | Command | Address Range | Length | Notes |
|---------|---------|---------------|--------|-------|
| 0 | Read `0x52` / Write `0x57` | `0x0000` – `0x77FF` | 0x7800 | 960 channels (32 bytes each). |
| 1 | `0x52` / `0x57` | `0x8000` – `0x80FF` | 0x0100 | VFO (3 × 32 bytes). |
| 2 | `0x9000` – `0x90FF` | 0x0100 | Function settings. |
| 3 | `0xA000` – `0xA1FF` | 0x0200 | DTMF. |
| 4 | `0xB000` – `0xB1FF` | 0x0200 | Modulation parameters. |
| 5 | `0xD000` – `0xD2FF` | 0x0300 | Modulation names (FM/AM/SSB). |
| 6 | Read `0x54` / Write `0x55` | `0x0000` – `0x007F` | 0x0080 | APRS block (sent after loop over main segments). |

Any bytes beyond the concatenated segment lengths (`sum(DEFAULT_SEGMENTS) == 33152`) are radio-managed.  During our tests, the tail starting around file offset `0x7A87` is rewritten with `0x03` patterns regardless of input.

### Section Notes
- **DTMF (0xA000-0xA1FF)**: Digits use 0-15 codes; the radio treats `0xFF` as the terminator, so a stored digit "0" is encoded as byte `0x00` and must be preserved. The CPS only rewrites the info bytes when values change.
- **Modulation parameters/names (0xB000-0xB2FF, 0xD000-0xD2FF)**: Blank entries may contain `0x00` or `0x04` artifacts instead of `0xFF`; the CPS compares against the original buffer before writing to avoid normalising calibration data.
- **Firmware tail (>0x7A80)**: The radio overwrites this region with `0x03` patterns and housekeeping data on every write; limit integrity checks to the defined segments (<= `0x7A80`).

## Read Flow
For each segment, the host issues repeated 4-byte headers:
```
[command, address_hi, address_lo, 0x80]
```
The radio replies with the same header followed by 0x80 bytes of XOR-obfuscated payload.  After all segments complete, the host sends ASCII `E` to terminate.

Our harness logs each `0x80` request at DEBUG level (`Requesting block: command=0x52 address=0xXXXX`).

## Write Flow
The CPS write state machine (and our transport) processes 0x80-byte blocks using the same header structure.  Differences vs. read:
- Command byte is `0x57` for all segments except the APRS tail, which uses `0x55`.
- After each payload the radio replies with single-byte ACK `0x06`.  No buffered streaming: you must wait for the ACK before moving to the next block.  If the ACK is missing or different, abort immediately.  Our transport now enforces this.
- Block order and segment transitions match the read order; address jumps occur at the same offsets (`0x7800 -> 0x8000`, etc.).
- Writing `E` after the final ACK ends the session.

### Zero/FF Preservation
Channels, VFOs, and other sections use `0xFF` as “unset” sentinels.  The CPS always reuses the previous buffer when a field is unchanged.  To match that behaviour we cache the original bytes for each structure (`_raw_bytes` / `_original_state`) and emit them verbatim when nothing changed.

## Known Behaviours
- **Tail rewrites** – Host-provided data after offset `0x8080` is ignored; the radio writes proprietary housekeeping bytes (`0x03` dotted pattern).  Hash comparisons should therefore be limited to the defined segments when verifying round trips.
- **Channel edits** – Renaming channel 4 to `ABCDEF` changes only the 32-byte slot (0x0094–0x009D) plus the tail.  Frequencies and other channels remain stable.
- **Random keystream** – Each session may negotiate a different XOR key; this is expected.  Logs surface the chosen key at DEBUG (`Negotiated XOR key: XXXX`).

## Outstanding Questions
- Are there additional host commands (e.g., to toggle encryption off) that the CPS never exercises?
- Can the tail region be interpreted (settings cache, checksums, BLE pairing info)?  For now we treat it as opaque.
- Timeout/retry behaviour – we have not forced error cases to observe the CPS’s retry cadence.

## Reference Commands
```
# Verbose write using our harness
python -m rt950pro --verbose image clone-write --port COM5 --input dumps\loop_original.bin

# Follow-up read and partial hash check (<= 0x8080)
python -m rt950pro --verbose image clone-read --port COM5 --output dumps\loop_after.bin
python - <<'PY'
from pathlib import Path, hashlib
limit = 0x8080
orig = Path('dumps/loop_original.bin').read_bytes()
new = Path('dumps/loop_after.bin').read_bytes()
print(hashlib.sha256(orig[:limit]).hexdigest())
print(hashlib.sha256(new[:limit]).hexdigest())
PY
```

Feel free to extend this document with oscilloscope traces, timing measurements, or retry behaviour once we explore failure scenarios.

