import ctypes
import ctypes.wintypes
import datetime
import fnmatch
import os
import platform
import re
import shutil
import subprocess
import time

from pathlib import Path

from features.tools.policy import PathPolicy, ToolError
from features.project_agents import review_project
from features.projects import ProjectError
from features.luau_docs import search as search_luau_docs
from features.tools.registry import TOOL_MAP


ROOT = Path(__file__).resolve().parent.parent.parent


PRUNE_DIRS = {
    ".git",
    ".idea",
    ".vs",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "site-packages",
    "node_modules",
    "ollama-models",
    "comfyui",
    "recovery"
}

GPU_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e968-e325-11ce-bfc1-08002be10318}"
)


class MEMORYSTATUSEX(ctypes.Structure):

    _fields_ = [
        ("dwLength", ctypes.wintypes.DWORD),
        ("dwMemoryLoad", ctypes.wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)
    ]


def _human_size(value):

    size = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):

        if size < 1024 or unit == "TB":

            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} TB"


def _memory():

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    ):

        return None

    return status


def _gpu_names():

    names = []

    try:

        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, GPU_KEY) as key:

            index = 0

            while True:

                try:

                    child = winreg.EnumKey(key, index)

                except OSError:

                    break

                index += 1

                if not child.isdigit():

                    continue

                try:

                    with winreg.OpenKey(key, child) as sub:

                        name = winreg.QueryValueEx(sub, "DriverDesc")[0]

                except OSError:

                    continue

                if name and name not in names:

                    names.append(name)

    except OSError:

        return names

    return names


def _disks():

    lines = []
    mask = ctypes.windll.kernel32.GetLogicalDrives()

    for index in range(26):

        if not mask & (1 << index):

            continue

        letter = chr(ord("A") + index)

        if letter == "A":

            continue

        try:

            usage = shutil.disk_usage(f"{letter}:\\")

        except OSError:

            continue

        lines.append(
            f"{letter}: total {_human_size(usage.total)}, "
            f"free {_human_size(usage.free)}"
        )

    return lines


def system_time(args, config, policy):

    zone_name = str(args.get("timezone") or "").strip()

    if zone_name:

        try:

            from zoneinfo import ZoneInfo

            zone = ZoneInfo(zone_name)

        except Exception as error:

            raise ToolError(
                f"Unknown timezone: {zone_name}. Use an IANA name such as "
                "Asia/Tokyo or America/New_York."
            ) from error

        now = datetime.datetime.now(zone)

    else:

        now = datetime.datetime.now().astimezone()
        zone_name = now.tzname() or "local"

    offset = now.strftime("%z")
    formatted_offset = (
        f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
    )

    return (
        f"Date: {now.strftime('%Y-%m-%d')}\n"
        f"Time: {now.strftime('%H:%M:%S')}\n"
        f"Weekday: {now.strftime('%A')}\n"
        f"Timezone: {zone_name} (UTC{formatted_offset})\n"
        f"UTC: {now.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Unix timestamp: {int(now.timestamp())}"
    )


def system_info(args, config, policy):

    memory = _memory()
    lines = [
        f"Operating system: {platform.system()} {platform.release()}",
        f"Version: {platform.version()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor() or 'unknown'}",
        f"CPU cores (logical): {os.cpu_count() or 'unknown'}"
    ]

    if memory is not None:

        lines.append(
            f"RAM: {_human_size(memory.ullTotalPhys)} total, "
            f"{_human_size(memory.ullAvailPhys)} available"
        )

    gpus = _gpu_names()

    lines.append(
        "GPU: " + (", ".join(gpus) if gpus else "unknown")
    )

    disks = _disks()

    if disks:

        lines.append("Disks:")

        lines.extend(f"  {item}" for item in disks)

    return "\n".join(lines)


def files_list(args, config, policy):

    folder = policy.resolve(args.get("path") or "", must_exist=True)

    if not folder.is_dir():

        raise ToolError(f"Not a folder: {folder}")

    entries = []

    with os.scandir(folder) as handle:

        for entry in handle:

            try:

                stat = entry.stat()

            except OSError:

                continue

            entries.append(
                (
                    entry.is_dir(),
                    entry.name,
                    stat.st_size,
                    stat.st_mtime
                )
            )

    entries.sort(key=lambda item: (not item[0], item[1].lower()))

    total = len(entries)
    shown = entries[: config.max_entries]
    lines = [f"Folder: {folder}", f"Items: {total}"]

    for is_dir, name, size, modified in shown:

        stamp = datetime.datetime.fromtimestamp(
            modified
        ).strftime("%Y-%m-%d %H:%M")

        if is_dir:

            lines.append(f"DIR  {name}/")

        else:

            lines.append(f"FILE {name}  {_human_size(size)}  {stamp}")

    if total > len(shown):

        lines.append(
            f"[{total - len(shown)} more items not shown]"
        )

    return "\n".join(lines)


def _name_matches(name, query):

    lowered = name.lower()
    wanted = query.lower()

    if any(char in wanted for char in "*?["):

        return fnmatch.fnmatch(lowered, wanted)

    return wanted in lowered


def files_search(args, config, policy):

    query = str(args.get("query") or "").strip()

    if not query:

        raise ToolError("A search query is required.")

    mode = str(args.get("mode") or "name").strip().lower()

    if mode not in {"name", "content"}:

        raise ToolError("mode must be 'name' or 'content'.")

    folder = policy.resolve(args.get("path") or "", must_exist=True)

    if not folder.is_dir():

        raise ToolError(f"Not a folder: {folder}")

    recursive = args.get("recursive", True)

    if recursive:

        walker = os.walk(folder)

    else:

        walker = [
            (
                str(folder),
                [],
                [
                    item.name for item in os.scandir(folder)
                    if item.is_file()
                ]
            )
        ]

    hits = []
    scanned = 0
    stopped = False

    for current, dirs, names in walker:

        dirs[:] = [
            item for item in dirs
            if item.lower() not in PRUNE_DIRS
        ]

        for name in names:

            if len(hits) >= config.max_search_hits:

                stopped = True
                break

            if scanned >= config.max_search_files:

                stopped = True
                break

            path = Path(current) / name

            try:

                policy.check_sensitive(path)

            except ToolError:

                continue

            scanned += 1

            if mode == "name":

                if _name_matches(name, query):

                    hits.append(f"{path}")

                continue

            try:

                size = path.stat().st_size

            except OSError:

                continue

            if size > config.max_file_bytes:

                continue

            try:

                raw = path.read_bytes()

            except OSError:

                continue

            if b"\x00" in raw[:4096]:

                continue

            try:

                text = raw.decode("utf-8", errors="ignore")

            except Exception:

                continue

            lowered = text.lower()
            wanted = query.lower()

            if wanted not in lowered:

                continue

            position = lowered.find(wanted)
            line_number = text.count("\n", 0, position) + 1
            line_start = text.rfind("\n", 0, position) + 1
            line_end = text.find("\n", position)

            if line_end == -1:

                line_end = len(text)

            snippet = " ".join(
                text[line_start:line_end].strip().split()
            )[:180]

            hits.append(f"{path}:{line_number}: {snippet}")

        if stopped:

            break

    header = (
        f"Search: {query!r} in {folder} (mode: {mode}"
        f"{'' if recursive else ', top level only'})\n"
        f"Files scanned: {scanned}\n"
        f"Matches: {len(hits)}"
    )

    if not hits:

        return header + "\nNo matches found."

    body = "\n".join(hits)

    if stopped:

        body += "\n[search stopped at the configured limit]"

    return header + "\n" + body


def files_read(args, config, policy):

    path = policy.resolve(args.get("path") or "", must_exist=True)
    policy.check_sensitive(path)

    if not path.is_file():

        raise ToolError(f"Not a file: {path}")

    size = path.stat().st_size

    if size > config.max_file_bytes:

        raise ToolError(
            f"File is {_human_size(size)}; the limit is "
            f"{_human_size(config.max_file_bytes)}. Read a smaller part."
        )

    raw = path.read_bytes()

    if b"\x00" in raw[:4096]:

        raise ToolError("This looks like a binary file, not text.")

    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    try:

        start = max(1, int(args.get("start_line") or 1))

    except (TypeError, ValueError):

        start = 1

    try:

        count = max(1, int(args.get("max_lines") or 400))

    except (TypeError, ValueError):

        count = 400

    if not lines:

        return f"File: {path} (empty)"

    if start > len(lines):

        return (
            f"File: {path} has {len(lines)} lines; "
            f"start_line {start} is past the end."
        )

    end = min(len(lines), start - 1 + count)
    body = "\n".join(
        f"{number:5d}| {lines[number - 1]}"
        for number in range(start, end + 1)
    )
    header = f"File: {path} (lines {start}-{end} of {len(lines)})"

    if end < len(lines):

        body += f"\n[lines {end + 1}-{len(lines)} not shown]"

    return f"{header}\n{body}"


def _attachment_rows(rows, attachment_id=None):

    if not rows:

        raise ToolError("There are no attachments in the current request.")

    if attachment_id:

        matches = [
            row for row in rows
            if str(row.get("id")) == attachment_id
        ]

        if not matches:

            raise ToolError(
                "That attachment is not part of the current request."
            )

        return matches

    return rows


def _attachment_lines(row):

    extracted_path = row.get("extracted_path")

    if extracted_path:

        path = Path(extracted_path)

        if not path.is_file():

            raise ToolError(
                f"Extracted attachment content is missing: {path}"
            )

        try:

            with path.open("r", encoding="utf-8", errors="replace") as stream:

                for number, line in enumerate(stream, 1):

                    yield number, line.rstrip("\r\n")

        except OSError as error:

            raise ToolError(
                f"Could not read extracted attachment content: {error}"
            ) from error

        return

    for number, line in enumerate(
        (row.get("text") or "").splitlines(),
        1
    ):

        yield number, line


def _attachments_read(args, rows):

    row = _attachment_rows(rows, args.get("attachment_id"))[0]
    start = max(1, args.get("start_line") or 1)
    count = min(200, max(1, args.get("max_lines") or 100))
    selected = []

    for number, line in _attachment_lines(row):

        if number < start:

            continue

        selected.append((number, line))

        if len(selected) >= count:

            break

    if not selected:

        raise ToolError(
            f"Start line {start} is past the end of the attachment."
        )

    end = selected[-1][0]

    return (
        f"Attachment: {row.get('filename') or 'file'} "
        f"(id {row.get('id')})\n"
        f"Lines {start}-{end}:\n"
        + "\n".join(
            f"{number}| {line[:6000]}"
            for number, line in selected
        )
    )


def _attachments_search(args, rows):

    matches = _attachment_rows(rows, args.get("attachment_id"))
    query = args["query"].strip().casefold()

    if not query:

        raise ToolError("Search query cannot be empty.")

    limit = min(50, max(1, args.get("max_results") or 10))
    results = []

    for row in matches:

        for number, line in _attachment_lines(row):

            index = line.casefold().find(query)

            if index < 0:

                continue

            start = max(0, index - 120)
            end = min(len(line), index + len(query) + 240)
            snippet = line[start:end]

            if start:

                snippet = "..." + snippet

            if end < len(line):

                snippet += "..."

            results.append(
                f"{number}| {row.get('filename') or 'file'} "
                f"(id {row.get('id')}): {snippet}"
            )

            if len(results) >= limit:

                break

        if len(results) >= limit:

            break

    if not results:

        names = ", ".join(
            row.get("filename") or "file"
            for row in matches
        )

        return f"No matches for {args['query']!r} in: {names}"

    return (
        f"Found {len(results)} match(es) for {args['query']!r}:\n"
        + "\n".join(results)
    )


def _active_project(args, project):

    if not project:

        raise ToolError(
            "Select a persistent Roblox project before using project tools."
        )

    requested_id = args.get("project_id")

    if requested_id and str(requested_id) != project["id"]:

        raise ToolError(
            "That project is not active in the current request."
        )

    return project


def _project_search(args, project, project_service):

    project = _active_project(args, project)

    try:

        results = project_service.search(
            project["id"],
            args.get("query"),
            args.get("max_results") or 10
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    if not results:

        return f"No matches for {args.get('query')!r} in {project['name']}."

    lines = [
        f"Found {len(results)} match(es) in project "
        f"{project['name']} ({project['id']}):"
    ]

    for result in results:

        location = (
            f"{result['path']} — parsed line {result['line']}"
            if result["path"]
            else f"parsed line {result['line']}"
        )
        lines.append(f"{location}: {result['text']}")

    return "\n".join(lines)

def _project_find_scripts(args, project, project_service):

    project = _active_project(args, project)

    try:

        result = project_service.find_scripts(
            project["id"],
            args.get("query"),
            args.get("max_results") or 100,
            args.get("offset") or 0
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    scripts = result["scripts"]
    lines = [
        f"Scanned all {result['project_script_count']} indexed scripts in "
        f"{project['name']}. Found {result['total']} candidate script(s); "
        f"starting at offset {result['offset']}.",
        "Search terms: " + ", ".join(result["expanded_terms"])
    ]
    displayed = 0

    for script in scripts:

        candidate = [
            f"- {script['path']} "
            f"(script_id={script['script_id']}; {script['class_name']}; "
            f"{script['source_match_count']} source line(s))"
        ]

        if script["evidence"]:

            evidence = script["evidence"][0]
            candidate.append(
                f"  source line {evidence['line']}: "
                f"{evidence['text'][:100]}"
            )

        else:

            candidate.append("  path/name match only; role unconfirmed")

        if (
            displayed
            and len("\n".join(lines))
            + len("\n".join(candidate))
            + 1
            > 4500
        ):

            break

        lines.extend(candidate)
        displayed += 1

    next_offset = result["offset"] + displayed

    if next_offset < result["total"]:

        lines.append(
            f"More results remain; use offset={next_offset} to continue."
        )

    return "\n".join(lines)

def _project_script_read(args, project, project_service):

    project = _active_project(args, project)

    try:

        result = project_service.read_script(
            project["id"],
            args.get("script_id"),
            args.get("start_line") or 1,
            args.get("max_lines") or 100
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    body = "\n".join(
        f"{number}| {line}"
        for number, line in result["lines"]
    )

    return (
        f"Source lines {result['start_line']}-{result['end_line']} of "
        f"{result['total_lines']} for {result['path']} "
        f"({result['class_name']}; script_id={result['script_id']}):\n"
        f"{body}"
    )


def _project_read(args, project, project_service):

    project = _active_project(args, project)

    try:

        lines = project_service.read(
            project["id"],
            args.get("start_line") or 1,
            args.get("max_lines") or 100
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    start = lines[0][0]
    end = lines[-1][0]
    body = "\n".join(
        f"{number}| {line}"
        for number, line in lines
    )

    return (
        f"Project: {project['name']} ({project['id']})\n"
        f"Parsed lines {start}-{end}:\n{body}"
    )


def _project_tree(args, project, project_service):

    project = _active_project(args, project)

    try:

        nodes = project_service.tree(
            project["id"],
            args.get("parent_id"),
            min(200, args.get("limit") or 100),
            args.get("offset") or 0
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    if not nodes:

        return "No hierarchy entries in that range."

    lines = [
        f"Hierarchy for {project['name']} "
        f"({len(nodes)} node(s), starting at offset "
        f"{args.get('offset') or 0}):"
    ]

    for node in nodes:

        suffix = (
            f" [{node['child_count']} children]"
            if node["child_count"]
            else ""
        )
        if node["is_script"]:

            suffix += " [script]"
        lines.append(
            f"- {node['name']} ({node['class_name']}) "
            f"[node_id={node['node_id']}]{suffix}"
        )

    return "\n".join(lines)


def _project_node_read(args, project, project_service):

    project = _active_project(args, project)

    try:

        node = project_service.node(
            project["id"],
            args.get("node_id")
        )

    except ProjectError as error:

        raise ToolError(str(error)) from error

    properties = node.get("properties") or []
    lines = [
        f"Instance: {node['path']} ({node['class_name']}; "
        f"node_id={node['node_id']})"
    ]

    if properties:

        lines.append("Properties:")

        for item in properties:

            lines.append(
                f"- {item['name']}: {item['value']}"
            )

    else:

        lines.append("No indexed properties.")

    return "\n".join(lines)


def files_write(args, config, policy):

    path = policy.resolve(args.get("path") or "", must_exist=False)
    policy.check_sensitive(path)

    if ".git" in {part.lower() for part in path.parts}:

        raise ToolError("Writing inside .git is blocked.")

    content = str(args.get("content") or "")
    data = content.encode("utf-8")

    if len(data) > config.max_write_bytes:

        raise ToolError(
            f"Content is {_human_size(len(data))}; the limit is "
            f"{_human_size(config.max_write_bytes)}."
        )

    previous = None

    if path.exists():

        if not path.is_file():

            raise ToolError(f"Not a file: {path}")

        if not args.get("overwrite"):

            raise ToolError(
                f"File already exists: {path}. Set overwrite to true to "
                "replace it."
            )

        previous = path.stat().st_size

    if not path.parent.is_dir():

        raise ToolError(f"Folder does not exist: {path.parent}")

    path.write_text(content, encoding="utf-8")

    action = "Replaced" if previous is not None else "Created"
    detail = (
        f" (previous size {_human_size(previous)})"
        if previous is not None
        else ""
    )

    return f"{action} {path} ({_human_size(len(data))} written{detail})"


def files_move(args, config, policy):

    source = policy.resolve(args.get("source") or "", must_exist=True)
    destination = policy.resolve(
        args.get("destination") or "",
        must_exist=False
    )

    policy.check_sensitive(source)
    policy.check_sensitive(destination)

    for path in (source, destination):

        if ".git" in {part.lower() for part in path.parts}:

            raise ToolError("Moving files inside .git is blocked.")

    if not source.is_file():

        raise ToolError(f"Only files can be moved: {source}")

    if source == destination:

        raise ToolError("Source and destination are the same file.")

    replaced = None

    if destination.exists():

        if destination.is_dir():

            raise ToolError(f"Destination is a folder: {destination}")

        if not args.get("overwrite"):

            raise ToolError(
                f"Destination already exists: {destination}. Set overwrite "
                "to true to replace it."
            )

        replaced = destination.stat().st_size

    if not destination.parent.is_dir():

        raise ToolError(f"Folder does not exist: {destination.parent}")

    if replaced is not None:

        destination.unlink()

    shutil.move(str(source), str(destination))

    detail = (
        f" (replaced {_human_size(replaced)})"
        if replaced is not None
        else ""
    )

    return (
        f"Moved {source} -> {destination}{detail} "
        f"({_human_size(destination.stat().st_size)})"
    )


def _recycle(path):

    class ShFileOpStructW(ctypes.Structure):

        _fields_ = [
            ("hwnd", ctypes.wintypes.HWND),
            ("wFunc", ctypes.wintypes.UINT),
            ("pFrom", ctypes.wintypes.LPCWSTR),
            ("pTo", ctypes.wintypes.LPCWSTR),
            ("fFlags", ctypes.wintypes.USHORT),
            ("fAnyOperationsAborted", ctypes.wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", ctypes.wintypes.LPCWSTR)
        ]

    shell32 = ctypes.windll.shell32
    operation = ShFileOpStructW()
    operation.hwnd = None
    operation.wFunc = 0x0003
    operation.pFrom = f"{path}\0"
    operation.pTo = None
    operation.fFlags = 0x0004 | 0x0040 | 0x0400 | 0x4000
    operation.fAnyOperationsAborted = False
    operation.hNameMappings = None
    operation.lpszProgressTitle = None

    code = shell32.SHFileOperationW(ctypes.byref(operation))

    if operation.fAnyOperationsAborted:

        raise ToolError(f"Deleting {path} was cancelled.")

    if code:

        raise ToolError(
            f"Windows could not move {path} to the Recycle Bin "
            f"(error {code})."
        )

    if path.exists():

        raise ToolError(
            f"Windows reported success but {path} still exists."
        )


def _delete_target(args, policy):

    path = policy.resolve(args.get("path") or "", must_exist=True)
    policy.check_sensitive(path)

    if ".git" in {part.lower() for part in path.parts}:

        raise ToolError("Deleting files inside .git is blocked.")

    if path.parent == path:

        raise ToolError("Drive roots cannot be deleted.")

    root_dir = ROOT.resolve()

    if path == root_dir or path in root_dir.parents:

        raise ToolError("The app folder cannot be deleted.")

    data_dir = root_dir / "data"

    if path == data_dir or path in data_dir.parents:

        raise ToolError("The app data folder cannot be deleted.")

    home = os.environ.get("USERPROFILE")

    if home and path == Path(home).resolve():

        raise ToolError("The home folder cannot be deleted.")

    for root in policy.roots:

        if path == Path(root).resolve():

            raise ToolError(
                "A configured allowed folder cannot be deleted."
            )

    try:

        relative = path.relative_to(root_dir)

    except ValueError:

        relative = None

    if relative is not None:

        parts = [part.lower() for part in relative.parts]

        if len(parts) >= 2 and parts[0] == "data" and parts[1] == "recovery":

            raise ToolError("The app recovery data cannot be deleted.")

        if parts and parts[0] == "data" and parts[-1].startswith(
            "personal_ai.db"
        ):

            raise ToolError("The live app database cannot be deleted.")

    return path


def files_delete(args, config, policy):

    path = _delete_target(args, policy)

    is_folder = path.is_dir()
    size = path.stat().st_size

    if is_folder:

        size = 0

        for item in path.rglob("*"):

            try:

                if item.is_file():

                    size += item.stat().st_size

            except OSError:

                continue

    _recycle(path)

    label = "folder" if is_folder else "file"

    return (
        f"Sent {label} {path} to the Recycle Bin ({_human_size(size)}). "
        "It can be restored from the Recycle Bin."
    )


def luau_docs(args, config, policy):

    query = str(args.get("query") or "").strip()

    if not query:

        raise ToolError("A search query is required.")

    limit = args.get("limit")

    try:

        limit = int(limit) if limit is not None else 4

    except (TypeError, ValueError):

        limit = 4

    return search_luau_docs(query, limit)


def run_command(args, config, policy):

    command = str(args.get("command") or "").strip()

    if not command:

        raise ToolError("Command cannot be empty.")

    cwd = policy.resolve(args.get("cwd") or "", must_exist=True)

    if not cwd.is_dir():

        raise ToolError(f"Not a folder: {cwd}")

    timeout = int(config.command_timeout or 120)

    try:

        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    except subprocess.TimeoutExpired as error:

        raise ToolError(
            f"Command timed out after {timeout} seconds."
        ) from error

    out = completed.stdout.decode("utf-8", errors="replace").strip()
    err = completed.stderr.decode("utf-8", errors="replace").strip()

    parts = [
        f"Working directory (not a prefix for paths in the output): {cwd}",
        f"Exit code: {completed.returncode}"
    ]

    if out:

        parts.append(f"STDOUT:\n{out}")

    if err:

        parts.append(f"STDERR:\n{err}")

    if not out and not err:

        parts.append("(no output)")

    return "\n".join(parts)


HANDLERS = {
    "system_time": system_time,
    "system_info": system_info,
    "files_list": files_list,
    "files_search": files_search,
    "files_read": files_read,
    "files_write": files_write,
    "files_move": files_move,
    "files_delete": files_delete,
    "luau_docs": luau_docs,
    "run_command": run_command
}


def _clean_args(name, args):

    spec = TOOL_MAP.get(name)

    if spec is None:

        raise ToolError(f"Unknown tool: {name}")

    if args is None:

        args = {}

    if not isinstance(args, dict):

        raise ToolError("Arguments must be a JSON object.")

    unknown = set(args) - set(spec["args"])

    if unknown:

        raise ToolError(
            "Unknown argument(s): " + ", ".join(sorted(unknown))
        )

    cleaned = {}

    for key, item in spec["args"].items():

        if key not in args or args[key] is None:

            if item["required"]:

                raise ToolError(f"Missing required argument: {key}")

            continue

        value = args[key]

        if item["type"] == "int":

            if isinstance(value, bool):

                raise ToolError(f"Argument {key} must be a number.")

            try:

                value = int(value)

            except (TypeError, ValueError) as error:

                raise ToolError(f"Argument {key} must be a number.") from error

        elif item["type"] == "bool":

            if isinstance(value, bool):

                pass

            elif isinstance(value, str) and value.strip().lower() in {
                "true",
                "yes",
                "1"
            }:

                value = True

            elif isinstance(value, str) and value.strip().lower() in {
                "false",
                "no",
                "0"
            }:

                value = False

            else:

                raise ToolError(
                    f"Argument {key} must be true or false."
                )

        else:

            if isinstance(value, (dict, list)):

                raise ToolError(f"Argument {key} must be text.")

            value = str(value)

            if item["required"] and not value.strip():

                raise ToolError(f"Argument {key} cannot be empty.")

        cleaned[key] = value

    return cleaned


def preview_args(name, args):

    return _clean_args(name, args)


def preview_check(name, args, policy):

    if name == "run_command":

        if not str(args.get("command") or "").strip():

            raise ToolError("Command cannot be empty.")

        cwd = policy.resolve(args.get("cwd") or "", must_exist=True)

        if not cwd.is_dir():

            raise ToolError(f"Not a folder: {cwd}")

        return

    if name == "files_delete":

        _delete_target(args, policy)

        return

    if name != "files_move":

        return

    source = policy.resolve(args.get("source") or "", must_exist=True)
    destination = policy.resolve(
        args.get("destination") or "",
        must_exist=False
    )

    policy.check_sensitive(source)
    policy.check_sensitive(destination)

    if not source.is_file():

        raise ToolError(f"Only files can be moved: {source}")

    if source == destination:

        raise ToolError("Source and destination are the same file.")

    for path in (source, destination):

        if ".git" in {part.lower() for part in path.parts}:

            raise ToolError("Moving files inside .git is blocked.")

    if destination.exists() and destination.is_dir():

        raise ToolError(f"Destination is a folder: {destination}")

    if destination.exists() and not args.get("overwrite"):

        raise ToolError(
            f"Destination already exists: {destination}. Set overwrite "
            "to true to replace it."
        )

    if not destination.parent.is_dir():

        raise ToolError(f"Folder does not exist: {destination.parent}")


def run_tool(
    name,
    args,
    config,
    policy,
    attachment_rows=None,
    project=None,
    project_service=None,
    model=None,
    visual_context=None,
    request_context="",
    investigation_id=None,
    conversation_id=None,
    message_id=None,
    progress_callback=None
):

    started = time.monotonic()
    clean = {}

    try:

        clean = _clean_args(name, args)
        if name == "attachments_read":
            output = _attachments_read(clean, attachment_rows or [])
        elif name == "attachments_search":
            output = _attachments_search(clean, attachment_rows or [])
        elif name == "project_search":
            output = _project_search(clean, project, project_service)
        elif name == "project_find_scripts":
            output = _project_find_scripts(clean, project, project_service)
        elif name == "project_review":
            output = review_project(
                model,
                project_service,
                project,
                clean["query"],
                clean.get("scope") or "related",
                visual_context,
                request_context,
                conversation_id=conversation_id,
                message_id=message_id,
                investigation_id=investigation_id,
                progress_callback=progress_callback
            )
        elif name == "project_script_read":
            output = _project_script_read(clean, project, project_service)
        elif name == "project_read":
            output = _project_read(clean, project, project_service)
        elif name == "project_tree":
            output = _project_tree(clean, project, project_service)
        elif name == "project_node_read":
            output = _project_node_read(clean, project, project_service)
        else:
            output = HANDLERS[name](clean, config, policy)
        ok = True
        error = ""

    except ToolError as exc:

        ok = False
        error = str(exc)
        output = ""

    except Exception as exc:

        ok = False
        error = f"{type(exc).__name__}: {exc}"
        output = ""

    if len(output) > config.max_output_chars:

        cut = output[: config.max_output_chars]
        note = "[output truncated]"
        numbers = re.findall(r"(?m)^\s*(\d+)\| ", cut)

        if numbers:

            note = (
                "[output truncated; continue with start_line "
                f"{int(numbers[-1]) + 1}]"
            )

        output = f"{cut}\n{note}"

    return {
        "name": name,
        "args": clean if clean else args,
        "ok": ok,
        "output": output,
        "error": error,
        "seconds": round(time.monotonic() - started, 2)
    }


def policy_for(config):

    return PathPolicy(config)
