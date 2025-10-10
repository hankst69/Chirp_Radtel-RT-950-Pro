# User-Focused Change Log — 2025-10-10

What’s new
- Clearer progress during radio cloning (Read/Write):
  - Shows which channels are being transferred, e.g. “Reading channels 001–004…”.
  - Shows when it’s working on settings, e.g. “Writing VFO settings…”, “Reading DTMF settings…”.

- More reliable cloning on some setups:
  - Increased serial timeouts reduce unnecessary “Serial read timed out” messages when a clone actually succeeds.

How it looks in CHIRP
- When you start a clone Read/Write, the progress bar updates with:
  - Channel ranges in steps of 4 (the radio transfers 4 channels per block).
  - Named stages for settings sections near the end of the process.

How to try it
- In CHIRP, use File -> Load Module… and open `chirp_driver/radtel_rt950pro.py` from this repo.
- Perform a Read or Write; watch the progress text for the new messages.

Notes
- No changes to how you program channels — this is a quality-of-life improvement.
- If you see unexpected behavior, please capture the CHIRP debug log and share it.

