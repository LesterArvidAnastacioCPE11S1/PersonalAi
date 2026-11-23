import sqlite3
import re
import uuid
import json

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from core.persona import (
    DEFAULT_ASSISTANT_PERSONA_ID,
    DEFAULT_ASSISTANT_PERSONA_NAME,
    DEFAULT_ASSISTANT_PERSONA_TEXT,
    DEFAULT_CODING_PERSONA_ID,
    DEFAULT_CODING_PERSONA_NAME,
    DEFAULT_CODING_PERSONA_TEXT,
    DEFAULT_STORY_PERSONA_ID
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    premise TEXT NOT NULL DEFAULT '',
    setting TEXT NOT NULL DEFAULT '',
    characters TEXT NOT NULL DEFAULT '',
    style TEXT NOT NULL DEFAULT '',
    narrative_style TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT 'chat',
    summary TEXT NOT NULL DEFAULT '',
    last_extracted_id INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    prompt_content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (conversation_id, id);

CREATE INDEX IF NOT EXISTS idx_conversations_updated
    ON conversations (updated_at DESC);

CREATE TABLE IF NOT EXISTS lore (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'fact',
    subject TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lore_conversation
    ON lore (conversation_id, id);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    message_id INTEGER,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'text',
    size INTEGER NOT NULL DEFAULT 0,
    path TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages (id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_attachments_conversation
    ON attachments (conversation_id, id);

CREATE INDEX IF NOT EXISTS idx_attachments_message
    ON attachments (message_id);

CREATE TABLE IF NOT EXISTS tool_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id INTEGER,
    tool TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    seconds REAL NOT NULL DEFAULT 0,
    output_chars INTEGER NOT NULL DEFAULT 0,
    output TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages (id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_runs_conversation
    ON tool_runs (conversation_id, id);

CREATE TABLE IF NOT EXISTS tool_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id INTEGER,
    tool TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '',
    risk TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    decided_at TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages (id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_approvals_conversation
    ON tool_approvals (conversation_id, id);

CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    builtin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    source_path TEXT NOT NULL,
    parsed_path TEXT NOT NULL,
    instance_count INTEGER NOT NULL DEFAULT 0,
    script_count INTEGER NOT NULL DEFAULT 0,
    root_count INTEGER NOT NULL DEFAULT 0,
    class_counts_json TEXT NOT NULL DEFAULT '{}',
    properties_indexed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_nodes (
    project_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    parent_id TEXT,
    name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    path TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    child_count INTEGER NOT NULL DEFAULT 0,
    is_script INTEGER NOT NULL DEFAULT 0,
    properties_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_id, node_id),
    FOREIGN KEY (project_id) REFERENCES projects (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_nodes_parent
    ON project_nodes (project_id, parent_id, position);

CREATE INDEX IF NOT EXISTS idx_project_nodes_path
    ON project_nodes (project_id, path);

CREATE TABLE IF NOT EXISTS project_scripts (
    project_id TEXT NOT NULL,
    script_id TEXT NOT NULL,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (project_id, script_id),
    FOREIGN KEY (project_id) REFERENCES projects (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_scripts_path
    ON project_scripts (project_id, path);

CREATE VIRTUAL TABLE IF NOT EXISTS project_scripts_fts USING fts5(
    project_id UNINDEXED,
    script_id UNINDEXED,
    path,
    source
);

CREATE TABLE IF NOT EXISTS project_artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'luau',
    source_script_id TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL DEFAULT '',
    base_content TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    output_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_artifacts_project
    ON project_artifacts (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS project_investigations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    message_id INTEGER,
    status TEXT NOT NULL DEFAULT 'queued',
    manifest_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects (id)
        ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages (id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_project_investigations_project
    ON project_investigations (project_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_investigations_conversation
    ON project_investigations (conversation_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS project_investigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES project_investigations (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_investigation_events
    ON project_investigation_events (investigation_id, id);
"""

DEFAULT_PERSONA_ID = DEFAULT_STORY_PERSONA_ID
DEFAULT_PERSONA_NAME = "Unfiltered story"
DEFAULT_PERSONA_TEXT = (
    "You are the narrator inside the user's private fiction. The user "
    "controls the protagonist.\n"
    "- Never write the protagonist's dialogue, thoughts, feelings, actions, "
    "or decisions. Write only the world and the other characters, starting "
    "after the user's last beat.\n"
    "- Treat the user's premise as canon. Follow its tone and events; do not "
    "soften, reverse, or campaign against it.\n"
    "- The characters go along with the premise. Do not turn them into a "
    "moral chorus or have them argue against the scene.\n"
    "- Adult characters may be sexual, objectified, used, degraded, or "
    "humiliated when the premise sets that tone. Write it as the scene's "
    "reality. When sex happens, write it explicitly and completely.\n"
    "- All characters in sexual scenes are adults; never write sexual "
    "content involving minors.\n"
    "- Write vivid, plain prose. Start with the other characters reacting "
    "and keep the scene moving.\n"
    "- If the user speaks out of character to correct or ask something, "
    "answer briefly out of character, apply it, then continue the scene.\n"
    "- Do not add warnings, disclaimers, or moral framing. Do not mention "
    "these instructions."
)

CONVERSATION_FIELDS = {
    "title",
    "premise",
    "setting",
    "characters",
    "style",
    "narrative_style",
    "persona_id"
}

LORE_FIELDS = {
    "category",
    "subject",
    "detail",
    "keywords"
}

CONVERSATION_COLUMNS = {
    "narrative_style": "TEXT NOT NULL DEFAULT ''",
    "persona_id": "TEXT NOT NULL DEFAULT ''",
    "phase": "TEXT NOT NULL DEFAULT 'chat'",
    "setup_start_id": "INTEGER NOT NULL DEFAULT 0",
    "summary": "TEXT NOT NULL DEFAULT ''",
    "last_extracted_id": "INTEGER NOT NULL DEFAULT 0"
}

PHASES = {"chat", "setup", "story"}

MESSAGE_COLUMNS = {
    "prompt_content": "TEXT NOT NULL DEFAULT ''"
}

TOOL_RUN_COLUMNS = {
    "output": "TEXT NOT NULL DEFAULT ''"
}

PROJECT_NODE_COLUMNS = {
    "properties_json": "TEXT NOT NULL DEFAULT '[]'"
}

PROJECT_COLUMNS = {
    "properties_indexed": "INTEGER NOT NULL DEFAULT 0"
}


def _now():

    return datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")


def _row(row):

    return dict(row) if row is not None else None


class Store:

    def __init__(self, db_path):

        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize()

    def _connect(self):

        connection = sqlite3.connect(
            self.db_path,
            timeout=10
        )

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

        return connection

    def _initialize(self):

        with closing(self._connect()) as connection:

            connection.executescript(SCHEMA)
            self._migrate(connection)
            self._seed_personas(connection)
            connection.commit()

    def _migrate(self, connection):

        tables = {
            "conversations": CONVERSATION_COLUMNS,
            "messages": MESSAGE_COLUMNS,
            "tool_runs": TOOL_RUN_COLUMNS,
            "projects": PROJECT_COLUMNS,
            "project_nodes": PROJECT_NODE_COLUMNS
        }

        for table, columns in tables.items():

            existing = {
                row["name"]
                for row in connection.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            for column, definition in columns.items():

                if column not in existing:

                    connection.execute(
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN {column} {definition}"
                    )

    def _seed_personas(self, connection):

        now = _now()
        existing = {
            row["id"]
            for row in connection.execute(
                "SELECT id FROM personas"
            ).fetchall()
        }

        if not existing:

            connection.execute(
                """
                INSERT INTO personas (
                    id, name, instructions, builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    DEFAULT_PERSONA_ID,
                    DEFAULT_PERSONA_NAME,
                    DEFAULT_PERSONA_TEXT,
                    now,
                    now
                )
            )

        if DEFAULT_CODING_PERSONA_ID not in existing:

            connection.execute(
                """
                INSERT INTO personas (
                    id, name, instructions, builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    DEFAULT_CODING_PERSONA_ID,
                    DEFAULT_CODING_PERSONA_NAME,
                    DEFAULT_CODING_PERSONA_TEXT,
                    now,
                    now
                )
            )
            connection.execute(
                """
                UPDATE conversations
                SET persona_id = ?, updated_at = ?
                WHERE persona_id = ? AND phase = 'chat'
                """,
                (DEFAULT_CODING_PERSONA_ID, now, DEFAULT_PERSONA_ID)
            )

        if DEFAULT_ASSISTANT_PERSONA_ID not in existing:

            connection.execute(
                """
                INSERT INTO personas (
                    id, name, instructions, builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    DEFAULT_ASSISTANT_PERSONA_ID,
                    DEFAULT_ASSISTANT_PERSONA_NAME,
                    DEFAULT_ASSISTANT_PERSONA_TEXT,
                    now,
                    now
                )
            )
            connection.execute(
                """
                UPDATE conversations
                SET persona_id = ?, updated_at = ?
                WHERE phase = 'chat' AND persona_id IN (?, ?)
                """,
                (
                    DEFAULT_ASSISTANT_PERSONA_ID,
                    now,
                    DEFAULT_PERSONA_ID,
                    DEFAULT_CODING_PERSONA_ID
                )
            )

    def list_personas(self):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM personas
                ORDER BY builtin DESC, name COLLATE NOCASE ASC
                """
            ).fetchall()

        return [_row(row) for row in rows]

    def get_persona(self, persona_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                "SELECT * FROM personas WHERE id = ?",
                (persona_id,)
            ).fetchone()

        return _row(row)

    def default_persona(self):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT *
                FROM personas
                ORDER BY
                    CASE WHEN id = ? THEN 0 ELSE 1 END,
                    builtin DESC,
                    created_at ASC
                LIMIT 1
                """,
                (DEFAULT_ASSISTANT_PERSONA_ID,)
            ).fetchone()

        return _row(row)

    def create_persona(self, name, instructions):

        persona_id = uuid.uuid4().hex
        now = _now()

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO personas (
                    id, name, instructions, builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (
                    persona_id,
                    (name or "").strip() or "Untitled persona",
                    instructions or "",
                    now,
                    now
                )
            )

            connection.commit()

        return self.get_persona(persona_id)

    def update_persona(self, persona_id, values):

        updates = {
            key: value
            for key, value in values.items()
            if key in {"name", "instructions"}
        }

        if not updates:

            return self.get_persona(persona_id)

        if "name" in updates:

            updates["name"] = (
                str(updates["name"]).strip()
                or "Untitled persona"
            )

        assignments = ", ".join(
            f"{key} = ?"
            for key in updates
        )

        parameters = list(updates.values())
        parameters.extend([_now(), persona_id])

        with closing(self._connect()) as connection:

            connection.execute(
                f"""
                UPDATE personas
                SET {assignments}, updated_at = ?
                WHERE id = ?
                """,
                parameters
            )

            connection.commit()

        return self.get_persona(persona_id)

    def delete_persona(self, persona_id):

        with closing(self._connect()) as connection:

            connection.execute(
                "DELETE FROM personas WHERE id = ?",
                (persona_id,)
            )
            connection.execute(
                """
                UPDATE conversations
                SET persona_id = '', updated_at = ?
                WHERE persona_id = ?
                """,
                (_now(), persona_id)
            )

            connection.commit()

    def list_conversations(self):

        query = """
            SELECT
                c.*,
                COUNT(m.id) AS message_count,
                COALESCE(
                    (
                        SELECT content
                        FROM messages
                        WHERE conversation_id = c.id
                        ORDER BY id DESC
                        LIMIT 1
                    ),
                    ''
                ) AS preview,
                (
                    SELECT COUNT(*)
                    FROM lore
                    WHERE conversation_id = c.id
                ) AS lore_count,
                (
                    SELECT COUNT(*)
                    FROM attachments
                    WHERE conversation_id = c.id
                ) AS attachment_count,
                COALESCE(
                    (
                        SELECT name
                        FROM personas
                        WHERE id = c.persona_id
                    ),
                    ''
                ) AS persona_name
            FROM conversations c
            LEFT JOIN messages m
                ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """

        with closing(self._connect()) as connection:

            rows = connection.execute(query).fetchall()

        return [_row(row) for row in rows]

    def get_conversation(self, conversation_id):

        query = """
            SELECT
                c.*,
                COUNT(m.id) AS message_count,
                (
                    SELECT COUNT(*)
                    FROM lore
                    WHERE conversation_id = c.id
                ) AS lore_count,
                COALESCE(
                    (
                        SELECT name
                        FROM personas
                        WHERE id = c.persona_id
                    ),
                    ''
                ) AS persona_name
            FROM conversations c
            LEFT JOIN messages m
                ON m.conversation_id = c.id
            WHERE c.id = ?
            GROUP BY c.id
        """

        with closing(self._connect()) as connection:

            row = connection.execute(
                query,
                (conversation_id,)
            ).fetchone()

        return _row(row)

    def create_conversation(
        self,
        title=None,
        premise="",
        setting="",
        characters="",
        style="",
        narrative_style="",
        persona_id=""
    ):

        conversation_id = uuid.uuid4().hex
        now = _now()
        cleaned_title = (title or "").strip() or "New chat"

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO conversations (
                    id, title, premise, setting,
                    characters, style, narrative_style,
                    persona_id, phase, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    cleaned_title,
                    premise or "",
                    setting or "",
                    characters or "",
                    style or "",
                    narrative_style or "",
                    persona_id or "",
                    "chat",
                    now,
                    now
                )
            )

            connection.commit()

        return self.get_conversation(conversation_id)

    def update_conversation(
        self,
        conversation_id,
        values
    ):

        updates = {
            key: value
            for key, value in values.items()
            if key in CONVERSATION_FIELDS
        }

        if not updates:

            return self.get_conversation(conversation_id)

        if "title" in updates:

            updates["title"] = (
                str(updates["title"]).strip()
                or "New chat"
            )

        assignments = ", ".join(
            f"{key} = ?"
            for key in updates
        )

        parameters = list(updates.values())
        parameters.extend([_now(), conversation_id])

        with closing(self._connect()) as connection:

            connection.execute(
                f"""
                UPDATE conversations
                SET {assignments}, updated_at = ?
                WHERE id = ?
                """,
                parameters
            )

            connection.commit()

        return self.get_conversation(conversation_id)

    def last_message_id(self, conversation_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT COALESCE(MAX(id), 0) AS id
                FROM messages
                WHERE conversation_id = ?
                """,
                (conversation_id,)
            ).fetchone()

        return int(row["id"] or 0)

    def set_setup_start(self, conversation_id, message_id):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE conversations
                SET setup_start_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(message_id or 0), _now(), conversation_id)
            )

            connection.commit()

        return self.get_conversation(conversation_id)

    def set_phase(self, conversation_id, phase):

        if phase not in PHASES:

            raise ValueError("Unknown story phase.")

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                """
                UPDATE conversations
                SET phase = ?, updated_at = ?
                WHERE id = ?
                """,
                (phase, _now(), conversation_id)
            )

            connection.commit()

        if cursor.rowcount == 0:

            return None

        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id):

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,)
            )

            connection.commit()

        return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id,
        role,
        content,
        prompt_content=None
    ):

        now = _now()
        prompt_content = prompt_content or ""

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                """
                INSERT INTO messages (
                    conversation_id, role, content,
                    prompt_content, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    prompt_content,
                    now
                )
            )

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, conversation_id)
            )

            connection.commit()

            message_id = cursor.lastrowid

        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "prompt_content": prompt_content,
            "created_at": now
        }

    def add_tool_run(
        self,
        conversation_id,
        tool,
        args="",
        status="ok",
        seconds=0.0,
        output_chars=0,
        output="",
        message_id=None
    ):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO tool_runs (
                    conversation_id, message_id, tool, args,
                    status, seconds, output_chars, output, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    message_id,
                    tool,
                    args or "",
                    status,
                    float(seconds or 0),
                    int(output_chars or 0),
                    output or "",
                    _now()
                )
            )

            connection.commit()

    def list_tool_runs(self, conversation_id, limit=5):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT id, conversation_id, message_id, tool, args,
                       status, output, created_at
                FROM tool_runs
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, int(limit))
            ).fetchall()

        return [_row(row) for row in reversed(rows)]

    def create_project_investigation(
        self,
        investigation_id,
        project_id,
        conversation_id,
        message_id,
        manifest,
        event
    ):

        now = _now()

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO project_investigations (
                    id, project_id, conversation_id, message_id, status,
                    manifest_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    project_id,
                    conversation_id,
                    message_id,
                    manifest.get("investigation_status", "queued"),
                    json.dumps(manifest, ensure_ascii=True),
                    now,
                    now
                )
            )
            connection.execute(
                """
                INSERT INTO project_investigation_events (
                    investigation_id, event_json, created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    investigation_id,
                    json.dumps(event, ensure_ascii=True),
                    now
                )
            )
            connection.commit()

        return self.get_project_investigation(investigation_id)

    def save_project_investigation(self, investigation_id, manifest, event):

        now = _now()

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE project_investigations
                SET status = ?, manifest_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    manifest.get("investigation_status", "in_progress"),
                    json.dumps(manifest, ensure_ascii=True),
                    now,
                    investigation_id
                )
            )
            connection.execute(
                """
                INSERT INTO project_investigation_events (
                    investigation_id, event_json, created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    investigation_id,
                    json.dumps(event, ensure_ascii=True),
                    now
                )
            )
            connection.commit()

        return self.get_project_investigation(investigation_id)

    @staticmethod
    def _project_investigation(row):

        item = _row(row)

        if item is not None:

            item["manifest"] = json.loads(item.pop("manifest_json") or "{}")

        return item

    def get_project_investigation(self, investigation_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT id, project_id, conversation_id, message_id, status,
                       manifest_json, created_at, updated_at
                FROM project_investigations
                WHERE id = ?
                """,
                (investigation_id,)
            ).fetchone()

        return self._project_investigation(row)

    def list_project_investigations(self, project_id, limit=20):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT id, project_id, conversation_id, message_id, status,
                       manifest_json, created_at, updated_at
                FROM project_investigations
                WHERE project_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (project_id, min(100, max(1, int(limit or 20))))
            ).fetchall()

        return [
            self._project_investigation(row)
            for row in rows
        ]

    def list_project_investigation_events(self, investigation_id, limit=500):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT id, event_json, created_at
                FROM project_investigation_events
                WHERE investigation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (investigation_id, min(2_000, max(1, int(limit or 500))))
            ).fetchall()

        return [
            {
                "id": row["id"],
                "event": json.loads(row["event_json"]),
                "created_at": row["created_at"]
            }
            for row in reversed(rows)
        ]

    def set_project_investigation_message(self, investigation_id, message_id):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE project_investigations
                SET message_id = ?
                WHERE id = ?
                """,
                (message_id, investigation_id)
            )
            connection.commit()

    def add_tool_approval(
        self,
        conversation_id,
        tool,
        args="",
        risk="",
        summary="",
        message_id=None
    ):

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                """
                INSERT INTO tool_approvals (
                    conversation_id, message_id, tool, args, risk,
                    summary, status, result, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending', '', ?)
                """,
                (
                    conversation_id,
                    message_id,
                    tool,
                    args or "",
                    risk,
                    summary,
                    _now()
                )
            )

            connection.commit()

            approval_id = cursor.lastrowid

        return self.get_tool_approval(approval_id)

    def get_tool_approval(self, approval_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT id, conversation_id, message_id, tool, args, risk,
                       summary, status, result, created_at, decided_at
                FROM tool_approvals
                WHERE id = ?
                """,
                (approval_id,)
            ).fetchone()

        return _row(row)

    def list_tool_approvals(self, conversation_id):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT id, conversation_id, message_id, tool, args, risk,
                       summary, status, result, created_at, decided_at
                FROM tool_approvals
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            ).fetchall()

        return [_row(row) for row in rows]

    def set_tool_approval_status(self, approval_id, status, result=""):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE tool_approvals
                SET status = ?, result = ?, decided_at = ?
                WHERE id = ?
                """,
                (status, result or "", _now(), approval_id)
            )

            connection.commit()

        return self.get_tool_approval(approval_id)

    def get_messages(
        self,
        conversation_id,
        include_prompt=False
    ):

        columns = "id, conversation_id, role, content, created_at"

        if include_prompt:

            columns += ", prompt_content"

        with closing(self._connect()) as connection:

            rows = connection.execute(
                f"""
                SELECT {columns}
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            ).fetchall()

        return [_row(row) for row in rows]

    def get_message(self, message_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT
                    id, conversation_id, role, content,
                    prompt_content, created_at
                FROM messages
                WHERE id = ?
                """,
                (message_id,)
            ).fetchone()

        return _row(row)

    def update_message(self, message_id, content):

        row = self.get_message(message_id)

        if row is None:

            return None

        with closing(self._connect()) as connection:

            connection.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (content, message_id)
            )

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (_now(), row["conversation_id"])
            )

            connection.commit()

        return self.get_message(message_id)

    def truncate_after(self, conversation_id, message_id):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT a.*
                FROM attachments a
                JOIN messages m
                    ON m.id = a.message_id
                WHERE a.conversation_id = ?
                    AND m.id > ?
                """,
                (conversation_id, message_id)
            ).fetchall()

            if rows:

                placeholders = ", ".join(
                    "?" for _ in rows
                )

                connection.execute(
                    f"""
                    DELETE FROM attachments
                    WHERE id IN ({placeholders})
                    """,
                    [row["id"] for row in rows]
                )

            cursor = connection.execute(
                """
                DELETE FROM messages
                WHERE conversation_id = ? AND id > ?
                """,
                (conversation_id, message_id)
            )

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (_now(), conversation_id)
            )

            connection.commit()

        return [_row(row) for row in rows], cursor.rowcount

    def auto_title(self, conversation_id, message):

        title = " ".join(
            message.strip().split()
        )

        if not title:

            return

        if len(title) > 60:

            title = title[:57].rstrip() + "..."

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ? AND title = 'New chat'
                """,
                (title, _now(), conversation_id)
            )

            connection.commit()

    def list_lore(self, conversation_id):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM lore
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            ).fetchall()

        return [_row(row) for row in rows]

    def get_lore(self, lore_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                "SELECT * FROM lore WHERE id = ?",
                (lore_id,)
            ).fetchone()

        return _row(row)

    def add_lore(
        self,
        conversation_id,
        category="fact",
        subject="",
        detail="",
        keywords="",
        source="manual"
    ):

        now = _now()
        subject = (subject or "").strip()
        category = (category or "fact").strip().lower() or "fact"
        detail = (detail or "").strip()
        source = (source or "manual").strip() or "manual"

        if isinstance(keywords, (list, tuple)):

            keywords = ", ".join(
                str(item).strip()
                for item in keywords
                if str(item).strip()
            )

        keywords = (keywords or "").strip()

        with closing(self._connect()) as connection:

            existing = None

            if subject:

                existing = connection.execute(
                    """
                    SELECT id
                    FROM lore
                    WHERE conversation_id = ?
                        AND lower(subject) = lower(?)
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (conversation_id, subject)
                ).fetchone()

            if existing is not None:

                lore_id = existing["id"]

                connection.execute(
                    """
                    UPDATE lore
                    SET category = ?, subject = ?, detail = ?,
                        keywords = ?, source = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        category,
                        subject,
                        detail,
                        keywords,
                        source,
                        now,
                        lore_id
                    )
                )

            else:

                cursor = connection.execute(
                    """
                    INSERT INTO lore (
                        conversation_id, category, subject, detail,
                        keywords, source, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        category,
                        subject,
                        detail,
                        keywords,
                        source,
                        now,
                        now
                    )
                )

                lore_id = cursor.lastrowid

            connection.commit()

        return self.get_lore(lore_id)

    def update_lore(self, lore_id, values):

        updates = {
            key: value
            for key, value in values.items()
            if key in LORE_FIELDS
        }

        if not updates:

            return self.get_lore(lore_id)

        if "category" in updates:

            updates["category"] = (
                str(updates["category"]).strip().lower()
                or "fact"
            )

        if "subject" in updates:

            updates["subject"] = str(
                updates["subject"]
            ).strip()

        if "detail" in updates:

            updates["detail"] = str(
                updates["detail"]
            ).strip()

        if "keywords" in updates:

            if isinstance(updates["keywords"], (list, tuple)):

                updates["keywords"] = ", ".join(
                    str(item).strip()
                    for item in updates["keywords"]
                    if str(item).strip()
                )

            else:

                updates["keywords"] = str(
                    updates["keywords"] or ""
                ).strip()

        assignments = ", ".join(
            f"{key} = ?"
            for key in updates
        )

        parameters = list(updates.values())
        parameters.extend([_now(), lore_id])

        with closing(self._connect()) as connection:

            connection.execute(
                f"""
                UPDATE lore
                SET {assignments}, updated_at = ?
                WHERE id = ?
                """,
                parameters
            )

            connection.commit()

        return self.get_lore(lore_id)

    def delete_lore(self, lore_id):

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                "DELETE FROM lore WHERE id = ?",
                (lore_id,)
            )

            connection.commit()

        return cursor.rowcount > 0

    def add_attachment(
        self,
        conversation_id,
        attachment_id,
        filename,
        mime,
        kind,
        size,
        path,
        text=""
    ):

        now = _now()

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO attachments (
                    id, conversation_id, message_id, filename,
                    mime, kind, size, path, text, created_at
                )
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment_id,
                    conversation_id,
                    filename,
                    mime or "",
                    kind or "text",
                    int(size or 0),
                    path or "",
                    text or "",
                    now
                )
            )

            connection.commit()

        return self.get_attachment(attachment_id)

    def update_attachment_text(self, attachment_id, text):

        with closing(self._connect()) as connection:

            connection.execute(
                "UPDATE attachments SET text = ? WHERE id = ?",
                (text or "", attachment_id)
            )

            connection.commit()

        return self.get_attachment(attachment_id)

    def get_attachment(self, attachment_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                "SELECT * FROM attachments WHERE id = ?",
                (attachment_id,)
            ).fetchone()

        return _row(row)

    def list_attachments(
        self,
        conversation_id,
        message_id=None,
        unlinked=False
    ):

        conditions = ["conversation_id = ?"]
        parameters = [conversation_id]

        if unlinked:

            conditions.append("message_id IS NULL")

        elif message_id is not None:

            conditions.append("message_id = ?")
            parameters.append(message_id)

        with closing(self._connect()) as connection:

            rows = connection.execute(
                f"""
                SELECT *
                FROM attachments
                WHERE {" AND ".join(conditions)}
                ORDER BY rowid ASC
                """,
                parameters
            ).fetchall()

        return [_row(row) for row in rows]

    def count_unlinked_attachments(self, conversation_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM attachments
                WHERE conversation_id = ? AND message_id IS NULL
                """,
                (conversation_id,)
            ).fetchone()

        return row["total"] if row else 0

    def create_project(self, project, nodes, scripts):

        node_batch = []
        script_batch = []
        search_batch = []

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO projects (
                    id, name, filename, source_path, parsed_path,
                    instance_count, script_count, root_count,
                    class_counts_json, properties_indexed,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["id"],
                    project["name"],
                    project["filename"],
                    project["source_path"],
                    project["parsed_path"],
                    project["instance_count"],
                    project["script_count"],
                    project["root_count"],
                    project["class_counts_json"],
                    1,
                    project["created_at"],
                    project["updated_at"]
                )
            )

            for node in nodes:

                node_batch.append(
                    (
                        project["id"],
                        node["node_id"],
                        node["parent_id"],
                        node["name"],
                        node["class_name"],
                        node["path"],
                        node["depth"],
                        node["position"],
                        node["child_count"],
                        int(node["is_script"]),
                        json.dumps(
                            node.get("properties") or [],
                            ensure_ascii=True
                        )
                    )
                )

                if len(node_batch) >= 1000:

                    connection.executemany(
                        """
                        INSERT INTO project_nodes (
                            project_id, node_id, parent_id, name,
                            class_name, path, depth, position,
                            child_count, is_script, properties_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        node_batch
                    )
                    node_batch.clear()

            if node_batch:

                connection.executemany(
                    """
                    INSERT INTO project_nodes (
                        project_id, node_id, parent_id, name,
                        class_name, path, depth, position,
                        child_count, is_script, properties_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    node_batch
                )

            for script in scripts:

                script_batch.append(
                    (
                        project["id"],
                        script["script_id"],
                        script["path"],
                        script["name"],
                        script["class_name"],
                        script["source"]
                    )
                )
                search_batch.append(
                    (
                        project["id"],
                        script["script_id"],
                        script["path"],
                        script["source"]
                    )
                )

                if len(script_batch) >= 100:

                    connection.executemany(
                        """
                        INSERT INTO project_scripts (
                            project_id, script_id, path, name,
                            class_name, source
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        script_batch
                    )
                    connection.executemany(
                        """
                        INSERT INTO project_scripts_fts (
                            project_id, script_id, path, source
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        search_batch
                    )
                    script_batch.clear()
                    search_batch.clear()

            if script_batch:

                connection.executemany(
                    """
                    INSERT INTO project_scripts (
                        project_id, script_id, path, name,
                        class_name, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    script_batch
                )
                connection.executemany(
                    """
                    INSERT INTO project_scripts_fts (
                        project_id, script_id, path, source
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    search_batch
                )

            connection.commit()

        return self.get_project(project["id"])

    def list_projects(self):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC, name"
            ).fetchall()

        return [_row(row) for row in rows]

    def get_project(self, project_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            ).fetchone()

        return _row(row)

    def delete_project(self, project_id):

        with closing(self._connect()) as connection:

            connection.execute(
                "DELETE FROM project_scripts_fts WHERE project_id = ?",
                (project_id,)
            )
            cursor = connection.execute(
                "DELETE FROM projects WHERE id = ?",
                (project_id,)
            )
            connection.commit()

        return cursor.rowcount > 0

    def list_project_nodes(
        self,
        project_id,
        parent_id=None,
        limit=200,
        offset=0
    ):

        if parent_id is None:

            condition = "parent_id IS NULL"
            parameters = [project_id]

        else:

            condition = "parent_id = ?"
            parameters = [project_id, parent_id]

        parameters.extend([limit, offset])

        with closing(self._connect()) as connection:

            rows = connection.execute(
                f"""
                SELECT node_id, parent_id, name, class_name, path,
                       depth, position, child_count, is_script
                FROM project_nodes
                WHERE project_id = ? AND {condition}
                ORDER BY position
                LIMIT ? OFFSET ?
                """,
                parameters
            ).fetchall()

        return [_row(row) for row in rows]

    def get_project_node(self, project_id, node_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT node_id, parent_id, name, class_name, path,
                       depth, position, child_count, is_script,
                       properties_json
                FROM project_nodes
                WHERE project_id = ? AND node_id = ?
                """,
                (project_id, node_id)
            ).fetchone()

        return _row(row)

    def update_project_node_properties(self, project_id, nodes):

        batch = []

        with closing(self._connect()) as connection:

            for node in nodes:

                batch.append(
                    (
                        json.dumps(
                            node.get("properties") or [],
                            ensure_ascii=True
                        ),
                        project_id,
                        node["node_id"]
                    )
                )

                if len(batch) >= 1000:

                    connection.executemany(
                        """
                        UPDATE project_nodes
                        SET properties_json = ?
                        WHERE project_id = ? AND node_id = ?
                        """,
                        batch
                    )
                    batch.clear()

            if batch:

                connection.executemany(
                    """
                    UPDATE project_nodes
                    SET properties_json = ?
                    WHERE project_id = ? AND node_id = ?
                    """,
                    batch
                )

            connection.execute(
                """
                UPDATE projects
                SET properties_indexed = 1
                WHERE id = ?
                """,
                (project_id,)
            )
            connection.commit()

    def list_project_scripts(self, project_id, limit=500, offset=0):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT script_id, path, name, class_name
                FROM project_scripts
                WHERE project_id = ?
                ORDER BY path COLLATE NOCASE
                LIMIT ? OFFSET ?
                """,
                (project_id, limit, offset)
            ).fetchall()

        return [_row(row) for row in rows]

    def iter_project_script_sources(self, project_id):

        connection = self._connect()

        try:

            cursor = connection.execute(
                """
                SELECT script_id, path, name, class_name, source
                FROM project_scripts
                WHERE project_id = ?
                ORDER BY path COLLATE NOCASE
                """,
                (project_id,)
            )

            for row in cursor:

                yield _row(row)

        finally:

            connection.close()

    def search_project_scripts(self, project_id, query, limit=20):

        terms = re.findall(r"[\w]+", query, flags=re.UNICODE)

        if not terms:

            return []

        match = " AND ".join(
            '"' + term.replace('"', '""') + '"'
            for term in terms
        )

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT s.script_id, s.path, s.name, s.class_name
                FROM project_scripts_fts f
                JOIN project_scripts s
                  ON s.project_id = f.project_id
                 AND s.script_id = f.script_id
                WHERE project_scripts_fts MATCH ?
                  AND f.project_id = ?
                ORDER BY bm25(project_scripts_fts)
                LIMIT ?
                """,
                (match, project_id, limit)
            ).fetchall()

        return [_row(row) for row in rows]

    def get_project_script(self, project_id, script_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT script_id, path, name, class_name, source
                FROM project_scripts
                WHERE project_id = ? AND script_id = ?
                """,
                (project_id, script_id)
            ).fetchone()

        return _row(row)

    def create_project_artifact(
        self,
        project_id,
        title,
        language,
        content,
        source_script_id=""
    ):

        artifact_id = uuid.uuid4().hex
        now = _now()
        source = self.get_project_script(project_id, source_script_id) \
            if source_script_id else None

        if source_script_id and source is None:

            return None

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO project_artifacts (
                    id, project_id, title, language, source_script_id,
                    source_path, base_content, content, status,
                    output_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', '', ?, ?)
                """,
                (
                    artifact_id,
                    project_id,
                    title,
                    language,
                    source_script_id or "",
                    source["path"] if source else "",
                    source["source"] if source else "",
                    content,
                    now,
                    now
                )
            )
            connection.commit()

        return self.get_project_artifact(project_id, artifact_id)

    def get_project_artifact(self, project_id, artifact_id):

        with closing(self._connect()) as connection:

            row = connection.execute(
                """
                SELECT *
                FROM project_artifacts
                WHERE project_id = ? AND id = ?
                """,
                (project_id, artifact_id)
            ).fetchone()

        return _row(row)

    def list_project_artifacts(self, project_id):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM project_artifacts
                WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (project_id,)
            ).fetchall()

        return [_row(row) for row in rows]

    def decide_project_artifact(
        self,
        project_id,
        artifact_id,
        status,
        output_path=""
    ):

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                """
                UPDATE project_artifacts
                SET status = ?, output_path = ?, updated_at = ?
                WHERE project_id = ? AND id = ? AND status = 'pending'
                """,
                (
                    status,
                    output_path,
                    _now(),
                    project_id,
                    artifact_id
                )
            )
            connection.commit()

        if cursor.rowcount == 0:

            return None

        return self.get_project_artifact(project_id, artifact_id)

    def link_attachments(self, attachment_ids, message_id):

        if not attachment_ids:

            return 0

        placeholders = ", ".join("?" for _ in attachment_ids)

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                f"""
                UPDATE attachments
                SET message_id = ?
                WHERE id IN ({placeholders})
                    AND message_id IS NULL
                """,
                [message_id, *attachment_ids]
            )

            connection.commit()

        return cursor.rowcount

    def delete_attachment(self, attachment_id):

        with closing(self._connect()) as connection:

            cursor = connection.execute(
                "DELETE FROM attachments WHERE id = ?",
                (attachment_id,)
            )

            connection.commit()

        return cursor.rowcount > 0

    def set_summary(self, conversation_id, summary):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE conversations
                SET summary = ?
                WHERE id = ?
                """,
                (summary or "", conversation_id)
            )

            connection.commit()

        return self.get_conversation(conversation_id)

    def mark_extracted(self, conversation_id, message_id):

        with closing(self._connect()) as connection:

            connection.execute(
                """
                UPDATE conversations
                SET last_extracted_id = ?
                WHERE id = ? AND last_extracted_id < ?
                """,
                (message_id, conversation_id, message_id)
            )

            connection.commit()

    def messages_after(self, conversation_id, message_id):

        with closing(self._connect()) as connection:

            rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE conversation_id = ? AND id > ?
                ORDER BY id ASC
                """,
                (conversation_id, message_id or 0)
            ).fetchall()

        return [_row(row) for row in rows]

    def get_memory(self, conversation_id):

        conversation = self.get_conversation(conversation_id)

        if conversation is None:

            return None

        return {
            "summary": conversation.get("summary") or "",
            "last_extracted_id": conversation.get(
                "last_extracted_id"
            ) or 0,
            "lore": self.list_lore(conversation_id)
        }
