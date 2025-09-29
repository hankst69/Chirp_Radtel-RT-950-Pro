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
- Convert between CHIRP’s `Memory` objects and the radio’s raw memory representation.
- Handle downloading (clone/read) and uploading (clone/write).

### General architecture of CHIRP
- **UI Layer:** Provides desktop interface; allows users to edit channels and settings.
- **Core Data Model:** Uses `chirp_common.Memory` objects to represent channel entries generically.
- **Driver Layer:** Contains a set of Python classes (`CloneModeRadio` subclasses) that implement radio-specific behavior.
- **Transport Layer:** Provides generic helpers for serial/USB communication (where applicable).

### Terminology
- **Channel / Memory:** A programmed slot storing frequency, tone, modulation, etc.
- **VFO (Variable Frequency Oscillator):** A mode where the radio tunes to arbitrary frequencies without stored memories.
- **Offset / Duplex:** Used for repeaters; describes transmit frequency relative to receive frequency.
- **Tone / CTCSS / DCS:** Audio signaling used for squelch control.
- **Bank:** A grouping of memories (not all radios support this).
- **Clone:** The process of reading or writing the radio’s entire configuration image.

### Overview of radio communication protocols
Radios commonly use:
- **Serial over USB (most common):** Presents as a virtual COM port on the host computer.
- **Native USB (HID or vendor-specific):** Requires specialized handling.
- **Audio/composite interfaces:** Some radios expose control lines via audio connectors.

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
- **Serial sniffers:** Software tools (e.g., serial port monitors) that capture data exchanged between the radio and software.
- **Logic analyzers:** Hardware devices that capture digital signals for low-level analysis.
- **USB protocol analyzers:** Capture USB traffic directly (for radios using native USB).
- **Hex editors & protocol decoders:** Help interpret binary data, identify patterns, and decode structures.
- **Disassemblers / decompilers (optional):** If vendor software is accessible, these tools can reveal how commands and memory layouts work.

## 4. Getting Started With a New Radio

### Gathering what’s available
1. **User manuals:** Often hint at clone modes, connector types, or programming sequences.
2. **Regulatory filings (e.g., FCC):** May include block diagrams, radio interfaces, and test procedures.
3. **Vendor programming software:** Provides a baseline for protocol behavior; use alongside sniffing tools.
4. **Community resources:** Forums or user groups may already have partial information.

### Establishing a connection
- Identify the correct programming cable.
- Install necessary USB-to-serial drivers or vendor utilities.
- Verify the host computer recognizes the device (e.g., check Device Manager or `lsusb`).

### Detecting communication interfaces
- Determine if the radio enumerates as a COM port.
- Use terminal software or sniffers to observe the initial handshake from vendor software.
- Confirm whether the radio requires a specific COM port configuration (baud rate, parity, etc.).

## 5. Understanding the Protocol

### Identifying how the radio talks
- Determine serial parameters: baud rate, data bits, parity, stop bits.
- Identify framing: Are commands fixed-length, length-prefixed, or delimited?
- Note any handshake sequences (passwords, version requests).

### Capturing raw data exchanges
- Use a serial sniffer or USB analyzer while running vendor software.
- Capture the entire session (connect, read, write) to understand the sequence.
- Store captures systematically (include timestamps and context).

### Pattern recognition in command/response pairs
- Look for repeating patterns: commands, acknowledgments, block sizes.
- Identify checksums or XOR masks by comparing data blocks.

### Distinguishing read vs write operations
- Reads often start with request commands followed by data from the radio.
- Writes typically show host-to-radio data blocks with corresponding acknowledgments.

### Example: generic memory read transaction
1. Host sends a “start clone” command.
2. Radio returns a handshake response.
3. Host requests block 0: `READ 0x0000`.
4. Radio sends 0x80 bytes of data plus checksum.
5. Host acknowledges and requests the next block.
6. Sequence repeats until complete.

## 6. Mapping the Radio’s Data Model

### Radio "memories" and structure
- Each channel memory combines properties like frequency, tone, power level, modulation, and flags.
- Some radios use fixed-size memory blocks per channel; others pack data more densely.

### Frequency, tone, step size, etc.
- Frequencies often stored as Binary Coded Decimal (BCD) or scaled integers.
- Tones (CTCSS/DCS) are encoded as codes or indexes.
- Step size and bandwidth are typically enumerations.

### Encoding/decoding concepts
- Understand bit fields: multiple settings squeezed into a single byte.
- Recognize sentinel values: e.g., 0xFF indicating “unused”.
- Document conversions between raw data and human-readable values.

### Building a mental model of the layout
- Outline the entire clone image: channel section, settings section, tail data.
- Note boundaries of known sections and suspicious padding.
- Update the model iteratively as you decode more attributes.

## 7. Implementing a CHIRP Driver

### Project structure of a CHIRP driver
- Driver code under `chirp/drivers/`, typically a single Python file.
- Exported class inherits from `chirp_common.CloneModeRadio`.
- Register the driver using `@directory.register`.

### Guidelines for writing a new driver class/module
1. Define `VENDOR`, `MODEL`, `BAUD_RATE` (if applicable).
2. Implement `get_features()` describing capabilities (memory bounds, valid modes, etc.).
3. Implement `sync_in()` to download the radio’s image.
4. Implement `sync_out()` to upload a modified image.
5. Convert between CHIRP `Memory` objects and raw structures (`get_memory()` / `set_memory()` or mapped methods).
6. Implement settings (`get_settings()` / `set_settings()`) if the radio exposes global options.

### Defining radio capabilities
- Specify valid frequency ranges, step sizes, tone modes, allowed duplex options.
- Indicate the number of memories.

### Implementing download (read from radio)
- Use a transport class (custom or reused) to handle command sequences.
- Validate payload lengths and checksums.
- Convert raw blocks into structured data objects.

### Implementing upload (write to radio)
- Carefully construct the raw image.
- Back up original data before writing.
- Validate success responses and handle retries or errors gracefully.

### Error handling and edge cases
- Raise `errors.RadioError` with clear messages when encountering unexpected data.
- Guard against partial reads/writes, invalid checksums, or handshake failures.
- Provide logging (ideally adjustable verbosity) for debugging.

## 8. Testing and Validation

### Developing good test cases
- Unit tests to verify encoding/decoding functions (round-tripping sample data).
- Tests covering memory conversions (CHIRP Memory ? radio binary).
- Tests for settings and boundary conditions.

### Iterative testing strategy
1. Start with decoding only (read-only driver).
2. Validate on multiple clone images (if available).
3. Add write support once confident in the data model.
4. Perform small, reversible edits during early hardware tests.

### Debugging tips and tricks
- Use controlled inputs: modify a single field, observe resulting bytes.
- Keep verbose logs to trace communication (handshakes, block numbers).
- Compare CHIRP-generated buffers with vendor software outputs.

### Validating correctness against the physical radio
- Always back up the original configuration.
- After writing, read back and compare (hash or diff).
- Spot-check on the radio’s interface to ensure settings match expectations.

## 9. Collaboration and Contribution

### Following CHIRP coding standards
- Adhere to CHIRP’s code style (PEP 8 + project-specific guidelines).
- Use descriptive logging messages.
- Include docstrings and comments where necessary.

### Submitting drivers to the CHIRP project
- Fork CHIRP’s repository and develop on a dedicated branch.
- Provide unit tests where feasible.
- Submit a pull request with description, testing evidence, and hardware details (without proprietary information).

### Writing documentation for your driver
- Document supported features, known limitations, and prerequisites (e.g., special cables).
- Update the CHIRP wiki or README as requested by maintainers.
- Provide user-facing notes (e.g., required radio menu settings).

### Engaging with the community
- Participate in mailing lists or forums to share findings, request guidance, or report unusual behavior.
- Be responsive to reviewer feedback.
- Respectfully share partial discoveries; others may build upon them.

## 10. Best Practices and Pitfalls

### Common mistakes to avoid
- Writing to the radio before fully understanding the protocol.
- Assuming a section layout without verifying via multiple samples.
- Ignoring sentinel or checksum bytes.
- Hard-coding assumptions about block sizes.

### Safety precautions (avoiding bricking a radio)
- Always back up the original image and keep it safe.
- Limit scope of early writes (change one channel, not the entire memory map).
- Power the radio with a stable supply during cloning (avoid low battery scenarios).
- Implement thorough sanity checks before allowing writes.

### Continuous learning resources
- Study existing CHIRP drivers for similar radios.
- Follow blog posts and talks on reverse engineering and embedded systems.
- Experiment with generic test rigs (loopback devices) to build confidence.

## 11. Additional Resources

### Developer documentation
- CHIRP’s official developer guide (refer to project repository).
- Python documentation for modules used in drivers.

### Recommended tools and libraries
- Serial sniffing software (e.g., PortMon, Wireshark with serial dissector).
- USB protocol analyzers (hardware or software).
- Python’s `pyserial` for quick experiments.
- Hex editors (e.g., wxHexEditor, HxD).

### Where to ask for help
- CHIRP mailing lists or forums.
- Community chat channels (if available).
- Experienced contributors mentioned in the CHIRP repository.

# Appendix

## Glossary of terms
- **ACK:** Acknowledge byte sent after successful receipt.
- **Baud rate:** Number of symbols per second in serial communication.
- **Clone:** Full dump of a radio’s configuration.
- **CTCSS/DCS:** Sub-audible tone systems for selective squelch.
- **Driver:** In CHIRP, a module that translates between CHIRP data structures and a radio’s protocol.
- **VFO:** Mode where frequency is tuned freely rather than using stored memories.

## Example driver skeleton (pseudo-code)

```python
from chirp import directory, errors, chirp_common

@directory.register
class ExampleRadioDriver(chirp_common.CloneModeRadio):
    VENDOR = "ExampleCorp"
    MODEL = "ExampleRadio 1000"
    BAUD_RATE = 9600

    def get_features(self):
        features = chirp_common.RadioFeatures()
        features.memory_bounds = (0, 199)
        features.valid_bands = [(100_000_000, 200_000_000)]
        features.has_name = True
        # Populate additional capability flags...
        return features

    def sync_in(self):
        # 1. Establish connection
        # 2. Perform handshake
        # 3. Download binary image from radio
        # 4. Parse into internal data structures
        pass

    def sync_out(self):
        # 1. Reconstruct binary image from internal objects
        # 2. Upload to radio with proper checksums and acknowledgments
        pass

    def get_memory(self, number):
        # Convert from internal representation to chirp_common.Memory
        pass

    def set_memory(self, mem):
        # Translate chirp_common.Memory back to internal structures
        pass
```

## Checklist for junior engineers

1. **Preparation**
   - [ ] Gather manuals, vendor software, and community notes.
   - [ ] Acquire proper cables and drivers.
   - [ ] Set up workspace (Python environment, CHIRP source code).

2. **Observation**
   - [ ] Capture communications while using vendor software (read & write).
   - [ ] Record serial/USB parameters and handshakes.

3. **Analysis**
   - [ ] Identify command structure, blocks, checksums.
   - [ ] Map out memory sections and data layout.
   - [ ] Document findings continuously.

4. **Implementation**
   - [ ] Create driver skeleton in CHIRP.
   - [ ] Implement decoding and read-only support first.
   - [ ] Add encoding and write support once confident.

5. **Testing**
   - [ ] Build unit tests for encoding/decoding.
   - [ ] Conduct read/write tests on hardware with minimal changes.
   - [ ] Confirm results via dump comparisons and on-radio inspection.

6. **Contribution**
   - [ ] Clean up code, conform to style guidelines.
   - [ ] Provide documentation and test evidence.
   - [ ] Submit driver upstream and engage with reviewers.
