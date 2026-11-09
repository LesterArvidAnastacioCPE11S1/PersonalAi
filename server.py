import json
import os
import re
import threading
import time

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import load_config, save_config
from core.backup import snapshot
from core.engine import ChatEngine
from core.memory import MemoryBusy, MemoryWriter
from core.store import Store
from features.attachments import (
    MAX_FILE_BYTES,
    AttachmentError,
    AttachmentNotFound,
    AttachmentService
)
from features.image_gen import ImageError, ImageService
from features.intent_model import start_warmup
from features.intents import intents_from, understand
from features.mobile_access import (
    COOKIE_NAME,
    HEADER_NAME,
    generate_token,
    is_loopback,
    lan_addresses,
    login_page,
    normalize_token,
    token_valid
)
from features.request_router import RequestRouter
from features.story_setup import has_story_brief
from features.ui_actions import match_action
from features.story_styles import (
    is_style_key,
    normalize_style,
    style_options
)
from models.openai_compat import ModelError, OpenAICompatibleModel


config = load_config()

if config.app.mobile_access and not config.app.access_token:

    config.app.access_token = generate_token()
    save_config(config)

snapshot(config.app.db_path)

store = Store(config.app.db_path)

model = OpenAICompatibleModel(config.model)

engine = ChatEngine(
    config,
    store,
    model
)

memory = MemoryWriter(
    store,
    model,
    config
)

attachments = AttachmentService(
    config,
    store
)

images = ImageService(
    config,
    store,
    attachments
)

router = RequestRouter()

CHAT_SWITCH_PATTERNS = (
    re.compile(
        r"\b(let'?s|lets|how about|can we|could we|i want to|i wanna|"
        r"i'?d rather|i just want to|maybe we should)\b"
        r".{0,30}\b(chat|talk|conversation)\b"
    ),
    re.compile(
        r"\b(stop|no more|forget|skip|drop|cancel|scrap|never ?mind|"
        r"quit|end)\b.{0,25}\bstor(y|ies)\b"
    ),
    re.compile(
        r"\b(chat|talk)\b.{0,12}\b(first|instead|for now)\b"
    )
)


def wants_chat_mode(message, understanding, phase):

    """Decide whether the user is leaving story setup or story mode.

    The classifier alone is too strict for soft phrasing such as
    "how about lets have a chat first", so inside setup or story the
    mode_chat score only has to be plausible when the wording also
    clearly asks to chat.
    """

    if understanding is None:

        return False

    scores = understanding.scores or {}
    mode_score = float(scores.get("mode_chat", 0.0))

    if understanding.label == "mode_chat" and mode_score >= 0.45:

        return True

    if phase not in {"setup", "story"}:

        return False

    text = " ".join((message or "").lower().split())

    if not any(pattern.search(text) for pattern in CHAT_SWITCH_PATTERNS):

        return False

    return mode_score >= 0.10

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app):

    start_warmup()

    yield


app = FastAPI(title="PersonalAI", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static"
)


@app.middleware("http")
async def no_ui_cache(request, call_next):

    response = await call_next(request)

    if (
        request.url.path == "/"
        or request.url.path.startswith("/static/")
    ):

        response.headers["Cache-Control"] = "no-store"

    return response


def _request_token(request):

    header = request.headers.get(HEADER_NAME, "")

    if header:

        return header, "header"

    cookie = request.cookies.get(COOKIE_NAME, "")

    if cookie:

        return cookie, "cookie"

    query = request.query_params.get("token", "")

    if query:

        return query, "query"

    return "", ""


@app.middleware("http")
async def require_access_code(request, call_next):

    if not config.app.mobile_access or not config.app.access_token:

        return await call_next(request)

    client = request.client.host if request.client else ""

    if is_loopback(client):

        return await call_next(request)

    provided, source = _request_token(request)

    if not token_valid(config.app.access_token, provided):

        if request.url.path.startswith("/api/"):

            return JSONResponse(
                {"detail": "Access code required."},
                status_code=401
            )

        return HTMLResponse(
            login_page("Wrong or missing access code."),
            status_code=401
        )

    response = await call_next(request)

    if source in {"header", "query"}:

        response.set_cookie(
            COOKIE_NAME,
            config.app.access_token,
            max_age=31536000,
            httponly=True,
            samesite="lax",
            path="/"
        )

    return response


@app.get("/pair")
def pair():

    return RedirectResponse("/", status_code=303)


class ConversationCreate(BaseModel):
    title: str | None = None
    premise: str = ""
    setting: str = ""
    characters: str = ""
    style: str = ""
    narrative_style: str = ""


class ConversationUpdate(BaseModel):
    title: str | None = None
    premise: str | None = None
    setting: str | None = None
    characters: str | None = None
    style: str | None = None
    narrative_style: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = ""
    attachments: list[str] = []
    edit_message_id: int | None = None


class PhaseUpdate(BaseModel):
    phase: str


class ImageRequest(BaseModel):
    conversation_id: str
    message_id: int | None = None
    prompt: str | None = None


class SettingsUpdate(BaseModel):
    model: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    no_refusals: bool | None = None
    custom_instructions: str | None = None
    auto_extract: bool | None = None
    extract_every: int | None = None
    vision: bool | None = None
    vision_model: str | None = None
    mobile_access: bool | None = None
    access_token: str | None = None


class LoreCreate(BaseModel):
    category: str = "fact"
    subject: str = ""
    detail: str
    keywords: str = ""


class LoreUpdate(BaseModel):
    category: str | None = None
    subject: str | None = None
    detail: str | None = None
    keywords: str | list[str] | None = None


def _phone_urls():

    port = config.app.port

    return [
        f"http://{address}:{port}"
        for address in lan_addresses()
    ]


def _settings_payload(available=None):

    return {
        "model": config.model.model,
        "base_url": config.model.base_url,
        "temperature": config.model.temperature,
        "max_tokens": config.model.max_tokens,
        "no_refusals": config.behavior.no_refusals,
        "custom_instructions": config.behavior.custom_instructions,
        "auto_extract": config.memory.auto_extract,
        "extract_every": config.memory.extract_every,
        "vision": config.model.vision,
        "vision_model": config.model.vision_model,
        "mobile_access": config.app.mobile_access,
        "access_token": config.app.access_token,
        "phone_urls": _phone_urls(),
        "context": {
            "max_messages": config.context.max_messages,
            "max_chars": config.context.max_chars
        },
        "available": available or []
    }


def _event(name, data):

    return (
        f"event: {name}\n"
        f"data: {json.dumps(data)}\n\n"
    )


def _last_assistant(conversation_id):

    for row in reversed(store.get_messages(conversation_id)):

        if row["role"] == "assistant":

            return row

    return None


@app.get("/")
def index():

    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/ping")
def ping():

    return {"ok": True}


@app.get("/api/status")
def status():

    available = []
    error = None

    try:

        available = model.available_models()

    except Exception as exception:

        error = str(exception)

    return {
        "online": error is None,
        "error": error,
        "model": config.model.model,
        "vision": config.model.vision,
        "vision_model": config.model.vision_model,
        "base_url": config.model.base_url,
        "available": available,
        "image": images.status()
    }


def _force_exit():

    time.sleep(0.6)
    os._exit(0)


@app.post("/api/shutdown")
def shutdown_app():

    callback = getattr(app.state, "shutdown", None)

    if callback is None:

        callback = _force_exit

    threading.Thread(target=callback, daemon=True).start()

    return {"stopping": True}


@app.get("/api/styles")
def get_styles():

    return {
        "styles": style_options()
    }


@app.get("/api/settings")
def get_settings():

    available = []

    try:

        available = model.available_models()

    except Exception:

        available = []

    return _settings_payload(available)


@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate):

    values = {
        key: value
        for key, value in payload.model_dump(
            exclude_unset=True
        ).items()
        if value is not None
    }

    endpoint_changed = False

    if "model" in values:

        config.model.model = str(
            values["model"] or ""
        ).strip()
        endpoint_changed = True

    if "base_url" in values:

        base_url = str(values["base_url"] or "").strip()

        if base_url:

            config.model.base_url = base_url
            endpoint_changed = True

    if "temperature" in values:

        config.model.temperature = min(
            2.0,
            max(0.0, float(values["temperature"]))
        )

    if "max_tokens" in values:

        config.model.max_tokens = min(
            8192,
            max(64, int(values["max_tokens"]))
        )

    if "no_refusals" in values:

        config.behavior.no_refusals = bool(
            values["no_refusals"]
        )

    if "custom_instructions" in values:

        config.behavior.custom_instructions = str(
            values["custom_instructions"] or ""
        )[:4000]

    if "auto_extract" in values:

        config.memory.auto_extract = bool(
            values["auto_extract"]
        )

    if "extract_every" in values:

        config.memory.extract_every = min(
            50,
            max(1, int(values["extract_every"]))
        )

    if "vision" in values:

        config.model.vision = bool(values["vision"])

    if "vision_model" in values:

        config.model.vision_model = str(
            values["vision_model"] or ""
        ).strip()

        model.refresh()

    if "access_token" in values:

        token = normalize_token(values["access_token"])

        if token and len(token) < 6:

            raise HTTPException(
                status_code=400,
                detail="Access code must be at least 6 characters."
            )

        if token:

            config.app.access_token = token

    if "mobile_access" in values:

        config.app.mobile_access = bool(
            values["mobile_access"]
        )

        if (
            config.app.mobile_access
            and not config.app.access_token
        ):

            config.app.access_token = generate_token()

    if endpoint_changed:

        model.refresh()

    save_config(config)

    available = []

    try:

        available = model.available_models()

    except Exception:

        available = []

    return _settings_payload(available)


@app.post("/api/settings/mobile-token")
def rotate_access_code():

    config.app.access_token = generate_token()

    save_config(config)

    available = []

    try:

        available = model.available_models()

    except Exception:

        available = []

    return _settings_payload(available)


@app.get("/api/conversations")
def list_conversations():

    return {
        "conversations": store.list_conversations()
    }


@app.post("/api/conversations")
def create_conversation(payload: ConversationCreate):

    if not is_style_key(payload.narrative_style):

        raise HTTPException(
            status_code=400,
            detail="Unknown storytelling style."
        )

    return {
        "conversation": store.create_conversation(
            title=payload.title,
            premise=payload.premise,
            setting=payload.setting,
            characters=payload.characters,
            style=payload.style,
            narrative_style=normalize_style(
                payload.narrative_style
            )
        )
    }


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):

    conversation = store.get_conversation(
        conversation_id
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "conversation": conversation,
        "messages": store.get_messages(conversation_id),
        "attachments": [
            attachments.public(row)
            for row in store.list_attachments(conversation_id)
        ]
    }


@app.patch("/api/conversations/{conversation_id}")
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate
):

    if store.get_conversation(conversation_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    values = payload.model_dump(exclude_unset=True)

    if "narrative_style" in values:

        if values["narrative_style"] is None:

            values.pop("narrative_style")

        else:

            if not is_style_key(values["narrative_style"]):

                raise HTTPException(
                    status_code=400,
                    detail="Unknown storytelling style."
                )

            values["narrative_style"] = normalize_style(
                values["narrative_style"]
            )

    conversation = store.update_conversation(
        conversation_id,
        values
    )

    return {
        "conversation": conversation
    }


@app.post("/api/conversations/{conversation_id}/phase")
def update_phase(conversation_id: str, payload: PhaseUpdate):

    phase = payload.phase.strip().lower()

    if phase not in {"chat", "setup", "story"}:

        raise HTTPException(
            status_code=400,
            detail="Phase must be chat, setup, or story."
        )

    conversation = store.set_phase(
        conversation_id,
        phase
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    if phase == "setup":

        conversation = store.set_setup_start(
            conversation_id,
            store.last_message_id(conversation_id)
        ) or conversation

    return {
        "conversation": conversation
    }


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):

    rows = store.list_attachments(conversation_id)

    deleted = store.delete_conversation(
        conversation_id
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    attachments.remove_files(rows)

    return {
        "deleted": True
    }


@app.post("/api/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(...)
):

    if store.get_conversation(conversation_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    data = await file.read(MAX_FILE_BYTES + 1)

    try:

        row, warning = attachments.save(
            conversation_id,
            file.filename or "file",
            data
        )

    except AttachmentError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    return {
        "attachment": attachments.public(row),
        "warning": warning
    }


@app.post("/api/images/generate")
def generate_image(payload: ImageRequest):

    conversation = store.get_conversation(payload.conversation_id)

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    if payload.message_id is not None:

        row = store.get_message(payload.message_id)

        if row is None or row["conversation_id"] != payload.conversation_id:

            raise HTTPException(
                status_code=404,
                detail="Message not found in this conversation."
            )

    try:

        attachment, prompt = images.generate(
            payload.conversation_id,
            payload.message_id,
            payload.prompt
        )

    except ImageError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        ) from error

    return {
        "attachment": attachment,
        "prompt": prompt
    }


@app.get("/api/attachments/{attachment_id}/file")
def attachment_file(attachment_id: str):

    row = store.get_attachment(attachment_id)

    if row is None:

        raise HTTPException(
            status_code=404,
            detail="Attachment not found."
        )

    try:

        path = attachments.file_path(row)

    except AttachmentNotFound as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    mime = row["mime"] or "application/octet-stream"

    if mime in {
        "text/html",
        "application/xhtml+xml",
        "application/xml",
        "text/xml"
    }:

        mime = "text/plain; charset=utf-8"

    return FileResponse(
        path,
        media_type=mime,
        filename=row["filename"],
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"}
    )


@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: str):

    try:

        attachments.delete_unlinked(attachment_id)

    except AttachmentNotFound as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    except AttachmentError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error)
        ) from error

    return {
        "deleted": True
    }


@app.get("/api/conversations/{conversation_id}/memory")
def get_memory(conversation_id: str):

    if store.get_conversation(conversation_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    data = store.get_memory(conversation_id)

    data["due"] = memory.due(conversation_id)
    data["running"] = memory.running(conversation_id)

    return data


@app.post("/api/conversations/{conversation_id}/memory/extract")
def extract_memory(conversation_id: str):

    if store.get_conversation(conversation_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    try:

        result = memory.run(
            conversation_id,
            force=True
        )

    except MemoryBusy as error:

        raise HTTPException(
            status_code=409,
            detail=str(error)
        ) from error

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    except ModelError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        ) from error

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=f"Memory update failed: {error}"
        ) from error

    result["due"] = memory.due(conversation_id)
    result["running"] = False

    return result


@app.post("/api/conversations/{conversation_id}/lore")
def create_lore(
    conversation_id: str,
    payload: LoreCreate
):

    if store.get_conversation(conversation_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    detail = payload.detail.strip()

    if not detail:

        raise HTTPException(
            status_code=400,
            detail="Detail is required."
        )

    row = store.add_lore(
        conversation_id,
        category=payload.category,
        subject=payload.subject,
        detail=detail,
        keywords=payload.keywords,
        source="manual"
    )

    return {
        "lore": row
    }


@app.patch("/api/lore/{lore_id}")
def update_lore(lore_id: int, payload: LoreUpdate):

    if store.get_lore(lore_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Memory entry not found."
        )

    values = {
        key: value
        for key, value in payload.model_dump(
            exclude_unset=True
        ).items()
        if value is not None
    }

    if "detail" in values and not str(
        values["detail"] or ""
    ).strip():

        raise HTTPException(
            status_code=400,
            detail="Detail is required."
        )

    row = store.update_lore(lore_id, values)

    return {
        "lore": row
    }


@app.delete("/api/lore/{lore_id}")
def delete_lore(lore_id: int):

    if not store.delete_lore(lore_id):

        raise HTTPException(
            status_code=404,
            detail="Memory entry not found."
        )

    return {
        "deleted": True
    }


TITLE_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "just", "have",
    "from", "your", "story", "new", "chat", "about", "into", "they",
    "them", "what", "when", "where", "will", "would", "could",
    "should", "there", "here", "some", "then", "than", "very"
}


def _story_conversations():

    return [
        item for item in store.list_conversations()
        if item.get("phase") == "story"
    ]


def _match_story(message, stories):

    lowered = (message or "").lower()

    for story in stories:

        title = (story.get("title") or "").strip()

        if not title or title.lower() == "new chat":

            continue

        if title.lower() in lowered:

            return story

        words = [
            word for word in re.findall(r"[a-z]{4,}", title.lower())
            if word not in TITLE_STOPWORDS
        ]

        if (
            1 <= len(words) <= 4
            and all(word in lowered for word in words)
        ):

            return story

    return None


def _adopt_story(conversation_id, story):

    values = {
        key: story.get(key) or ""
        for key in (
            "title",
            "premise",
            "setting",
            "characters",
            "style",
            "narrative_style"
        )
    }

    store.update_conversation(conversation_id, values)

    if story.get("summary"):

        store.set_summary(conversation_id, story["summary"])

    for item in store.list_lore(story["id"]):

        store.add_lore(
            conversation_id,
            category=item.get("category") or "fact",
            subject=item.get("subject") or "",
            detail=item.get("detail") or "",
            keywords=item.get("keywords") or "",
            source="import"
        )

    return store.set_phase(conversation_id, "story")


@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest):

    conversation = store.get_conversation(
        payload.conversation_id
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    message = payload.message.strip()
    edit_id = payload.edit_message_id
    rows = []
    saved = None

    if edit_id is not None:

        saved = store.get_message(edit_id)

        if (
            saved is None
            or saved["conversation_id"] != payload.conversation_id
            or saved["role"] != "user"
        ):

            raise HTTPException(
                status_code=400,
                detail="Only a message in this conversation can be edited."
            )

        if not message:

            raise HTTPException(
                status_code=400,
                detail="Message is empty."
            )

        removed, _ = store.truncate_after(
            payload.conversation_id,
            edit_id
        )

        attachments.remove_files(removed)

        store.update_message(edit_id, message)
        store.auto_title(payload.conversation_id, message)
        saved = store.get_message(edit_id)
        rows = store.list_attachments(
            payload.conversation_id,
            message_id=edit_id
        )

    else:

        try:

            rows = attachments.ready(
                payload.conversation_id,
                payload.attachments
            )

        except AttachmentError as error:

            raise HTTPException(
                status_code=400,
                detail=str(error)
            ) from error

        if not message and not rows:

            raise HTTPException(
                status_code=400,
                detail="Message is empty."
            )

    understanding = understand(message) if message else None
    intents = intents_from(understanding)
    action = None
    mode_chat = False
    notes = []
    activated_setup = False
    previous_phase = conversation.get("phase") or "chat"

    if message and edit_id is None:

        action = match_action(message, understanding)
        mode_chat = wants_chat_mode(
            message,
            understanding,
            previous_phase
        )

    if mode_chat and previous_phase in {"setup", "story"}:

        conversation = store.set_phase(
            payload.conversation_id,
            "chat"
        ) or conversation

        if previous_phase == "setup":

            notes.append(
                "ROUTING NOTE\n"
                "The user is leaving the story setup to have a normal "
                "conversation. Do not ask setup questions, do not present the "
                "brief, and do not start a story. Confirm the switch in one "
                "short sentence and respond to what they said."
            )

        else:

            notes.append(
                "ROUTING NOTE\n"
                "The user is leaving the story to have a normal conversation. "
                "Do not narrate or continue the scene. Confirm the switch in "
                "one short sentence and respond to what they said."
            )

    if action is not None:

        if action.get("name") == "generate_image":

            notes.append(
                "ROUTING NOTE\n"
                "The app is painting the current scene as an image right now. "
                "Reply with one short sentence confirming that, such as "
                "\"The app is painting the scene.\" Do not describe the "
                "image, its colors, objects, or details. Do not write new "
                "prose and do not repeat the previous paragraph."
            )

        elif action.get("name") == "new_chat":

            notes.append(
                "ROUTING NOTE\n"
                "A new empty chat is being created for the user. Confirm in "
                "one short sentence. Do not ask a question and do not write "
                "a scene."
            )

        else:

            notes.append(
                "ROUTING NOTE\n"
                f"The app is opening {action.get('label')} for the user right "
                "now. Confirm in one short sentence and ask what they want to "
                "do next. Do not describe the panel's contents and do not "
                "write a scene."
            )

    elif (
        message
        and edit_id is None
        and conversation.get("phase") == "chat"
    ):

        notes.append(
            "ROUTING NOTE\n"
            "No image is being painted for this turn. Do not say an image, "
            "picture, drawing, or illustration was generated, created, "
            "painted, or completed now, and do not offer to make one. Do "
            "not ask the user what image they want and do not explain image "
            "options. Just react to their message as ordinary chat."
        )

    if (
        message
        and edit_id is None
        and conversation.get("phase") == "setup"
        and intents & {"question", "chat", "ooc"}
    ):

        notes.append(
            "ROUTING NOTE\n"
            "The user asked you a question, not a foundation answer. Answer "
            "their question directly in the first sentence, in one to three "
            "sentences, before asking anything. Do not reply with questions "
            "only and do not treat the message as story preferences, even if "
            "it mentions story topics. This overrides the setup interview "
            "rules for this turn. Then ask one or two focused setup "
            "questions."
        )

    route_note = "\n\n".join(notes) if notes else None

    if (
        conversation.get("phase") == "chat"
        and message
        and edit_id is None
        and action is None
        and not mode_chat
    ):

        stories = _story_conversations()
        matched = _match_story(message, stories)
        decision, _ = router.decide(message, understanding)

        if decision == "continue":

            target = None

            if len(stories) == 1:

                target = stories[0]

            elif matched is not None:

                target = matched

            if target is not None:

                conversation = (
                    _adopt_story(payload.conversation_id, target)
                    or conversation
                )

                route_note = (
                    "ROUTING NOTE\n"
                    f"You are continuing the saved story "
                    f"\"{target.get('title')}\". Its foundation and story "
                    "memory are loaded. Resume the narrative from the latest "
                    "established moment."
                )

            elif not stories:

                route_note = (
                    "ROUTING NOTE\n"
                    "The user asked to continue a story, but no saved story "
                    "exists. Say that briefly and offer to start a new one. "
                    "Do not invent story context."
                )

            else:

                titles = "\n".join(
                    f"- {item.get('title') or 'Untitled'}"
                    for item in stories[:10]
                )

                route_note = (
                    "ROUTING NOTE\n"
                    "The user asked to continue a story, but several saved "
                    "stories exist. Ask which one they mean using this list, "
                    "and do not write narrative until they choose:\n"
                    f"{titles}"
                )

        elif decision == "story":

            conversation = store.set_phase(
                payload.conversation_id,
                "setup"
            ) or conversation

            conversation = store.set_setup_start(
                payload.conversation_id,
                store.last_message_id(payload.conversation_id)
            ) or conversation

            activated_setup = True

        elif (
            matched is not None
            and "?" not in message
            and len(message.split()) <= 6
        ):

            conversation = (
                _adopt_story(payload.conversation_id, matched)
                or conversation
            )

            route_note = (
                "ROUTING NOTE\n"
                f"The user named the saved story "
                f"\"{matched.get('title')}\". Its foundation and story "
                "memory are loaded. Resume the narrative."
            )

    if (
        conversation.get("phase") == "setup"
        and message
        and not activated_setup
    ):

        setup_start = conversation.get("setup_start_id") or 0

        history = [
            item for item in store.get_messages(
                payload.conversation_id
            )
            if (item.get("id") or 0) > setup_start
        ]

        last_assistant = ""

        for item in history:

            if item.get("role") == "assistant":

                last_assistant = item.get("content") or ""

        brief_presented = any(
            has_story_brief(item.get("content") or "")
            for item in history
            if item.get("role") == "assistant"
        )

        confident = (
            understanding is not None
            and understanding.confidence >= 0.45
        )

        confirmed = confident and (
            "begin_story" in intents
            or (
                "affirmation" in intents
                and brief_presented
                and "?" in last_assistant
            )
        )

        if confirmed and last_assistant:

            conversation = store.set_phase(
                payload.conversation_id,
                "story"
            ) or conversation

    if edit_id is not None:

        conversation = store.get_conversation(
            payload.conversation_id
        ) or conversation

        prompt = engine.regenerate(
            conversation,
            edit_id,
            image_urls=attachments.image_data_urls(rows),
            intents=intents
        )

        meta_message = saved

    else:

        prompt_content = attachments.prompt_text(rows)

        conversation, prompt, saved = engine.prepare(
            conversation,
            message,
            prompt_content=prompt_content,
            attachment_ids=[row["id"] for row in rows],
            image_urls=attachments.image_data_urls(rows),
            intents=intents,
            route_note=route_note
        )

        if not message and rows:

            store.auto_title(
                conversation["id"],
                rows[0]["filename"]
            )

            conversation = store.get_conversation(
                conversation["id"]
            )

        meta_message = saved

    def generate():

        yield _event(
            "meta",
            {
                "conversation": conversation,
                "message": meta_message,
                "action": action
            }
        )

        failed = False

        try:

            for chunk in engine.stream(
                conversation,
                prompt
            ):

                yield _event(
                    "delta",
                    {"text": chunk}
                )

        except ModelError as error:

            failed = True

            yield _event(
                "error",
                {"message": str(error)}
            )

            yield _event(
                "done",
                {
                    "conversation": store.get_conversation(
                        conversation["id"]
                    )
                }
            )

            return

        except Exception as error:

            failed = True

            yield _event(
                "error",
                {"message": f"Generation failed: {error}"}
            )

            yield _event(
                "done",
                {
                    "conversation": store.get_conversation(
                        conversation["id"]
                    )
                }
            )

            return

        finally:

            if not failed:

                memory.schedule(conversation["id"])

        yield _event(
            "done",
            {
                "conversation": store.get_conversation(
                    conversation["id"]
                ),
                "message": _last_assistant(conversation["id"])
            }
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
