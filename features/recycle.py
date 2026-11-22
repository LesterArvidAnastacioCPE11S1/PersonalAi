import datetime
import json
import os
import shutil
import subprocess

from pathlib import Path

from features.tools.policy import ToolError


CREATE_NO_WINDOW = 0x08000000
TIMEOUT = 60

LIST_SCRIPT = (
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
    "$shell = New-Object -ComObject Shell.Application; "
    "$items = @($shell.NameSpace(10).Items()); "
    "$out = foreach ($i in $items) { "
    "$from = ''; $when = ''; $size = 0; "
    "try { $from = [string]$i.ExtendedProperty('System.Recycle.DeletedFrom') } catch {}; "
    "try { "
    "$d = $i.ExtendedProperty('System.Recycle.DateDeleted'); "
    "if ($d -is [datetime]) { $when = $d.ToUniversalTime().ToString('o') } "
    "else { $when = [string]$d } "
    "} catch {}; "
    "try { $size = [int64]$i.ExtendedProperty('System.Size') } catch {}; "
    "[pscustomobject]@{ name = [string]$i.Name; path = [string]$i.Path; "
    "original = $from; deleted_at = $when; size = $size; "
    "folder = [bool]$i.IsFolder } "
    "}; "
    "ConvertTo-Json -InputObject @($out) -Compress -Depth 3"
)

RESTORE_SCRIPT = (
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
    "$shell = New-Object -ComObject Shell.Application; "
    "$key = $env:PAI_RECYCLE_KEY; "
    "$item = @($shell.NameSpace(10).Items()) | "
    "Where-Object { $_.Path -eq $key } | Select-Object -First 1; "
    "if (-not $item) { exit 3 }; "
    "$verbs = @($item.Verbs()); "
    "$verb = @($verbs | Where-Object { $_.Name -match 'estore|ndelete' })[0]; "
    "if (-not $verb) { $verb = $verbs[0] }; "
    "if (-not $verb) { exit 4 }; "
    "$verb.DoIt(); "
    "Start-Sleep -Milliseconds 800"
)


def _powershell(script, extra_env=None):

    env = os.environ.copy()

    if extra_env:

        env.update(extra_env)

    try:

        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            creationflags=CREATE_NO_WINDOW,
            env=env
        )

    except subprocess.TimeoutExpired as error:

        raise ToolError("The Recycle Bin took too long to respond.") from error

    except OSError as error:

        raise ToolError(f"Could not reach the Recycle Bin: {error}") from error

    if completed.returncode != 0:

        detail = (completed.stderr or "").strip()

        raise ToolError(
            "The Recycle Bin operation failed."
            + (f" {detail[:300]}" if detail else "")
        )

    return completed.stdout.strip().lstrip("\ufeff")


def _stamp(value):

    text = str(value or "").strip()

    if not text:

        return ""

    try:

        return (
            datetime.datetime.fromisoformat(
                text.replace("Z", "+00:00")
            ).astimezone(
                datetime.timezone.utc
            ).isoformat(timespec="seconds")
        )

    except ValueError:

        return text


def _path(key):

    text = str(key or "").strip()

    if not text:

        raise ToolError("Missing Recycle Bin item.")

    path = Path(text)

    if ".." in path.parts:

        raise ToolError("That is not a Recycle Bin item.")

    path = path.resolve()
    parts = [part.lower() for part in path.parts]

    if "$recycle.bin" not in parts or not path.name.lower().startswith("$r"):

        raise ToolError("That is not a Recycle Bin item.")

    return path


def list_items():

    raw = _powershell(LIST_SCRIPT)

    if not raw:

        return []

    try:

        data = json.loads(raw)

    except ValueError as error:

        raise ToolError("Could not read the Recycle Bin.") from error

    if isinstance(data, dict):

        data = [data]

    if not isinstance(data, list):

        return []

    entries = []

    for item in data:

        if not isinstance(item, dict):

            continue

        path = str(item.get("path") or "")

        parts = [part.lower() for part in Path(path).parts]

        if "$recycle.bin" not in parts:

            continue

        name = str(item.get("name") or Path(path).name)
        original = str(item.get("original") or "")

        if original:

            original = str(Path(original) / name)

        entries.append(
            {
                "name": name,
                "key": path,
                "original": original,
                "deleted_at": _stamp(item.get("deleted_at")),
                "size": int(item.get("size") or 0),
                "folder": bool(item.get("folder"))
            }
        )

    entries.sort(
        key=lambda entry: entry["deleted_at"],
        reverse=True
    )

    return entries


def restore(key):

    path = _path(key)
    _powershell(
        RESTORE_SCRIPT,
        extra_env={"PAI_RECYCLE_KEY": str(path)}
    )

    return str(path)


def purge(key):

    path = _path(key)

    if not path.exists():

        raise ToolError("That item is no longer in the Recycle Bin.")

    size = _size(path)

    def retry(function, target, _):

        try:

            os.chmod(target, 0o666)

        except OSError:

            pass

        function(target)

    if path.is_dir():

        shutil.rmtree(path, onerror=retry)

    else:

        os.remove(path)

    sibling = path.parent / f"$I{path.name[2:]}"

    if sibling.is_file():

        try:

            sibling.unlink()

        except OSError:

            pass

    return size


def _size(path):

    if path.is_file():

        try:

            return path.stat().st_size

        except OSError:

            return 0

    total = 0

    for item in path.rglob("*"):

        try:

            if item.is_file():

                total += item.stat().st_size

        except OSError:

            continue

    return total
