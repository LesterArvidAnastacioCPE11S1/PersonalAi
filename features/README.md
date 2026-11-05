# Features

Every new feature module lives in this folder. Wire it into `server.py`, `core/`, or `web/`, but keep the feature logic itself here.

## Current

- `attachments.py` — file uploads from the composer `+` button. Stores files under `data/attachments/`, extracts text from txt/markdown/csv/json/code, PDF, and DOCX, builds the prompt block, and supplies image data URLs when vision is enabled.
- `intents.py` — the intent catalog. Covers starting, summarizing, skipping, deciding, revising, pausing, continuing, rewriting, expanding, time skips, and OOC. Each intent carries example phrases, regex patterns, negation guards, and phase-specific guidance.
- `story_setup.py` — the pre-story interview. Holds the setup-mode and story-mode prompt blocks, the interview stage rules, and Story Brief detection.
- `mobile_access.py` — phone pairing. Generates and checks the access code, finds LAN addresses, and renders the dark login page shown to devices that are not the PC.

## Conventions

- One file per feature, named after the feature.
- The module should own its parsing, validation, and prompt shaping.
- Routes stay in `server.py`; the feature exposes plain methods the routes call.
- Files are stored on disk; metadata and extracted text go in SQLite.
