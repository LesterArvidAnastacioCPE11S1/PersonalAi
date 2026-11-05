import sqlite3
import uuid

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    premise TEXT NOT NULL DEFAULT '',
    setting TEXT NOT NULL DEFAULT '',
    characters TEXT NOT NULL DEFAULT '',
    style TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT 'setup',
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
"""

CONVERSATION_FIELDS = {
    "title",
    "premise",
    "setting",
    "characters",
    "style"
}

LORE_FIELDS = {
    "category",
    "subject",
    "detail",
    "keywords"
}

CONVERSATION_COLUMNS = {
    "phase": "TEXT NOT NULL DEFAULT 'story'",
    "summary": "TEXT NOT NULL DEFAULT ''",
    "last_extracted_id": "INTEGER NOT NULL DEFAULT 0"
}

PHASES = {"setup", "story"}

MESSAGE_COLUMNS = {
    "prompt_content": "TEXT NOT NULL DEFAULT ''"
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
            connection.commit()

    def _migrate(self, connection):

        tables = {
            "conversations": CONVERSATION_COLUMNS,
            "messages": MESSAGE_COLUMNS
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
                ) AS attachment_count
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
                ) AS lore_count
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
        style=""
    ):

        conversation_id = uuid.uuid4().hex
        now = _now()
        cleaned_title = (title or "").strip() or "New chat"

        with closing(self._connect()) as connection:

            connection.execute(
                """
                INSERT INTO conversations (
                    id, title, premise, setting,
                    characters, style, phase,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    cleaned_title,
                    premise or "",
                    setting or "",
                    characters or "",
                    style or "",
                    "setup",
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
