TOOLS = [
    {
        "name": "system_time",
        "description": (
            "Current date and time. Optional IANA timezone such as "
            "'Asia/Tokyo'; omit it for the local time."
        ),
        "args": {
            "timezone": {
                "type": "str",
                "required": False,
                "description": "IANA timezone name"
            }
        },
        "risk": "read"
    },
    {
        "name": "system_info",
        "description": (
            "Operating system, CPU, RAM, disks, and GPU of this computer."
        ),
        "args": {},
        "risk": "read"
    },
    {
        "name": "files_list",
        "description": (
            "List a folder inside the allowed folders. Returns names, "
            "types, sizes, and modified times."
        ),
        "args": {
            "path": {
                "type": "str",
                "required": False,
                "description": "Absolute path or path relative to the project"
            }
        },
        "risk": "read"
    },
    {
        "name": "files_search",
        "description": (
            "Search file names or file contents inside the allowed folders."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": "Text or wildcard pattern to find"
            },
            "path": {
                "type": "str",
                "required": False,
                "description": "Folder to search; defaults to the project"
            },
            "mode": {
                "type": "str",
                "required": False,
                "description": "'name' or 'content'; defaults to name"
            },
            "recursive": {
                "type": "bool",
                "required": False,
                "description": (
                    "Search inside subfolders; set false for top-level "
                    "files only; defaults to true"
                )
            }
        },
        "risk": "read"
    },
    {
        "name": "files_read",
        "description": (
            "Read a text file inside the allowed folders."
        ),
        "args": {
            "path": {
                "type": "str",
                "required": True,
                "description": "Absolute path or path relative to the project"
            },
            "start_line": {
                "type": "int",
                "required": False,
                "description": "First line to return, starting at 1"
            },
            "max_lines": {
                "type": "int",
                "required": False,
                "description": "How many lines to return"
            }
        },
        "risk": "read"
    },
    {
        "name": "files_write",
        "description": (
            "Create a text file inside the allowed folders, or replace an "
            "existing one when overwrite is true. The user must approve "
            "every write."
        ),
        "args": {
            "path": {
                "type": "str",
                "required": True,
                "description": "Absolute path or path relative to the project"
            },
            "content": {
                "type": "str",
                "required": True,
                "description": "Full text to write"
            },
            "overwrite": {
                "type": "bool",
                "required": False,
                "description": "Replace the file if it already exists"
            }
        },
        "risk": "write"
    },
    {
        "name": "files_move",
        "description": (
            "Move or rename a file inside the allowed folders, or replace "
            "the destination when overwrite is true. The user must approve "
            "every move."
        ),
        "args": {
            "source": {
                "type": "str",
                "required": True,
                "description": "Existing file to move"
            },
            "destination": {
                "type": "str",
                "required": True,
                "description": "New path, including the new file name"
            },
            "overwrite": {
                "type": "bool",
                "required": False,
                "description": "Replace the destination if it already exists"
            }
        },
        "risk": "write"
    },
    {
        "name": "files_delete",
        "description": (
            "Delete a file or folder by sending it to the Windows Recycle "
            "Bin, where it can still be restored. The user must approve "
            "every delete."
        ),
        "args": {
            "path": {
                "type": "str",
                "required": True,
                "description": "File or folder to send to the Recycle Bin"
            }
        },
        "risk": "write"
    },
    {
        "name": "luau_docs",
        "description": (
            "Search the bundled Luau language guide and the official Roblox "
            "engine reference for exact class, datatype, global, and library "
            "signatures, properties, and usage notes. Use it before writing "
            "Roblox Luau or when unsure about an API."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": (
                    "Class, datatype, function, or feature to look up, such "
                    "as 'TweenService Create' or 'how to teleport a player'"
                )
            },
            "limit": {
                "type": "int",
                "required": False,
                "description": "How many result blocks to return, 1 to 6"
            }
        },
        "risk": "read"
    },
    {
        "name": "run_command",
        "description": (
            "Run one shell command and return its output. Use it when "
            "files_search cannot do the job, such as findstr, where, dir "
            "/s, or PowerShell searches. The user must approve every "
            "command before it runs."
        ),
        "args": {
            "command": {
                "type": "str",
                "required": True,
                "description": "Command line to run; must finish on its own"
            },
            "cwd": {
                "type": "str",
                "required": False,
                "description": (
                    "Folder to run the command in; defaults to the project "
                    "folder"
                )
            }
        },
        "risk": "exec"
    }
]

TOOL_MAP = {
    item["name"]: item
    for item in TOOLS
}


def catalog_text():

    lines = []

    for item in TOOLS:

        args = []

        for name, spec in item["args"].items():

            suffix = "" if spec["required"] else "?"

            args.append(f"{name}:{spec['type']}{suffix}")

        signature = ", ".join(args) if args else "no arguments"

        lines.append(
            f"- {item['name']} ({signature}): {item['description']}"
        )

    return "\n".join(lines)
