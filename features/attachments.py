import base64
import hashlib
import io
import mimetypes
import os
import re
import shutil
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from features.image_ocr import ImageOCRError, extract_text as extract_image_text
from features.roblox_files import extract_text as extract_roblox_text

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False

try:
    from docx import Document
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

MAX_FILE_BYTES = 200 * 1024 * 1024
MAX_IMAGE_BYTES = 100 * 1024 * 1024
MAX_ROBLOX_BYTES = 500 * 1024 * 1024
MAX_STORED_CHARS = 2_000_000
MAX_PROMPT_CHARS = 500_000
MAX_IMAGE_OCR_CHARS = 20_000
MAX_NAME_CHARS = 160

SUPPORTED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".json", ".log",
    ".yaml", ".yml", ".html", ".htm", ".xml", ".py",
    ".js", ".ts", ".css", ".ini", ".toml", ".cfg",
    ".lua", ".luau",
    ".cpp", ".h", ".hpp", ".c", ".cs", ".java", ".kt",
    ".rs", ".go", ".rb", ".php", ".swift", ".sh", ".bat",
    ".ps1", ".sql", ".tf", ".dockerfile", ".gitignore",
    ".env", ".example", ".sample", ".wat", ".wast",
}

SUPPORTED_ROBLOX_EXTENSIONS = {
    ".rbxm", ".rbxl", ".rbxlx", ".rbxmx",
}

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp",
}

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_DOCX_EXTENSIONS = {".docx"}

ALL_SUPPORTED = (
    SUPPORTED_TEXT_EXTENSIONS
    | SUPPORTED_ROBLOX_EXTENSIONS
    | SUPPORTED_IMAGE_EXTENSIONS
    | SUPPORTED_PDF_EXTENSIONS
    | SUPPORTED_DOCX_EXTENSIONS
)


class AttachmentError(Exception):
    pass


class AttachmentNotFound(AttachmentError):
    pass


class AttachmentService:

    def __init__(self, config, store):

        self.config = config
        self.store = store
        self.root = Path(getattr(config.app, "db_path", "data/personal_ai.db")).parent / "attachments"
        self.root.mkdir(parents=True, exist_ok=True)

    def _ext(self, filename: str) -> str:
        name = Path(filename).name.lower()
        if name in {".env", ".gitignore"}:
            return name
        if name == "dockerfile":
            return ".dockerfile"
        return Path(name).suffix

    def _kind(self, ext: str) -> str:
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            return "image"
        if ext in SUPPORTED_PDF_EXTENSIONS:
            return "pdf"
        if ext in SUPPORTED_DOCX_EXTENSIONS:
            return "docx"
        if ext in SUPPORTED_ROBLOX_EXTENSIONS:
            return "roblox"
        if ext in SUPPORTED_TEXT_EXTENSIONS:
            return "text"
        return "file"

    def _max_bytes(self, ext: str) -> int:
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            return MAX_IMAGE_BYTES
        if ext in SUPPORTED_ROBLOX_EXTENSIONS | {".luau", ".lua"}:
            return MAX_ROBLOX_BYTES
        return MAX_FILE_BYTES

    def _is_supported(self, ext: str) -> bool:
        return ext in ALL_SUPPORTED

    def _extract_text(self, ext: str, data: bytes, filename: str):
        warning = None

        if ext in SUPPORTED_ROBLOX_EXTENSIONS:
            try:
                text = extract_roblox_text(data, filename)
                return text, None
            except Exception as error:
                return "", f"Could not read Roblox file: {error}"
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            try:
                text = extract_image_text(data)
            except ImageOCRError as error:
                return "", str(error)
            return text[:MAX_IMAGE_OCR_CHARS], None
        if ext == ".pdf":
            return self._extract_pdf(data)
        if ext == ".docx":
            return self._extract_docx(data)
        if ext in SUPPORTED_TEXT_EXTENSIONS:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
                warning = "File contained non-UTF-8 bytes; some characters may be replaced."
            return text[:MAX_STORED_CHARS], warning

        return "", warning

    def _extract_pdf(self, data: bytes):
        if not HAS_PYPDF:
            return "", "pypdf not installed; PDF text could not be extracted."
        try:
            reader = PdfReader(__import__("io").BytesIO(data))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            text = "\n".join(parts).strip()
            if not text:
                return "", "No selectable text was found in this PDF. Scanned pages need OCR."
            return text[:MAX_STORED_CHARS], None
        except Exception as error:
            return "", f"Could not read PDF: {error}"

    def _extract_docx(self, data: bytes):
        if not HAS_DOCX:
            return "", "python-docx not installed; DOCX text could not be extracted."
        try:
            doc = Document(__import__("io").BytesIO(data))
            parts = [p.text for p in doc.paragraphs if p.text]
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):
                        parts.append("\t".join(cells))
            text = "\n".join(parts).strip()
            if not text:
                return "", "No text was found in this DOCX."
            return text[:MAX_STORED_CHARS], None
        except Exception as error:
            return "", f"Could not read DOCX: {error}"

    def _extraction_path(self, row):
        return Path(row["path"] + ".parsed.txt")

    def _roblox_index(self, attachment_id, filename, text):
        first_line, _, remainder = text.partition("\n")
        counts_line, _, _ = remainder.partition("\n")
        script_paths = re.findall(
            r"(?m)^--- (.+?) "
            r"\((?:Script|LocalScript|ModuleScript)\) ---$",
            text
        )
        summary = (
            f"[Roblox attachment {attachment_id}: {filename}]\n"
            f"{first_line}\n{counts_line}\n"
            f"Full parsed content: {text.count(chr(10)) + 1} lines, "
            f"{len(text)} characters. Use attachments_search/read with "
            f"attachment_id={attachment_id} to inspect complete scripts "
            "and hierarchy. Binary assets are omitted.\n"
        )
        if script_paths:
            summary += (
                f"Scripts ({len(script_paths)}):\n"
                + "\n".join(f"- {path}" for path in script_paths)
            )
        return summary

    def save(self, conversation_id: str, filename: str, data: bytes):

        if not filename:
            raise AttachmentError("No filename provided.")

        if len(data) == 0:
            raise AttachmentError("File is empty.")

        ext = self._ext(filename)

        if not self._is_supported(ext):
            raise AttachmentError(
                f"File type '{ext}' is not supported."
            )

        max_bytes = self._max_bytes(ext)
        if len(data) > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise AttachmentError(
                f"File is larger than {mb} MB."
            )

        kind = self._kind(ext)

        attachment_id = uuid.uuid4().hex
        relative = f"{conversation_id}/{attachment_id}{ext}"
        dest = self.root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            f.write(data)

        text, warning = self._extract_text(ext, data, filename)

        if kind == "roblox" and text:
            extracted_path = Path(str(dest) + ".parsed.txt")
            try:
                extracted_path.write_text(text, encoding="utf-8")
            except OSError as error:
                raise AttachmentError(
                    f"Could not save parsed Roblox content: {error}"
                ) from error
            text = self._roblox_index(attachment_id, filename, text)

        row = self.store.add_attachment(
            attachment_id=attachment_id,
            conversation_id=conversation_id,
            filename=filename[:MAX_NAME_CHARS],
            mime=(
                IMAGE_MIME_TYPES.get(ext)
                or mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            ),
            kind=kind,
            size=len(data),
            path=str(dest),
            text=text,
        )

        if kind == "roblox" and extracted_path.exists():
            row["extracted_path"] = str(extracted_path)

        return row, warning

    def public(self, row) -> dict:
        text = row["text"] or ""
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "message_id": row["message_id"],
            "filename": row["filename"],
            "mime": row["mime"],
            "kind": row["kind"],
            "size": row["size"],
            "url": f"/api/attachments/{row['id']}/file",
            "text_chars": len(text),
            "text_preview": text[:200],
            "vision_needed": row["kind"] == "image",
            "warning": row.get("warning"),
            "created_at": row["created_at"],
        }

    def ready(self, conversation_id: str, attachment_ids: list):

        if not attachment_ids:
            return []

        rows = []
        seen = set()

        for attachment_id in attachment_ids:
            if attachment_id in seen:
                continue
            seen.add(attachment_id)

            row = self.store.get_attachment(attachment_id)
            if row is None:
                raise AttachmentNotFound(f"Attachment {attachment_id} not found.")

            if row["conversation_id"] != conversation_id:
                raise AttachmentNotFound(
                    f"Attachment {attachment_id} is not in this conversation."
                )

            if row["kind"] == "roblox":
                row = self._ensure_roblox_extraction(row)

            rows.append(row)

        return rows

    def _ensure_roblox_extraction(self, row):
        extracted_path = self._extraction_path(row)

        if not extracted_path.is_file() and row["text"]:
            try:
                data = self.file_path(row).read_bytes()
                text = extract_roblox_text(data, row["filename"])
                extracted_path.write_text(text, encoding="utf-8")
                summary = self._roblox_index(row["id"], row["filename"], text)
                row = self.store.update_attachment_text(row["id"], summary)
            except AttachmentError:
                raise
            except Exception as error:
                raise AttachmentError(
                    f"Could not index Roblox attachment "
                    f"'{row['filename']}': {error}"
                ) from error

        if extracted_path.is_file():
            row["extracted_path"] = str(extracted_path)

        return row

    def prompt_text(self, rows: list) -> str:

        if not rows:
            return ""

        parts = []
        budget = MAX_PROMPT_CHARS
        used = 0

        for row in rows:
            if row["kind"] == "image":
                marker = (
                    f"[Attached image: {row['filename']} "
                    "(analyzed separately)]"
                )
                text = (row.get("text") or "")[:MAX_IMAGE_OCR_CHARS]
                available = budget - used - len(marker)
                header = "\nLocal OCR text (may contain recognition errors):\n"
                if text and available > len(header):
                    text = text[:max(0, available - len(header))]
                    parts.append(marker + header + text)
                    used += len(marker) + len(header) + len(text)
                else:
                    parts.append(marker)
                    used += len(marker)
                continue

            if row["kind"] == "roblox":
                summary = row["text"] or ""
                remaining = budget - used
                if remaining <= 0:
                    parts.append(
                        "\n[Roblox index omitted due to prompt budget; "
                        "use attachment_search/read.]\n"
                    )
                    break
                if len(summary) > remaining:
                    summary = (
                        summary[:remaining]
                        + "\n[Roblox index truncated; use attachment tools.]"
                    )
                parts.append(summary)
                used += len(summary)
                continue

            if not row["text"]:
                parts.append(f"[Attached file: {row['filename']} (no readable text)]")
                continue

            header = (
                f"\n--- {row['filename']} (attachment_id={row['id']}, "
                f"{len(row['text'])} chars) ---\n"
            )
            available = budget - used

            if available <= 0:
                parts.append(f"\n[Omitted: attachment text budget reached.]\n")
                break

            text = row["text"]
            if len(text) > available:
                text = text[:available] + "\n[...truncated...]"

            parts.append(header + text)
            used += len(header) + len(text)

        if not parts:
            return ""

        return (
            "[Attached files]\n"
            + "".join(parts)
            + "\n[End of attached files]"
        )

    def image_ocr_text(self, rows: list) -> str:
        parts = []
        remaining = MAX_IMAGE_OCR_CHARS
        for row in rows:
            text = row.get("text") or ""
            if row.get("kind") != "image" or not text:
                continue
            if remaining <= 0:
                parts.append("[Additional image OCR omitted due to context limit.]")
                break
            snippet = text[:remaining]
            parts.append(
                f"Local OCR from {row['filename']} "
                "(may contain recognition errors):\n"
                f"{snippet}"
            )
            remaining -= len(snippet)
            if len(snippet) < len(text):
                parts.append("[Image OCR context truncated.]")
                break
        return "\n\n".join(parts)

    def image_data_urls(self, rows: list) -> list:

        data_urls = []
        for row in rows:
            if row["kind"] != "image":
                continue

            path = self.file_path(row)
            data = path.read_bytes()
            mime = (
                IMAGE_MIME_TYPES.get(path.suffix.lower())
                or row["mime"]
                or "application/octet-stream"
            )

            if path.suffix.lower() in {".bmp", ".gif"}:
                try:
                    with Image.open(io.BytesIO(data)) as image:
                        image.seek(0)
                        image = ImageOps.exif_transpose(image)
                        mode = "RGBA" if "A" in image.getbands() else "RGB"
                        image = image.convert(mode)
                        output = io.BytesIO()
                        image.save(output, format="PNG")
                        data = output.getvalue()
                except Exception as error:
                    raise AttachmentError(
                        f"Could not prepare image '{row['filename']}': {error}"
                    ) from error

                mime = "image/png"

            if not mime.startswith("image/"):
                raise AttachmentError(
                    f"Unsupported image format for '{row['filename']}'."
                )

            encoded = base64.b64encode(data).decode("ascii")
            data_urls.append(f"data:{mime};base64,{encoded}")

        return data_urls

    def file_path(self, row):

        path = Path(row["path"])
        if not path.exists():
            raise AttachmentNotFound(f"Attachment file not found: {path}")
        return path

    def delete_unlinked(self, attachment_id: str):

        row = self.store.get_attachment(attachment_id)
        if row is None:
            raise AttachmentNotFound(f"Attachment {attachment_id} not found.")

        if row["message_id"] is not None:
            raise AttachmentError(
                "Cannot delete an attachment that is linked to a message."
            )

        self.store.delete_attachment(attachment_id)

        try:
            path = Path(row["path"])
            if path.exists():
                path.unlink()
            extracted_path = self._extraction_path(row)
            if extracted_path.exists():
                extracted_path.unlink()
        except OSError:
            pass

    def remove_files(self, rows: list):

        for row in rows:
            try:
                path = Path(row["path"])
                if path.exists():
                    path.unlink()
                extracted_path = self._extraction_path(row)
                if extracted_path.exists():
                    extracted_path.unlink()
            except OSError:
                pass
