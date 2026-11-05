import json

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
from core.engine import ChatEngine
from core.memory import MemoryBusy, MemoryWriter
from core.store import Store
from features.attachments import (
    MAX_FILE_BYTES,
    AttachmentError,
    AttachmentNotFound,
    AttachmentService
)
from features.intents import asks_to_begin, detect
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
from features.story_setup import has_story_brief
from models.openai_compat import ModelError, OpenAICompatibleModel


config = load_config()

if config.app.mobile_access and not config.app.access_token:

    config.app.access_token = generate_token()
    save_config(config)

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

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title="PersonalAI")

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


class ConversationUpdate(BaseModel):
    title: str | None = None
    premise: str | None = None
    setting: str | None = None
    characters: str | None = None
    style: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = ""
    attachments: list[str] = []


class PhaseUpdate(BaseModel):
    phase: str


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


@app.get("/")
def index():

    return FileResponse(WEB_DIR / "index.html")


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
        "base_url": config.model.base_url,
        "available": available
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

    return {
        "conversation": store.create_conversation(
            title=payload.title,
            premise=payload.premise,
            setting=payload.setting,
            characters=payload.characters,
            style=payload.style
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

    conversation = store.update_conversation(
        conversation_id,
        payload.model_dump(exclude_unset=True)
    )

    return {
        "conversation": conversation
    }


@app.post("/api/conversations/{conversation_id}/phase")
def update_phase(conversation_id: str, payload: PhaseUpdate):

    phase = payload.phase.strip().lower()

    if phase not in {"setup", "story"}:

        raise HTTPException(
            status_code=400,
            detail="Phase must be setup or story."
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

    intents = detect(message)

    if conversation.get("phase") == "setup" and message:

        history = store.get_messages(
            payload.conversation_id
        )

        last_assistant = ""

        for item in history:

            if item.get("role") == "assistant":

                last_assistant = item.get("content") or ""

        brief_presented = any(
            has_story_brief(item.get("content") or "")
            for item in history
            if item.get("role") == "assistant"
        )

        confirmed = (
            "begin_story" in intents
            or (
                "affirmation" in intents
                and asks_to_begin(last_assistant)
                and brief_presented
            )
        )

        if confirmed and last_assistant:

            conversation = store.set_phase(
                payload.conversation_id,
                "story"
            ) or conversation

    prompt_content = attachments.prompt_text(rows)

    conversation, prompt = engine.prepare(
        conversation,
        message,
        prompt_content=prompt_content,
        attachment_ids=[row["id"] for row in rows],
        image_urls=attachments.image_data_urls(rows),
        intents=intents
    )

    if not message and rows:

        store.auto_title(
            conversation["id"],
            rows[0]["filename"]
        )

        conversation = store.get_conversation(
            conversation["id"]
        )

    def generate():

        yield _event(
            "meta",
            {"conversation": conversation}
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
                )
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
