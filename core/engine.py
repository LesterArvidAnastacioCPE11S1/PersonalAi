from core.persona import PersonaBuilder
from features.story_setup import has_story_brief


class ChatEngine:

    def __init__(self, config, store, model):

        self.config = config
        self.store = store
        self.model = model
        self.persona = PersonaBuilder(config)

    def prepare(
        self,
        conversation,
        message,
        prompt_content=None,
        attachment_ids=None,
        image_urls=None,
        intents=None
    ):

        history = self.store.get_messages(
            conversation["id"],
            include_prompt=True
        )

        prompt = self._assemble(
            conversation,
            history,
            message,
            prompt_content,
            image_urls or [],
            intents
        )

        saved = self.store.add_message(
            conversation["id"],
            "user",
            message,
            prompt_content
        )

        if attachment_ids:

            self.store.link_attachments(
                attachment_ids,
                saved["id"]
            )

        self.store.auto_title(
            conversation["id"],
            message
        )

        return (
            self.store.get_conversation(
                conversation["id"]
            ),
            prompt
        )

    def _assemble(
        self,
        conversation,
        history,
        message,
        prompt_content,
        image_urls,
        intents=None
    ):

        lore = self.store.list_lore(
            conversation["id"]
        )

        setup_round, brief_presented = self._setup_state(
            history
        )

        prompt = [
            {
                "role": "system",
                "content": self.persona.build(
                    conversation,
                    lore=lore,
                    summary=conversation.get("summary") or "",
                    phase=conversation.get("phase"),
                    setup_round=setup_round,
                    brief_presented=brief_presented,
                    intents=intents
                )
            }
        ]

        prompt.extend(
            self._window(
                history,
                conversation.get("phase")
            )
        )

        content = prompt_content or message

        if image_urls:

            parts = [{"type": "text", "text": content}]
            parts.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": url}
                }
                for url in image_urls
            )

            prompt.append(
                {
                    "role": "user",
                    "content": parts
                }
            )

        else:

            prompt.append(
                {
                    "role": "user",
                    "content": content
                }
            )

        return prompt

    def _setup_state(self, history):

        assistant = [
            item for item in history
            if item.get("role") == "assistant"
        ]

        brief_presented = any(
            has_story_brief(item.get("content") or "")
            for item in assistant
        )

        return len(assistant) + 1, brief_presented

    def _window(self, history, phase=None):

        max_messages = self.config.context.max_messages
        max_chars = self.config.context.max_chars

        messages = history[-max_messages:]

        if phase == "setup":

            messages = [
                self._setup_history(item)
                for item in messages
            ]

        total = sum(
            len(self._text(item))
            for item in messages
        )

        while len(messages) > 1 and total > max_chars:

            removed = messages.pop(0)

            total -= len(self._text(removed))

        return [
            {
                "role": item["role"],
                "content": self._text(item)
            }
            for item in messages
        ]

    def _setup_history(self, item):

        if item.get("role") != "assistant":

            return item

        text = self._text(item).strip()

        if not text or "story brief" in text.lower():

            return item

        questions = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and "?" in line
        ]

        content = (
            "\n".join(questions)
            if questions
            else "(earlier setup reply had no questions)"
        )

        return {
            "role": "assistant",
            "content": content,
            "prompt_content": ""
        }

    def _text(self, item):

        return item.get("prompt_content") or item["content"]

    def stream(self, conversation, prompt):

        parts = []

        try:

            for chunk in self.model.stream(prompt):

                parts.append(chunk)

                yield chunk

        finally:

            content = "".join(parts).strip()

            if content:

                self.store.add_message(
                    conversation["id"],
                    "assistant",
                    content
                )
