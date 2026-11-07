# Features

Every new feature module lives in this folder. Wire it into `server.py`, `core/`, or `web/`, but keep the feature logic itself here.

## Current

- `attachments.py` — file uploads from the composer `+` button. Stores files under `data/attachments/`, extracts text from txt/markdown/csv/json/code, PDF, and DOCX, builds the prompt block, and supplies image data URLs when vision is enabled.
- `intent_model.py` — the runtime understanding layer. Loads `models/deberta_intent_v3` (falling back to v2 or the original model) and blends its probabilities with a TF-IDF word+char classifier retrained at startup from `data/intents/train.json` and `validation.json`. Labels, examples, and routing behavior all come from those JSON files; there are no keyword tables in the decision path. Adding examples and restarting is how the assistant learns new phrasings. `training/train.py` rebuilds the DeBERTa checkpoint from the same JSON.
- `intents.py` — maps the learned label to phase-specific prompt guidance. Covers starting, summarizing, skipping, deciding, revising, pausing, continuing, rewriting, expanding, time skips, leaving setup or story for general chat, interface actions, and OOC.
- `request_router.py` — decides whether a message in a general chat is an ordinary request, a request to continue a saved story, or a request to start a new story, using the learned label plus confidence.
- `story_setup.py` — the pre-story interview. Holds the setup-mode and story-mode prompt blocks, the interview stage rules, and Story Brief detection.
- `ui_actions.py` — turns learned interface-command labels into app actions. Covers Settings, Story memory, Scenario, the style picker, the chat list, and starting a new chat. Questions and in-story narration are trained negatives, and the server sends the action to the web UI alongside the reply.
- `story_styles.py` — the storytelling style catalog. Defines the selectable narrative voices, validates and normalizes style keys, and renders the story-only prompt block that changes future narration without touching established canon.
- `mobile_access.py` — phone pairing. Generates and checks the access code, finds LAN addresses, and renders the dark login page shown to devices that are not the PC.

## Conventions

- One file per feature, named after the feature.
- The module should own its parsing, validation, and prompt shaping.
- Routes stay in `server.py`; the feature exposes plain methods the routes call.
- Files are stored on disk; metadata and extracted text go in SQLite.
