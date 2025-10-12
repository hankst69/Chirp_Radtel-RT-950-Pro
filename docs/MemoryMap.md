# RT-950 Pro Memory Map (Working Notes)

This document consolidates the current understanding of the RT-950 Pro’s nonvolatile layout and the protocol commands that access each region. Addresses are offsets within the clone/EEPROM view unless otherwise noted. Treat any region marked Unknown/Read-only with caution.

## Clone Space (0x0000–0xFFFF via 0x52/0x57)

- 0x0000–0x77FF — Channels (960 × 32 B)
  - Status: Known. Parsed/encoded by harness.
  - Access: Read `0x52`, Write `0x57`.
  - Reference: `rt950pro/transport.py:82` (first segment).

- 0x7800–0x7FFF — 2 KB “gap”
  - Status: Unknown. CPS skips; both radios read as 0xFF. Suspect calibration shadow managed by firmware.
  - Access: Clone read returns data; CPS never writes. Do not write.

- 0x8000–0x80FF — VFO A/B/C (3 × 0x80)
  - Status: Known.
  - Access: Read `0x52`, Write `0x57`.

- 0x9000–0x90FF — Function configuration (3 × 0x80)
  - Status: Known.
  - Access: Read `0x52`, Write `0x57`.

- 0xA000–0xA1FF — DTMF settings and code groups
  - Status: Known.
  - Access: Read `0x52`, Write `0x57`.

- 0xB000–0xB0FF — Modulation parameters
  - Status: Known.
  - Access: Read `0x52`, Write `0x57`.

- 0xC000–0xCFFF — Reserved/Unknown
  - Status: Unknown. Not referenced by CPS.
  - Access: Readable via `0x52`; contents not mapped. Do not write.

- 0xD000–0xD2FF — String/name area (~0x300 B)
  - Status: Known (text blocks; GB2312).
  - Access: Read `0x52`, Write `0x57`.

- 0xD300–0xDFFF — Reserved/Unknown
  - Status: Unknown. Not referenced by CPS.
  - Access: Readable via `0x52`; contents not mapped. Do not write.

- 0xE000–0xFFFF — Firmware-managed tail (calibration/tables)
  - Status: Inferred. Readable; differs significantly between units; writing here altered TX/VFO behaviour.
  - Access: Readable via `0x52`. Treat as read-only.

Notes:
- The radio will serve data across 0x0000–0xFFFF with `0x52` even where CPS does not operate. CPS write logic purposely skips 0x7800–0x7FFF and only streams the defined blocks.
- Session terminator after reads/writes: `0x45` (`'E'`).

## APRS Block (separate command set)

- 0x0000–0x007F (relative) — APRS parameters
  - Status: Known.
  - Access: Read `0x54`, Write `0x55` (streamed after the main clone pass).
  - Note: Address is relative to the APRS command space, not the `0x52/0x57` map above.

## Startup Picture Region (flash, separate protocol)

- Base address: 0x090000 in flash
  - Status: Known from CPS source (`ImportBmpOperation`).
  - Protocol: Packet header `0xA5`; commands `CMD_HANDSHAKE (0x02)`, `CMD_SETADDRESS (0x03)`, `CMD_ERASE (0x04)`, `CMD_WRITE (0x57)` with 1024‑byte payloads, and `CMD_OVER (0x06)`.
  - Readback: No read opcode exposed in CPS path; uploader is write‑only.

## Firmware Update Region (bootloader protocol)

- Uses a distinct bootloader channel (header `0xAA` … `0x55`).
  - Commands include: `HANDSHAKE (10)`, `INTO_BOOT (66)`, `INTO_ERASE_MODE (238)`, `CHECKMODELTYPE (2)`, `UPDATE_DATA_PACKAGES (4)`, `UPDATE (3)` (1 KB pages), `UPDATE_END (69)`.
  - Targets program flash; unrelated to the 0x0000–0xFFFF clone space.

## Safety Guidance

- Do not write 0x7800–0x7FFF or 0xE000–0xFFFF via clone; evidence indicates calibration/firmware‑managed data live there.
- Treat unknown/reserved regions as read‑only until mapped.
- The APRS and startup picture use separate command sets; do not mix them with clone operations.

## References

- Clone segments definition: `rt950pro/transport.py:82`
- CPS read/write state machine: `Reference/BT-RT950PRO_CPS-1.1.0/BT-RT950PRO_CPS/RWDataOperation.cs`
- APRS phase (0x54/0x55): same CPS file after main pass
- Startup picture uploader: `Reference/BT-RT950PRO_CPS-1.1.0/BT-RT950PRO_CPS/ImportBmpOperation.cs`
- Bootloader updater: `Reference/RT-950_EnUPDATE/BootHelper.cs`

