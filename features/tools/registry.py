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
        "name": "attachments_search",
        "description": (
            "Search extracted text from files attached in the current "
            "message. Use the exact attachment_id shown in the request "
            "context, or search all current attachments."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": "Text to find in attached file contents"
            },
            "attachment_id": {
                "type": "str",
                "required": False,
                "description": "Limit the search to this current attachment"
            },
            "max_results": {
                "type": "int",
                "required": False,
                "description": "Maximum matches to return; defaults to 10"
            }
        },
        "risk": "read"
    },
    {
        "name": "attachments_read",
        "description": (
            "Read a line range from the full extracted text of a file "
            "attached in the current message."
        ),
        "args": {
            "attachment_id": {
                "type": "str",
                "required": True,
                "description": "Exact current attachment ID"
            },
            "start_line": {
                "type": "int",
                "required": False,
                "description": "First line to return, starting at 1"
            },
            "max_lines": {
                "type": "int",
                "required": False,
                "description": "Lines to return; defaults to 100"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_search",
        "description": (
            "Search the full parsed contents of the active persistent "
            "Roblox project, including scripts and hierarchy."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": "Text to find in the active Roblox project"
            },
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "max_results": {
                "type": "int",
                "required": False,
                "description": "Maximum matches to return; defaults to 10"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_find_scripts",
        "description": (
            "Scan every indexed script in the active Roblox project for a "
            "concept and related terms. Returns all matching script paths "
            "and source-line evidence, with pagination for large result sets."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": (
                    "Concept and relevant synonyms, alternate names, code "
                    "identifiers, or API/property names to search for"
                )
            },
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "max_results": {
                "type": "int",
                "required": False,
                "description": "Results per page; defaults to 100"
            },
            "offset": {
                "type": "int",
                "required": False,
                "description": "Skip this many matching scripts"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_review",
        "description": (
            "Run a coordinated investigation of the active Roblox project: "
            "Project Scout discovers and retrieves scripts, Code Analyst "
            "can request additional evidence, and Solution Planner runs "
            "only after the coordinator verifies completeness. The shared "
            "manifest and progress are persisted. Use scope 'all' only when "
            "the user explicitly asks for every script."
        ),
        "args": {
            "query": {
                "type": "str",
                "required": True,
                "description": (
                    "The feature, behavior, system, or user request to review"
                )
            },
            "scope": {
                "type": "str",
                "required": False,
                "description": "'related' or 'all'; defaults to related"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_script_read",
        "description": (
            "Read up to 200 exact source lines from one indexed script. "
            "Paginate with start_line for larger files, or use "
            "project_review for complete multi-script source analysis."
        ),
        "args": {
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "script_id": {
                "type": "str",
                "required": True,
                "description": "Exact script_id returned by project_find_scripts"
            },
            "start_line": {
                "type": "int",
                "required": False,
                "description": "First source line to return, starting at 1"
            },
            "max_lines": {
                "type": "int",
                "required": False,
                "description": "Source lines to return; defaults to 100"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_read",
        "description": (
            "Read exact line ranges from the full parsed text of the active "
            "Roblox project. Use project_search first to locate evidence."
        ),
        "args": {
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "start_line": {
                "type": "int",
                "required": False,
                "description": "First parsed-text line to return, starting at 1"
            },
            "max_lines": {
                "type": "int",
                "required": False,
                "description": "Lines to return; defaults to 100"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_tree",
        "description": (
            "Browse children in the active Roblox project's complete "
            "hierarchy. Omit parent_id for top-level instances."
        ),
        "args": {
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "parent_id": {
                "type": "str",
                "required": False,
                "description": "Node ID returned by a previous project_tree call"
            },
            "offset": {
                "type": "int",
                "required": False,
                "description": "Skip this many siblings; defaults to 0"
            },
            "limit": {
                "type": "int",
                "required": False,
                "description": "Children to return; maximum 200"
            }
        },
        "risk": "read"
    },
    {
        "name": "project_node_read",
        "description": (
            "Read the exact properties of one hierarchy node in the active "
            "Roblox project using its node_id from project_tree."
        ),
        "args": {
            "project_id": {
                "type": "str",
                "required": False,
                "description": "The active project ID from the request context"
            },
            "node_id": {
                "type": "str",
                "required": True,
                "description": "Exact node_id returned by project_tree"
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
