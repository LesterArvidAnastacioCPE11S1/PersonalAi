import hashlib
import json
import re
import threading

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LUAU_ROOT = ROOT / "data" / "docs" / "luau"
LANG_ROOT = LUAU_ROOT / "lang"
ROBLOX_ROOT = LUAU_ROOT / "roblox"
GUIDE_PATH = LUAU_ROOT / "roblox-guide.md"
CACHE_PATH = LUAU_ROOT / "index-v3.json"
CACHE_VERSION = 3

WORD_RE = re.compile(r"[A-Za-z0-9_]+")
CAMEL_RE = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
FRONT_RE = re.compile(r"\Atitle:\s*(.+)$", re.MULTILINE)
LINK_PREFIX_RE = re.compile(r"\b(?:Class|Datatype|Enum|Library)\.")
LINK_TARGET_RE = re.compile(r"\|[A-Za-z0-9_]+")
PHRASE_RE = re.compile(r"[.:|]+")

STOPWORDS = {
    "a", "all", "an", "and", "any", "are", "as", "at", "be", "but",
    "by", "can", "could", "do", "does", "for", "from", "get", "give",
    "how", "i", "if", "in", "into", "is", "it", "its", "just", "like",
    "luau", "make", "me", "my", "need", "of", "on", "or", "please",
    "roblox", "should", "so", "some", "tell", "that", "the", "their",
    "then", "there", "these", "this", "to", "up", "use", "using", "want",
    "was", "way", "we", "what", "whats", "when", "where", "which", "why",
    "will", "with", "would", "you", "your"
}

MEMBER_KEYS = (
    "constructors", "methods", "functions", "callbacks", "events",
    "properties", "constants"
)

KIND_LABEL = {
    "class": "ROBLOX CLASS",
    "datatype": "ROBLOX DATATYPE",
    "library": "ROBLOX LIBRARY",
    "enum": "ROBLOX ENUM",
    "global": "ROBLOX GLOBAL",
    "doc": "LUAU DOC"
}

MAX_TOTAL = 4200


class _State:

    def __init__(self):

        self.lock = threading.Lock()
        self.ready = False
        self.error = ""
        self.records = []
        self.by_name = {}


_STATE = _State()


def _stem(word):

    if len(word) > 4 and word.endswith("ies"):

        return word[:-3] + "y"

    if len(word) > 5 and word.endswith("ing"):

        return word[:-3]

    if len(word) > 4 and word.endswith("ed"):

        return word[:-2]

    if (
        len(word) > 3
        and word.endswith("s")
        and not word.endswith(("ss", "us", "is"))
    ):

        return word[:-1]

    return word


def tokens(text):

    found = []
    used = set()

    def add(value):

        if len(value) >= 2 and value not in used:

            used.add(value)
            found.append(value)

    for raw in WORD_RE.findall(text or ""):

        parts = CAMEL_RE.split(raw)

        for part in parts:

            part = part.strip("_").lower()

            if len(part) >= 2:

                add(part)
                add(_stem(part))

        whole = raw.strip("_").lower()

        if len(whole) >= 2:

            add(whole)
            add(_stem(whole))

    return found


def _query(text):

    found = {}
    order = []

    def add(value, weight):

        if len(value) < 2 or value in STOPWORDS:

            return

        if value not in found:

            found[value] = weight
            order.append(value)

        elif weight > found[value]:

            found[value] = weight

    for raw in WORD_RE.findall(text or ""):

        parts = CAMEL_RE.split(raw)
        whole = raw.strip("_").lower()

        if len(parts) > 1:

            for part in parts:

                part = part.strip("_").lower()

                add(part, 0.2)
                add(_stem(part), 0.2)

            add(whole, 1.0)
            add(_stem(whole), 1.0)

        else:

            add(whole, 1.0)
            add(_stem(whole), 1.0)

    return [(item, found[item]) for item in order]


def _trim(text, limit):

    clean = " ".join((text or "").split())

    if len(clean) <= limit:

        return clean

    return clean[: limit - 4].rstrip() + " ..."


def _clean(text):

    return LINK_TARGET_RE.sub("", LINK_PREFIX_RE.sub("", text or ""))


def _phrase(text):

    return PHRASE_RE.sub(" ", (text or "").lower())


def _sources():

    paths = []

    for name in ("classes", "datatypes", "libraries", "enums", "globals"):

        base = ROBLOX_ROOT / name

        if base.is_dir():

            paths.extend(base.glob("*.yaml"))

    if LANG_ROOT.is_dir():

        paths.extend(LANG_ROOT.glob("*.md"))

    if GUIDE_PATH.is_file():

        paths.append(GUIDE_PATH)

    return paths


def _stamp(paths):

    items = []

    for path in sorted(paths, key=str):

        try:

            stat = path.stat()

        except OSError:

            continue

        items.append([str(path), stat.st_mtime_ns, stat.st_size])

    payload = json.dumps(items, separators=(",", ":"))

    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def warm():

    with _STATE.lock:

        if _STATE.ready:

            return _STATE.error

        paths = _sources()

        if not paths:

            _STATE.error = f"no documentation under {LUAU_ROOT}"
            _STATE.ready = True

            return _STATE.error

        stamp = _stamp(paths)
        packed = _read_cache(stamp)

        if packed is None:

            try:

                packed = _pack(_build_records())
                _write_cache(stamp, packed)

            except Exception as error:

                _STATE.error = f"{type(error).__name__}: {error}"
                _STATE.records = []
                _STATE.ready = True

                return _STATE.error

        try:

            _STATE.records = _unpack(packed)
            _STATE.by_name = {
                record["name"]: record
                for record in _STATE.records
                if record["kind"] in {"class", "datatype"}
            }
            _STATE.error = ""

        except Exception as error:

            _STATE.error = f"{type(error).__name__}: {error}"
            _STATE.records = []

        _STATE.ready = True

    return _STATE.error


def _read_cache(stamp):

    if not CACHE_PATH.is_file():

        return None

    try:

        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    except (OSError, json.JSONDecodeError):

        return None

    if (
        payload.get("version") != CACHE_VERSION
        or payload.get("stamp") != stamp
    ):

        return None

    records = payload.get("records")

    return records if isinstance(records, list) else None


def _write_cache(stamp, packed):

    try:

        payload = {
            "version": CACHE_VERSION,
            "stamp": stamp,
            "records": packed
        }
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8"
        )

    except OSError:

        pass


def _pack(records):

    packed = []

    for record in records:

        packed.append(
            {
                "kind": record["kind"],
                "name": record["name"],
                "sub": record.get("sub") or "",
                "description": record.get("description") or "",
                "text": record.get("text") or "",
                "inherits": record.get("inherits") or [],
                "members": record.get("members") or [],
                "title_tokens": sorted(record["title_tokens"]),
                "body_tokens": sorted(record["body_tokens"]),
                "member_tokens": sorted(record.get("member_tokens") or []),
                "phrase": record["phrase"]
            }
        )

    return packed


def _unpack(packed):

    records = []

    for item in packed:

        records.append(
            {
                "kind": item["kind"],
                "name": item["name"],
                "sub": item.get("sub") or "",
                "description": item.get("description") or "",
                "text": item.get("text") or "",
                "inherits": item.get("inherits") or [],
                "members": item.get("members") or [],
                "title_tokens": set(item.get("title_tokens") or []),
                "body_tokens": set(item.get("body_tokens") or []),
                "member_tokens": set(item.get("member_tokens") or []),
                "phrase": item.get("phrase") or ""
            }
        )

    return records


def _build_records():

    import yaml

    def load(path):

        try:

            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        except Exception:

            return {}

    records = []

    for path in sorted((ROBLOX_ROOT / "classes").glob("*.yaml")):

        data = load(path)

        if data.get("name"):

            records.append(_api_record("class", data))

    for path in sorted((ROBLOX_ROOT / "datatypes").glob("*.yaml")):

        data = load(path)

        if data.get("name"):

            records.append(_api_record("datatype", data))

    for path in sorted((ROBLOX_ROOT / "libraries").glob("*.yaml")):

        data = load(path)

        if data.get("name"):

            records.append(_api_record("library", data))

    enums = ROBLOX_ROOT / "enums"

    if enums.is_dir():

        for path in sorted(enums.glob("*.yaml")):

            data = load(path)

            if data.get("name"):

                records.append(_enum_record(data))

    for path in sorted((ROBLOX_ROOT / "globals").glob("*.yaml")):

        data = load(path)

        for entry in data.get("properties") or []:

            if isinstance(entry, dict) and entry.get("name"):

                records.append(_global_record(entry))

    if LANG_ROOT.is_dir():

        for path in sorted(LANG_ROOT.glob("*.md")):

            try:

                text = path.read_text(encoding="utf-8")

            except OSError:

                continue

            records.extend(_doc_records(text))

    if GUIDE_PATH.is_file():

        try:

            text = GUIDE_PATH.read_text(encoding="utf-8")

        except OSError:

            text = ""

        if text:

            records.extend(_doc_records(text))

    return records


def _slim(member):

    if not isinstance(member, dict):

        return None

    name = member.get("name")

    if not name:

        return None

    parameters = []

    for item in member.get("parameters") or []:

        if not isinstance(item, dict) or not item.get("name"):

            continue

        parameters.append(
            {
                "name": str(item.get("name")),
                "type": str(item.get("type") or ""),
                "default": item.get("default")
            }
        )

    returns = []

    for item in member.get("returns") or []:

        if isinstance(item, dict) and item.get("type"):

            returns.append({"type": str(item.get("type"))})

    slim = {
        "name": str(name),
        "type": str(member.get("type") or ""),
        "summary": _trim(_clean(member.get("summary") or ""), 300),
        "deprecation_message": _trim(
            member.get("deprecation_message") or "", 160
        ),
        "tags": [str(tag) for tag in member.get("tags") or []],
        "parameters": parameters,
        "returns": returns
    }

    if member.get("value") not in (None, ""):

        slim["value"] = member.get("value")

    return slim


def _api_record(kind, data):

    name = str(data.get("name") or "")
    summary = _trim(_clean(data.get("summary") or ""), 500)
    description = _trim(_clean(data.get("description") or ""), 1600)
    pieces = [name, summary, description]
    members = []
    member_tokens = set()

    for key in MEMBER_KEYS:

        for member in data.get(key) or []:

            slim = _slim(member)

            if slim is None:

                continue

            members.append([key, slim])
            short = slim["name"].split(":")[-1].split(".")[-1]
            member_tokens.update(tokens(short))
            member_tokens.update(tokens(slim["name"]))
            pieces.append(short + " " + slim["summary"])

    inherits = data.get("inherits") or []

    if isinstance(inherits, str):

        inherits = [inherits]

    inherits = [str(item) for item in inherits if item]

    sub = ""

    if kind == "class":

        tags = data.get("tags") or []
        notes = []

        if "Service" in tags:

            notes.append("Service")

        if inherits:

            notes.append("inherits " + ", ".join(inherits))

        sub = "; ".join(notes)

    body = " ".join(pieces)[:7000]

    return {
        "kind": kind,
        "name": name,
        "sub": sub,
        "description": description,
        "text": "",
        "inherits": inherits,
        "members": members,
        "title_tokens": set(tokens(name)),
        "body_tokens": set(tokens(body)),
        "member_tokens": member_tokens,
        "phrase": _phrase(name + " " + body)
    }


def _enum_record(data):

    short = str(data.get("name") or "")
    name = "Enum." + short
    summary = _trim(_clean(data.get("summary") or ""), 500)
    description = _trim(_clean(data.get("description") or ""), 900)
    pieces = [name, summary, description]
    members = []
    member_tokens = set()

    for item in data.get("items") or []:

        if not isinstance(item, dict) or not item.get("name"):

            continue

        slim = {
            "name": f"Enum.{short}.{item.get('name')}",
            "type": "",
            "summary": _trim(_clean(item.get("summary") or ""), 160),
            "tags": [str(tag) for tag in item.get("tags") or []],
            "parameters": [],
            "returns": []
        }

        if item.get("value") not in (None, ""):

            slim["value"] = item.get("value")

        if item.get("deprecation_message"):

            slim["deprecation_message"] = _trim(
                item.get("deprecation_message"), 120
            )

        members.append(["constants", slim])
        member_tokens.update(tokens(str(item.get("name"))))
        pieces.append(str(item.get("name")) + " " + slim["summary"])

    body = " ".join(pieces)[:7000]

    return {
        "kind": "enum",
        "name": name,
        "sub": summary,
        "description": description,
        "text": "",
        "inherits": [],
        "members": members,
        "title_tokens": set(tokens(name)),
        "body_tokens": set(tokens(body)),
        "member_tokens": member_tokens,
        "phrase": _phrase(name + " " + body)
    }


def _global_record(entry):

    name = str(entry.get("name") or "")
    summary = _trim(_clean(entry.get("summary") or ""), 500)
    description = _trim(_clean(entry.get("description") or ""), 900)
    body = " ".join([name, summary, description])

    return {
        "kind": "global",
        "name": name,
        "sub": "",
        "description": description,
        "text": "",
        "inherits": [],
        "members": [["properties", {"name": name, "summary": summary}]],
        "title_tokens": set(tokens(name)),
        "body_tokens": set(tokens(body)),
        "member_tokens": set(tokens(name)),
        "phrase": _phrase(body)
    }


def _doc_records(text):

    title = ""
    content = text

    if text.startswith("---"):

        end = text.find("\n---", 3)

        if end >= 0:

            found = FRONT_RE.search(text[:end])
            title = found.group(1).strip().strip('"') if found else ""
            content = text[end + 4:]

    chunks = []
    heading = title or "Luau"
    stack = []
    lines = []

    def flush():

        body = "\n".join(lines).strip()

        if len(body) >= 80:

            chunks.append(
                {
                    "heading": " > ".join([heading] + stack),
                    "body": body
                }
            )

    for line in content.splitlines():

        if line.startswith("## "):

            flush()
            lines = []
            stack = [line[3:].strip()]

            continue

        if line.startswith("# "):

            flush()
            lines = []
            heading = line[2:].strip()
            stack = []

            continue

        lines.append(line)

    flush()

    if not chunks and content.strip():

        chunks.append({"heading": heading, "body": content.strip()})

    records = []

    for chunk in chunks:

        body = chunk["body"][:9000]
        searchable = chunk["heading"] + " " + body

        records.append(
            {
                "kind": "doc",
                "name": chunk["heading"],
                "sub": "",
                "description": "",
                "text": body,
                "inherits": [],
                "members": [],
                "title_tokens": set(tokens(chunk["heading"])),
                "body_tokens": set(tokens(body)),
                "member_tokens": set(),
                "phrase": searchable.lower()
            }
        )

    return records


def _score(record, query, raw):

    score = 0.0
    titles = record["title_tokens"]
    bodies = record["body_tokens"]
    member_tokens = record.get("member_tokens") or set()
    name = record["name"].lower()

    title_hits = 0

    for item, weight in query:

        if item in titles:

            title_hits += 1
            score += 6.0 * weight

        elif len(item) >= 4 and any(
            token.startswith(item)
            for token in titles
            if len(token) >= 4
        ):

            score += 3.0 * weight

        if item in bodies:

            score += 1.0 * weight

        if item in member_tokens:

            score += 4.0 * weight

    score += 0.5 * title_hits
    lowered = raw.strip().lower()

    if len(lowered) >= 3:

        if lowered in name:

            score += 10.0

        elif re.search(
            r"(?<![a-z0-9])" + re.escape(_phrase(lowered)) + r"(?![a-z0-9])",
            record["phrase"]
        ):

            score += 6.0

    if record["kind"] in {"class", "datatype", "enum"}:

        score *= 1.1

    elif record["kind"] == "doc":

        score *= 0.95

    return score


def _param(entry):

    text = str(entry.get("name") or "arg")

    if entry.get("type"):

        text += f": {entry.get('type')}"

    default = entry.get("default")

    if default not in (None, "", "None"):

        text += f" = {default}"

    return text


def _signature(key, member):

    name = str(member.get("name") or "")
    tags = member.get("tags") or []

    if key == "constants" and not member.get("parameters"):

        text = name

        if member.get("value") not in (None, ""):

            text += f" = {member.get('value')}"

    elif key == "properties" and not member.get("parameters"):

        kind = str(member.get("type") or "Variant").strip()
        text = f"{name}: {kind}"

    else:

        args = ", ".join(_param(item) for item in member.get("parameters") or [])
        text = f"{name}({args})"
        returns = member.get("returns") or []

        if returns:

            kinds = [
                str(item.get("type") or "").strip()
                for item in returns
                if isinstance(item, dict)
            ]
            kinds = [item for item in kinds if item]

            if kinds:

                text += " -> " + ", ".join(kinds)

        if key == "events":

            text += "  [event]"

        if key == "callbacks":

            text += "  [callback]"

        if key == "constants" and member.get("value") not in (None, ""):

            text += f" = {member.get('value')}"

    if "Deprecated" in tags:

        text += "  [deprecated]"

    return text


def _member_score(member, query):

    raw = str(member.get("name") or "")
    short = raw.split(":")[-1].split(".")[-1]
    names = set(tokens(short))
    score = 0.0

    for item, weight in query:

        if item in names:

            score += 3.0 * weight

        elif len(item) >= 4 and any(item in token for token in names):

            score += 2.0 * weight

        elif len(item) >= 4 and any(
            token.startswith(item)
            for token in names
            if len(token) >= 3
        ):

            score += 1.0 * weight

    return score


def _candidates(record, query, limit=4):

    own = []

    for key, member in record.get("members") or []:

        own.append((_member_score(member, query), key, member, ""))

    if record["kind"] == "class":

        for ancestor in record.get("inherits") or []:

            source = _STATE.by_name.get(ancestor)

            if source is None:

                continue

            for key, member in source.get("members") or []:

                score = _member_score(member, query)

                if score > 0:

                    own.append((score, key, member, ancestor))

    own.sort(key=lambda item: (-item[0], item[2].get("name") or ""))

    chosen = [item for item in own if item[0] > 0][:limit]

    if not chosen and record["kind"] == "enum":

        chosen = [
            (0.0, key, member, "")
            for key, member in record.get("members") or []
            if member.get("summary")
        ][:6]

    if not chosen:

        preferred = {"methods": 0, "functions": 0, "constructors": 1}
        rest = [
            item for item in own
            if item[1] in preferred and item[2].get("summary") and not item[3]
        ]
        rest.sort(key=lambda item: (preferred[item[1]], item[2].get("name") or ""))
        chosen = rest[:3]

    return chosen


def _enum_allowed(record, raw):

    if "enum" in tokens(raw):

        return True

    short = record["name"].split(".")[-1].lower()

    return short in raw.lower().replace(" ", "")


def _render(record, query):

    label = KIND_LABEL.get(record["kind"], "LUAU DOC")
    name = record["name"]
    sub = record.get("sub") or ""
    header = f"{label} {name}"

    if sub and record["kind"] == "class":

        header += f" ({sub})"

    lines = [header]

    if record["kind"] == "doc":

        text = (record.get("text") or "").strip()

        if text:

            lines.append(text[:1500])

        return "\n".join(lines)

    if record["kind"] == "global":

        description = record.get("description") or ""

        if description:

            lines.append(description)

        return "\n".join(lines)

    if sub:

        lines.append(sub)

    chosen = _candidates(record, query)

    for _, key, member, source in chosen:

        prefix = f"(inherited from {source}) " if source else ""
        lines.append("- " + prefix + _signature(key, member))
        summary = member.get("summary") or ""

        if summary:

            lines.append("  " + summary)

        message = member.get("deprecation_message") or ""

        if message:

            lines.append("  Deprecated: " + message)

    description = record.get("description") or ""

    if description and record["kind"] in {"class", "datatype", "enum"}:

        lines.append(_trim(description, 500))

    return "\n".join(lines)


def search(query, limit=4):

    text = (query or "").strip()

    if not text:

        return "No search query."

    error = warm()

    if error:

        return f"Luau docs unavailable: {error}"

    wanted = _query(text)

    if not wanted:

        wanted = [(item.lower(), 1.0) for item in WORD_RE.findall(text)]

    try:

        limit = max(1, min(int(limit), 6))

    except (TypeError, ValueError):

        limit = 4

    scored = []

    for record in _STATE.records:

        score = _score(record, wanted, text)

        if score >= 3.0:

            scored.append((score, record))

    if not scored:

        return (
            "No matching Luau or Roblox documentation found for: "
            + _trim(text, 120)
        )

    scored.sort(key=lambda item: (-item[0], len(item[1]["name"])))

    parts = []
    seen = set()
    total = 0

    for _, record in scored:

        if record["kind"] == "enum" and not _enum_allowed(record, text):

            continue

        key = (record["kind"], record["name"])

        if key in seen:

            continue

        seen.add(key)
        block = _render(record, wanted)

        if not block:

            continue

        if total + len(block) > MAX_TOTAL and parts:

            break

        parts.append(block[:MAX_TOTAL])
        total += len(block)

        if len(parts) >= limit:

            break

    return "\n\n".join(parts)
