"""
Keeps the Luau documentation corpus current.

Roblox ships new API classes, properties, and functions almost every
week. The local YAML corpus under data/docs/luau/roblox is a snapshot
of Roblox's official documentation. This module merges Roblox's
reflection API dump (maintained daily by the Roblox-Client-Tracker
project) into that corpus:

- Classes that are missing get a generated page with the full member
  list and signatures (without prose descriptions).
- Existing class pages get members that the documentation has not
  covered yet.
- Missing enum pages are generated.

Existing content is never modified or deleted, so prose descriptions
written by Roblox stay untouched. After a merge the search index is
rebuilt automatically.

The updater runs in a background thread on server startup and rechecks
at most once per day (or whenever the Roblox version changes).
"""

import json
import threading
import time

from pathlib import Path

import requests
import yaml


import features.luau_docs as luau_docs


DUMP_URL = (
    "https://raw.githubusercontent.com/MaximumADHD/"
    "Roblox-Client-Tracker/roblox/Full-API-Dump.json"
)

VERSION_URL = (
    "https://clientsettings.roblox.com/v2/client-version/"
    "WindowsStudio64"
)

STATE_PATH = luau_docs.LUAU_ROOT / "api-dump-state.json"
DUMP_CACHE = luau_docs.LUAU_ROOT / "api-dump.json"

CHECK_INTERVAL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 180

# Classes and enums the dump knows about but Roblox deliberately
# hides from documentation are not useful as reference material.

HIDDEN_TAGS = {"NotBrowsable", "Hidden"}

SECTION_FOR_MEMBER_TYPE = {
    "Property": "properties",
    "Function": "methods",
    "Event": "events",
    "Callback": "callbacks"
}


class UpdateError(Exception):
    pass


def _fetch_json(url, timeout=REQUEST_TIMEOUT):

    response = requests.get(url, timeout=timeout)

    response.raise_for_status()

    return response.json()


def _load_state():

    try:

        return json.loads(
            STATE_PATH.read_text(encoding="utf-8")
        )

    except (OSError, json.JSONDecodeError):

        return {}


def _save_state(state):

    try:

        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(state, indent=1),
            encoding="utf-8"
        )

    except OSError:

        pass


def _type_text(type_info):

    if not isinstance(type_info, dict):

        return "unknown"

    name = str(type_info.get("Name") or "")
    category = str(type_info.get("Category") or "")

    if category == "Enum":
        return f"Enum.{name}" if name else "Enum"

    return name or category or "unknown"


def _note(version):

    return (
        "(Member present in the Roblox API dump "
        f"{version} but not yet covered by the documentation.)"
    )


def _member_from_dump(member, version):

    member_type = member.get("MemberType")
    note = _note(version)

    entry = {
        "name": str(member.get("Name") or ""),
        "summary": note,
        "description": note,
        "code_samples": [],
        "tags": [
            str(tag)
            for tag in member.get("Tags") or []
        ],
        "deprecation_message": str(
            member.get("Deprecation") or ""
        ),
        "security": {
            "read": str(
                (member.get("Security") or {}).get("Read", "None")
            )
            if isinstance(member.get("Security"), dict)
            else str(member.get("Security") or "None"),
            "write": str(
                (member.get("Security") or {}).get("Write", "None")
            )
            if isinstance(member.get("Security"), dict)
            else "None"
        },
        "thread_safety": str(
            member.get("ThreadSafety") or "ReadSafe"
        )
    }

    if member_type == "Property":

        value_type = member.get("ValueType") or member.get("Type")

        entry["type"] = _type_text(value_type)
        entry["category"] = str(member.get("Category") or "")
        entry["serialization"] = {
            "can_load": bool(
                (member.get("Serialization") or {}).get("CanLoad")
            ),
            "can_save": bool(
                (member.get("Serialization") or {}).get("CanSave")
            )
        }

        default = member.get("Default")

        if default not in (None, ""):
            entry["default"] = default

    else:

        parameters = []

        for item in member.get("Parameters") or []:

            parameter = {
                "name": str(item.get("Name") or ""),
                "type": _type_text(item.get("Type"))
            }

            if item.get("Default") not in (None, ""):
                parameter["default"] = str(item.get("Default"))

            parameters.append(parameter)

        entry["parameters"] = parameters

        if member_type in ("Function", "Callback"):

            entry["returns"] = [
                {"type": _type_text(member.get("ReturnType"))}
            ]

    return entry


def _is_hidden(tags):

    return bool(
        HIDDEN_TAGS.intersection(
            str(tag) for tag in tags or []
        )
    )


def _class_yaml(cls, version):

    name = str(cls.get("Name") or "")

    summary = (
        f"API reference for {name}, generated automatically from "
        f"the Roblox API dump {version}. Prose documentation is "
        "not available for this class yet."
    )

    data = {
        "name": name,
        "type": "class",
        "memory_category": str(
            cls.get("MemoryCategory") or "Instances"
        ),
        "summary": summary,
        "description": summary,
        "code_samples": [],
        "inherits": [
            str(cls.get("Superclass"))
        ]
        if cls.get("Superclass")
        else [],
        "descendants": [],
        "tags": [
            str(tag)
            for tag in cls.get("Tags") or []
        ],
        "deprecation_message": "",
        "properties": [],
        "methods": [],
        "events": [],
        "callbacks": []
    }

    for member in cls.get("Members") or []:

        section = SECTION_FOR_MEMBER_TYPE.get(
            member.get("MemberType")
        )

        if section is None:
            continue

        data[section].append(_member_from_dump(member, version))

    return data


def _enum_yaml(enum, version):

    name = str(enum.get("Name") or "")

    summary = (
        f"Reference for Enum.{name}, generated automatically from "
        f"the Roblox API dump {version}."
    )

    items = []

    for item in enum.get("Items") or []:

        items.append(
            {
                "name": str(item.get("Name") or ""),
                "summary": "",
                "value": item.get("Value"),
                "tags": [
                    str(tag)
                    for tag in item.get("Tags") or []
                ]
            }
        )

    return {
        "name": name,
        "type": "enum",
        "summary": summary,
        "description": summary,
        "code_samples": [],
        "tags": [
            str(tag)
            for tag in enum.get("Tags") or []
        ],
        "deprecation_message": "",
        "items": items
    }


def _merge_class(cls, version):

    name = str(cls.get("Name") or "")

    if not name:
        return (False, 0)

    path = luau_docs.ROBLOX_ROOT / "classes" / f"{name}.yaml"
    created = False
    added = 0

    existing = None

    if path.is_file():

        try:

            existing = yaml.safe_load(
                path.read_text(encoding="utf-8")
            )

        except Exception:

            existing = None

        if not isinstance(existing, dict):
            existing = None

    if existing is None:

        if _is_hidden(cls.get("Tags")):

            return (False, 0)

        existing = _class_yaml(cls, version)
        created = True

    for member_type, section in SECTION_FOR_MEMBER_TYPE.items():

        current = existing.get(section)

        if not isinstance(current, list):
            current = []

        known = {
            str(item.get("name"))
            for item in current
            if isinstance(item, dict) and item.get("name")
        }

        for member in cls.get("Members") or []:

            if member.get("MemberType") != member_type:
                continue

            member_name = str(member.get("Name") or "")

            if not member_name or member_name in known:
                continue

            current.append(_member_from_dump(member, version))
            known.add(member_name)
            added += 1

        existing[section] = current

    if not created and added == 0:
        return (False, 0)

    try:

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                existing,
                sort_keys=False,
                allow_unicode=True
            ),
            encoding="utf-8"
        )

    except OSError as error:

        print(f"[luau-docs] could not write {path.name}: {error}")

        return (False, 0)

    return (created, added)


def _merge_enum(enum, version):

    name = str(enum.get("Name") or "")

    if not name:
        return False

    path = luau_docs.ROBLOX_ROOT / "enums" / f"{name}.yaml"

    if path.is_file():
        return False

    if _is_hidden(enum.get("Tags")):
        return False

    try:

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                _enum_yaml(enum, version),
                sort_keys=False,
                allow_unicode=True
            ),
            encoding="utf-8"
        )

    except OSError as error:

        print(f"[luau-docs] could not write {path.name}: {error}")

        return False

    return True


def _merge_dump(dump, version):

    created_classes = 0
    updated_classes = 0
    added_members = 0
    created_enums = 0

    for cls in dump.get("Classes") or []:

        created, added = _merge_class(cls, version)

        if created:
            created_classes += 1

        elif added:
            updated_classes += 1

        added_members += added

    for enum in dump.get("Enums") or []:

        if _merge_enum(enum, version):
            created_enums += 1

    return {
        "dump_version": version,
        "created_classes": created_classes,
        "updated_classes": updated_classes,
        "added_members": added_members,
        "created_enums": created_enums
    }


def _invalidate_index():

    try:

        luau_docs.CACHE_PATH.unlink(missing_ok=True)

    except OSError:

        pass

    luau_docs._STATE.ready = False


def update(force=False):

    """
    Check for a newer Roblox version and merge the API dump if
    anything changed. Returns a stats dict, or None when nothing
    was done.
    """

    state = _load_state()

    version = None

    try:

        version = str(
            _fetch_json(VERSION_URL, timeout=30).get("version") or ""
        )

    except Exception:

        if not force:
            return None

        version = "unknown"

    now = time.time()
    checked = state.get("checked") or 0

    if (
        not force
        and state.get("version") == version
        and now - checked < CHECK_INTERVAL_SECONDS
    ):

        return None

    try:

        dump = _fetch_json(DUMP_URL)

    except Exception as error:

        print(f"[luau-docs] API dump download failed: {error}")

        if DUMP_CACHE.is_file() and force:

            try:

                dump = json.loads(
                    DUMP_CACHE.read_text(encoding="utf-8")
                )

                print("[luau-docs] using the cached API dump.")

            except (OSError, json.JSONDecodeError):

                return None

        else:

            return None

    try:

        DUMP_CACHE.write_text(
            json.dumps(dump),
            encoding="utf-8"
        )

    except OSError:

        pass

    stats = _merge_dump(dump, version)

    _save_state(
        {
            "version": version,
            "checked": now,
            "stats": stats
        }
    )

    _invalidate_index()

    error = luau_docs.warm()

    if error:
        print(f"[luau-docs] index rebuild failed: {error}")

    print(
        f"[luau-docs] merged Roblox API dump {version}: "
        f"{stats['created_classes']} new classes, "
        f"{stats['updated_classes']} classes updated, "
        f"{stats['added_members']} members added, "
        f"{stats['created_enums']} new enums."
    )

    return stats


def _run():

    try:

        update()

    except Exception as error:

        print(f"[luau-docs] update failed: {error}")


def start_updater():

    thread = threading.Thread(
        target=_run,
        daemon=True
    )

    thread.start()

    return thread
