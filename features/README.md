# Features

Every new feature module lives in this folder. Wire it into `server.py`, `core/`, or `web/`, but keep the feature logic itself here.

## Current

- `attachments.py` — file uploads from the composer `+` button. Stores files under `data/attachments/`, extracts text from supported text/code, PDF, DOCX, and image files using local OCR, builds the prompt block, and supplies image data URLs for vision analysis when OCR finds no text.
- `project_agents.py` — coordinated Roblox investigations. Project Scout alone reads the project index, Code Analyst returns cited findings and structured retrieval requests without direct tool access, and Solution Planner receives evidence only after the coordinator verifies coverage. The JSON manifest and progress history persist in SQLite; phase updates stream to chat.
- The Projects workspace indexes parsed instance properties alongside the hierarchy and exposes saved investigation manifests and event history, so reviews can be inspected after the chat response ends.
- `image_ocr.py` — extracts text from uploaded images locally with RapidOCR and ONNX Runtime; OCR text is available to attachment search and the coding model.
- `intent_model.py` — the runtime understanding layer. Defaults to a fast TF-IDF word+character classifier trained only from `data/intents/train.json`; `validation.json` is held out for evaluation. Set `PAI_INTENT_BACKEND=auto` to blend it with the local DeBERTa v4/v3/v2 checkpoint. `training/train.py` rebuilds the DeBERTa checkpoint from the same data.
- `intents.py` — maps learned intent labels to phase-specific prompt guidance and resolves assistant mode as general chat, story, or coding using the message, recent context, and active project. Covers story controls, coding follow-ups, interface actions, and OOC.
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
