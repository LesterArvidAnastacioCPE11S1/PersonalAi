import re


class MemoryExtractor:

    PREFIXES = [
        "remember that ",
        "remember ",
        "please remember that ",
        "please remember ",
        "save that ",
        "save ",
        "keep in mind that ",
        "keep in mind "
    ]

    def extract(self, message):

        if not message:
            return []

        text = message.strip()
        lowered = text.lower()

        for prefix in self.PREFIXES:

            if lowered.startswith(prefix):

                request = text[len(prefix):].strip()

                if request:
                    return [request]

                return []

        # If the message was classified as memory_save but
        # does not use one of the known prefixes, keep the
        # complete message as the memory request.
        return [text]


class ReferenceExtractor:

    REFERENCE_PHRASES = [
        "earlier",
        "before",
        "previously",
        "just now",
        "a moment ago",

        "what we talked about",
        "what i said",
        "what i mentioned",
        "what i told you",

        "what i said about",
        "what i mentioned about",
        "what i told you about",
        "what we said about",
        "what we talked about",

        "about my character",
        "about the character",
        "about my story",
        "about the story",

        "where we left off",
        "from where we left off",
        "continue from",
        "continue where",

        "that character",
        "my character",
        "the character i mentioned",
        "the character we talked about",

        "the story we were",
        "the story i mentioned",
        "the story we talked about"
    ]

    def extract(self, message):

        if not message:
            return []

        text = message.strip()
        lowered = text.lower()

        references = []

        for phrase in self.REFERENCE_PHRASES:

            if phrase in lowered:
                references.append(phrase)

        return references


class EntityExtractor:

    CHARACTER_PATTERNS = [
        r"\bcharacter named ([A-Z][a-zA-Z0-9_-]*)\b",
        r"\bcharacter is named ([A-Z][a-zA-Z0-9_-]*)\b",
        r"\bmy character named ([A-Z][a-zA-Z0-9_-]*)\b",
        r"\bmy character is ([A-Z][a-zA-Z0-9_-]*)\b"
    ]

    def extract(
        self,
        message,
        conversation_history=None
    ):

        if not message:
            return []

        if conversation_history is None:
            conversation_history = []

        entities = []

        # =========================================================
        # 1. EXTRACT NEW CHARACTER NAMES
        # =========================================================

        for pattern in self.CHARACTER_PATTERNS:

            matches = re.findall(
                pattern,
                message
            )

            for name in matches:

                entity = {
                    "name": name,
                    "entity_type": "character",
                    "confidence": 0.95
                }

                if entity not in entities:
                    entities.append(entity)

        # =========================================================
        # 2. FIND PREVIOUSLY KNOWN CHARACTER NAMES
        # =========================================================

        known_entities = []

        for history_message in conversation_history:

            content = history_message.get(
                "content",
                ""
            )

            if not content:
                continue

            for pattern in self.CHARACTER_PATTERNS:

                matches = re.findall(
                    pattern,
                    content
                )

                for name in matches:

                    if name not in known_entities:
                        known_entities.append(name)

        # =========================================================
        # 3. CHECK WHETHER KNOWN NAMES APPEAR IN CURRENT MESSAGE
        # =========================================================

        for name in known_entities:

            pattern = rf"\b{re.escape(name)}\b"

            if re.search(
                pattern,
                message,
                re.IGNORECASE
            ):

                entity = {
                    "name": name,
                    "entity_type": "character",
                    "confidence": 0.90
                }

                if entity not in entities:
                    entities.append(entity)

        return entities


class ReferenceResolver:

    STOP_WORDS = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "i",
        "me",
        "my",
        "we",
        "you",
        "your",
        "what",
        "did",
        "do",
        "does",
        "can",
        "could",
        "would",
        "should",
        "about",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "from",
        "that",
        "this",
        "it",
        "just",
        "say",
        "said",
        "mention",
        "mentioned",
        "tell",
        "told"
    }

    def _get_keywords(self, text):

        if not text:
            return []

        words = re.findall(
            r"\b[a-zA-Z0-9']+\b",
            text.lower()
        )

        keywords = []

        for word in words:

            if word in self.STOP_WORDS:
                continue

            if len(word) < 3:
                continue

            keywords.append(word)

        return keywords

    def _score_message(
        self,
        keywords,
        message,
        entities=None
    ):

        content = message.get(
            "content",
            ""
        )

        if not content:
            return 0

        content_lower = content.lower()

        message_words = set(
            self._get_keywords(content)
        )

        score = 0

        # =========================================================
        # 1. KEYWORD MATCHING
        # =========================================================

        for keyword in keywords:

            if keyword in message_words:
                score += 1

        # =========================================================
        # 2. ENTITY MATCHING
        # =========================================================

        if entities:

            for entity in entities:

                entity_name = entity.name.lower()

                if entity_name in content_lower:

                    # A known named entity is strong evidence
                    # that this message is relevant.
                    score += 10

        # =========================================================
        # 3. USER MESSAGE PRIORITY
        # =========================================================

        if message.get("role") == "user":

            # User statements contain the original information,
            # so prioritize them over assistant responses.
            score += 2

        return score

    def resolve(
        self,
        references,
        conversation_history,
        current_message="",
        entities=None
    ):

        # No history means there is nothing to retrieve.
        if not conversation_history:
            return []

        # =========================================================
        # IMPORTANT:
        # We allow retrieval when there are entities even if
        # there are no explicit reference phrases.
        #
        # Example:
        #
        # "Tell me about Rubert."
        #
        # This may not contain "earlier" or "my character",
        # but "Rubert" is still enough to search the history.
        # =========================================================

        if not references and not entities:
            return []

        keywords = self._get_keywords(
            current_message
        )

        scored_messages = []

        # =========================================================
        # SCORE EVERY MESSAGE IN CONVERSATION HISTORY
        # =========================================================

        for index, message in enumerate(
            conversation_history
        ):

            if not message.get("content"):
                continue

            score = self._score_message(
                keywords,
                message,
                entities
            )

            # Slightly prefer newer messages.
            recency_bonus = (
                index /
                max(len(conversation_history), 1)
            )

            score += recency_bonus

            scored_messages.append(
                (
                    score,
                    index,
                    message
                )
            )

        # =========================================================
        # SORT BY RELEVANCE
        # =========================================================

        scored_messages.sort(
            key=lambda item: (
                item[0],
                item[1]
            ),
            reverse=True
        )

        # =========================================================
        # KEEP ONLY ACTUALLY RELEVANT MESSAGES
        # =========================================================

        relevant_messages = [
            message
            for score, index, message
            in scored_messages
            if score > 0
        ]

        # Return at most the five most relevant messages.
        return relevant_messages[:5]