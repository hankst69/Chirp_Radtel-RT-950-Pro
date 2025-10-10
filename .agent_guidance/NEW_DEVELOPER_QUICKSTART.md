# CHIRP Driver Development Training Manual

## 1. Introduction

### Purpose of this guide
This manual guides junior engineers through the end-to-end process of creating a new CHIRP-compatible driver for an unfamiliar radio. It explains background concepts, recommended workflows, tools, and best practices, enabling you to work safely and confidently when faced with unknown radio hardware.

### Audience and prerequisites
- Junior software engineers or hobbyist developers.
- Comfortable with Python programming and basic debugging tools.
- Familiar with using the command line and version control (Git).
- No prior experience with radios, RF concepts, or CHIRP is required.

### What is CHIRP?
CHIRP is an open-source programming utility that allows users to read, modify, and write configuration data for a wide range of radios. Each supported radio has a driver that translates between CHIRP’s generic data model and the radio’s specific communication protocol and memory layout.

### Overview: how CHIRP interacts with radios via drivers
1. The user selects a radio model from CHIRP’s interface.
2. CHIRP loads the corresponding driver.
3. The driver communicates with the radio (usually over a serial-like connection) to download memory data.
4. The user edits the data generically in CHIRP.
5. The driver converts edits back into the radio’s raw format and uploads them to the radio.

Understanding both CHIRP’s expectations and the radio’s behavior is crucial to building a reliable driver.

## 2. Fundamentals

### What is a "driver" in CHIRP?
A CHIRP driver is a Python module that implements the logic required to:
- Claim capabilities (e.g., supported memory slots, features).
- Establish communication with the radio.
- Convert between CHIRP's `Memory` objects and the radio's raw memory representation.
- Handle downloading (clone/read) and uploading (clone/write).

### General architecture of CHIRP
- UI Layer: Provides desktop interface; allows users to edit channels and settings.
- Core Data Model: Uses `chirp_common.Memory` objects to represent channel entries generically.
- Driver Layer: Contains a set of Python classes (`CloneModeRadio` subclasses) that implement radio-specific behavior.
- Transport Layer: Provides generic helpers for serial/USB communication (where applicable).

### Terminology
- Channel / Memory: A programmed slot storing frequency, tone, modulation, etc.
- VFO (Variable Frequency Oscillator): A mode where the radio tunes to arbitrary frequencies without stored memories.
- Offset / Duplex: Used for repeaters; describes transmit frequency relative to receive frequency.
- Tone / CTCSS / DCS: Audio signaling used for squelch control.
- Bank: A grouping of memories (not all radios support this).
- Clone: The process of reading or writing the radio's entire configuration image.

### Overview of radio communication protocols
Radios commonly use:
- Serial over USB (most common): Presents as a virtual COM port on the host computer.
- Native USB (HID or vendor-specific): Requires specialized handling.
- Audio/composite interfaces: Some radios expose control lines via audio connectors.

Regardless of physical interface, communication typically involves:
- A handshake or login sequence.
- Binary commands identified by opcodes or text tokens.
- A sequence of read/write blocks with checksums or XOR masks.

## 3. The Reverse Engineering Mindset

### What reverse engineering means in this context
You will interpret how an unknown radio communicates by observing its behavior, without official documentation. This includes understanding command structure, timing, and memory layout by analyzing data captures and the behavior of any vendor software.

### Legal / ethical considerations
- Respect firmware licensing and usage terms. Do not distribute proprietary firmware or encryption keys.
- Obtain radios legitimately; avoid violating warranties.
- Ensure your work complies with local regulations and community standards.

### Tools of the trade
- Serial sniffers: Software tools (e.g., serial port monitors) that capture data exchanged between the radio and software.
- Logic analyzers: Hardware devices that capture digital signals for low-level analysis.
- USB protocol analyzers: Capture USB traffic directly (for radios using native USB).
- Hex editors & protocol decoders: Help interpret binary data, identify patterns, and decode structures.
- Disassemblers / decompilers (optional): If vendor software is accessible, these tools can reveal how commands and memory layouts work.

## 4. Getting Started With a New Radio

### Gathering what's available
1. User manuals: Often hint at clone modes, connector types, or programming sequences.
2. Regulatory filings (e.g., FCC): May include block diagrams, radio interfaces, and test procedures.
3. Vendor programming software: Provides a baseline for protocol behavior; use alongside sniffing tools.
4. Community resources: Forums or user groups with shared experiences.

... (unchanged main content retained) ...

## Addendum: CSV Defaults and UI Progress (RT‑950 Pro)

- CSV export compatibility (DtcsCode defaults)
  - CHIRP’s CSV exporter validates `DtcsCode` and `RxDtcsCode` even when `tmode` is blank.
  - Use the first valid DCS code (`023`) as a placeholder for non‑DTCS rows.
  - Initialize when building `chirp_common.Memory`:
    - `mem.dtcs = mem.rx_dtcs = chirp_common.DTCS_CODES[0]  # 23`
    - Leave `mem.tmode = ''` unless the channel uses DCS.
    - If an incoming `Memory` has `tmode == 'DTCS'` but either code is `0`, normalize to OFF before applying back to the channel.

- UI progress updates
  - Use `chirp_common.Status` + `self.status_fn(status)`.
  - Before a long operation: set `status.cur = 0`, `status.max = total_blocks`, `status.msg = 'Cloning from radio…'` (or `'Cloning to radio…'`), then call the callback.
  - During the per‑block loop: update `status.cur = blocks_done` and call the callback.
  - If block I/O is inside a transport helper, expose `progress_cb(done, total, phase)` and adapt to `Status` in the driver.

- Serial timeout floor
  - If the serial object has unset/too‑low timeouts, set a floor of `3.0` seconds in the transport constructor. Do not override higher values set upstream.

- Band/mode enforcement
  - Expand `valid_bands` to reflect actual behavior (e.g., 18–64 MHz FM/NFM; 118–137 MHz AM RX only).
  - When applying `Memory` → channel:
    - Airband (118–137 MHz): force AM, disable TX.
    - 18–64 MHz: FM only; allow NFM/WFM bandwidth selection.

- Bandwidth bit conventions
  - For the RT‑950 Pro image flags: bit6=1 → NARROW; bit6=0 → WIDE.
  - Keep channel and VFO encode/decode consistent and map `NFM` ↔ NARROW, `FM` ↔ WIDE.
