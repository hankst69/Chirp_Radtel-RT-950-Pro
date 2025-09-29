# Project Agents

## Nathan (_2E0NBS)
- Role: Project owner and hardware contact.
- Responsibilities: Provide radio dumps, confirm on-device behaviour, review deliverables, approve protocol assumptions.

## Codex (GPT-5 Assistant)
- Role: Implementation partner.
- Responsibilities: Produce CHIRP driver code, automated harness, documentation, and testing assets in alignment with DESIGN.md.

## Future Contributors
- Adopt Python docstrings ("""...""") for all public functions, methods, and classes to keep autodoc coverage complete.
- Encourage pull requests for documentation updates, harness improvements, and expanded test coverage.
- Coordinate any on-radio testing through Nathan before merging changes affecting the clone protocol.

- When editing files via inline PowerShell scripts, prefer writing the full Python or patch script into a temporary `.py` or `.diff` file and executing it rather than relying on inline `-c` strings. This avoids nesting/escaping problems with quotes (single, double, and triple). For example:
  1. `Set-Content temp_task.py @'<script contents>'`
  2. `.\.venv\Scripts\python.exe temp_task.py`
  3. `Remove-Item temp_task.py`
  Use multi-line here-strings (`@' ... '@`) for raw text to keep quoting reliable.
