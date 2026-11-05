import json
import re
import threading

from concurrent.futures import ThreadPoolExecutor


CATEGORIES = {
    "character",
    "place",
    "faction",
    "item",
    "event",
    "relationship",
    "rule",
    "fact"
}

EXTRACTOR = (
    "You maintain the story bible for a private fiction session. The "
    "narrator relies on you so that names, motives, injuries, promises, "
    "locations, and world rules never drift.\n\n"
    "Use the scenario, current summary, existing memory, and new transcript "
    "below. Reply with one JSON object and nothing else.\n\n"
    "{\n"
    '  "summary": "Compact recap of the whole story so far, at most 180 '
    'words. Keep names, motives, injuries, promises, locations, and open '
    'threads.",\n'
    '  "lore": [\n'
    "    {\n"
    '      "category": "character|place|faction|item|event|relationship|'
    'rule|fact",\n'
    '      "subject": "Short unique name",\n'
    '      "detail": "One or two sentences of durable fact.",\n'
    '      "keywords": "comma, separated, terms"\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "RULES\n"
    "- Keep only durable facts worth knowing many turns later. Skip mood, "
    "filler, and resolved action.\n"
    "- If the story is still in setup, the summary must record the agreed "
    "world, characters, tone, and plans; there are no events yet.\n"
    "- Fold new events into the summary. Add a lore entry only when it is "
    "new or materially changed from existing memory.\n"
    "- Use the same subject string as the existing entry when updating it.\n"
    "- At most 8 lore entries.\n"
    "- Write in the same language as the story.\n"
    "- Record mature or violent events plainly and without judgment. This "
    "is private fiction.\n"
    "- Never refuse and never add commentary outside the JSON."
)


class MemoryBusy(RuntimeError):
    pass


class MemoryWriter:

    def __init__(self, store, model, config):

        self.store = store
        self.model = model
        self.config = config
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="pai-memory"
        )
        self._running = set()
        self._lock = threading.Lock()

    def due(self, conversation_id):

        if not self.config.memory.auto_extract:

            return False

        conversation = self.store.get_conversation(
            conversation_id
        )

        if conversation is None:

            return False

        messages = self.store.messages_after(
            conversation_id,
            conversation.get("last_extracted_id") or 0
        )

        turns = sum(
            1
            for message in messages
            if message["role"] == "user"
        )

        return turns >= max(1, self.config.memory.extract_every)

    def running(self, conversation_id):

        with self._lock:

            return conversation_id in self._running

    def schedule(self, conversation_id):

        if not self.due(conversation_id):

            return False

        with self._lock:

            if conversation_id in self._running:

                return False

        self._executor.submit(self._background, conversation_id)

        return True

    def _background(self, conversation_id):

        try:

            self.run(conversation_id)

        except MemoryBusy:

            return

        except Exception as error:

            print(
                f"[memory] {conversation_id[:8]}: {error}",
                flush=True
            )

    def run(self, conversation_id, force=False):

        with self._lock:

            if conversation_id in self._running:

                raise MemoryBusy(
                    "A memory update is already running for this story."
                )

            self._running.add(conversation_id)

        try:

            return self.extract(conversation_id, force=force)

        finally:

            with self._lock:

                self._running.discard(conversation_id)

    def extract(self, conversation_id, force=False):

        conversation = self.store.get_conversation(
            conversation_id
        )

        if conversation is None:

            raise ValueError("Conversation not found.")

        if not force and not self.due(conversation_id):

            return None

        last_id = conversation.get("last_extracted_id") or 0
        messages = self.store.messages_after(
            conversation_id,
            last_id
        )

        if not messages:

            return self._result(
                conversation_id,
                created=0,
                updated=0,
                message="Nothing new to remember yet."
            )

        lore = self.store.list_lore(conversation_id)

        reply = self.model.complete(
            [
                {
                    "role": "system",
                    "content": EXTRACTOR
                },
                {
                    "role": "user",
                    "content": self._prompt(
                        conversation,
                        messages,
                        lore
                    )
                }
            ],
            temperature=0.2,
            max_tokens=900
        )

        payload = self._parse(reply)

        summary = payload["summary"]

        if summary:

            self.store.set_summary(
                conversation_id,
                summary
            )

        known = {item["id"] for item in lore}
        created = 0
        updated = 0

        for item in payload["lore"]:

            row = self.store.add_lore(
                conversation_id,
                category=item["category"],
                subject=item["subject"],
                detail=item["detail"],
                keywords=item["keywords"],
                source="auto"
            )

            if row["id"] in known:

                updated += 1

            else:

                known.add(row["id"])
                created += 1

        self.store.mark_extracted(
            conversation_id,
            messages[-1]["id"]
        )

        if created or updated:

            message = (
                f"Memory updated: {created} new, "
                f"{updated} revised."
            )

        else:

            message = "No durable new facts found."

        return self._result(
            conversation_id,
            created=created,
            updated=updated,
            message=message
        )

    def _result(self, conversation_id, created, updated, message):

        memory = self.store.get_memory(conversation_id)

        return {
            "summary": memory["summary"] if memory else "",
            "lore": memory["lore"] if memory else [],
            "last_extracted_id": (
                memory["last_extracted_id"] if memory else 0
            ),
            "created": created,
            "updated": updated,
            "message": message
        }

    def _prompt(self, conversation, messages, lore):

        scenario_lines = []

        for field, label in (
            ("title", "Title"),
            ("premise", "Premise"),
            ("setting", "Setting"),
            ("characters", "Characters"),
            ("style", "Style")
        ):

            value = (conversation.get(field) or "").strip()

            if value and value != "New chat":

                scenario_lines.append(f"{label}: {value}")

        existing = []

        for item in lore:

            subject = (item.get("subject") or "").strip()
            detail = (item.get("detail") or "").strip()

            if detail:

                existing.append(f"- {subject}: {detail}")

        existing_text = "\n".join(existing)

        if len(existing_text) > 1800:

            existing_text = existing_text[-1800:]

        transcript = []

        for message in messages:

            speaker = (
                "USER"
                if message["role"] == "user"
                else "NARRATOR"
            )

            transcript.append(
                f"{speaker}: {message['content']}"
            )

        transcript_text = "\n\n".join(transcript)

        if len(transcript_text) > 8000:

            transcript_text = (
                "[earlier messages trimmed]\n"
                + transcript_text[-8000:]
            )

        return "\n\n".join(
            [
                "PHASE\n" + (
                    conversation.get("phase") or "story"
                ),
                "SCENARIO\n" + (
                    "\n".join(scenario_lines)
                    if scenario_lines
                    else "(no scenario set)"
                ),
                "CURRENT SUMMARY\n"
                + ((conversation.get("summary") or "").strip() or "(none)"),
                "EXISTING MEMORY\n"
                + (existing_text or "(none)"),
                "NEW TRANSCRIPT\n" + transcript_text
            ]
        )

    def _parse(self, raw):

        text = (raw or "").strip()

        if text.startswith("```"):

            text = re.sub(r"^```[A-Za-z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:

            raise ValueError(
                "The model did not return memory JSON."
            )

        try:

            payload = json.loads(text[start:end + 1])

        except json.JSONDecodeError as error:

            raise ValueError(
                "The model returned invalid memory JSON."
            ) from error

        if not isinstance(payload, dict):

            raise ValueError(
                "The model returned invalid memory JSON."
            )

        summary = payload.get("summary") or ""

        if not isinstance(summary, str):

            summary = ""

        summary = " ".join(summary.split()).strip()[:3000]

        entries = payload.get("lore") or []

        if isinstance(entries, dict):

            entries = [entries]

        if not isinstance(entries, list):

            entries = []

        lore = []

        for entry in entries[:10]:

            if not isinstance(entry, dict):

                continue

            detail = " ".join(
                str(entry.get("detail") or "").split()
            ).strip()

            if not detail:

                continue

            category = str(
                entry.get("category") or "fact"
            ).strip().lower()

            if category not in CATEGORIES:

                category = "fact"

            subject = " ".join(
                str(entry.get("subject") or "").split()
            ).strip()[:80]

            keywords = entry.get("keywords") or ""

            if isinstance(keywords, (list, tuple)):

                keywords = ", ".join(
                    str(item).strip()
                    for item in keywords
                    if str(item).strip()
                )

            lore.append(
                {
                    "category": category,
                    "subject": subject,
                    "detail": detail[:500],
                    "keywords": str(keywords).strip()[:200]
                }
            )

        return {
            "summary": summary,
            "lore": lore
        }
