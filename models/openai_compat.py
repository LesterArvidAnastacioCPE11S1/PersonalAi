import json

import re

import requests


# Signals that a request is Roblox or Luau coding work, where the big
# context model is useful. A false positive only costs performance, so
# the list leans inclusive.

CODING_SIGNALS = re.compile(
    r"\[roblox file:"
    r"|\bluau\b"
    r"|\broblox\b"
    r"|\brbx[ml]\w*\b"
    r"|\bscripts?\b"
    r"|\bscripting\b"
    r"|\bcoding\b"
    r"|\bcodeword\b"
    r"|\bserverscriptservice\b"
    r"|\bstarterplayer\w*\b"
    r"|\bstartergui\b"
    r"|\bstarterpack\b"
    r"|\breplicatedstorage\b"
    r"|\blocalscripts?\b"
    r"|\bmodulescripts?\b"
    r"|\bremoteevents?\b"
    r"|\bremotefunctions?\b"
    r"|\bdatastores?\b"
    r"|\buserinputservice\b"
    r"|\btweenservice\b"
    r"|\brunservic\w+\b"
    r"|\bpathfindingservice\b"
    r"|\bcontextactionservice\b"
    r"|\binstance\.new\b"
    r"|\bcframe\.new\b"
    r"|\bvector3\.new\b"
    r"|\bvector2\.new\b"
    r"|\btask\.wait\b"
    r"|\btask\.spawn\b"
    r"|\bfindfirstchild\b"
    r"|\bwaitforchild\b"
    r"|\bgame\.players\b"
    r"|\bworkspace\b",
    re.IGNORECASE
)


class ModelError(RuntimeError):
    pass


class OpenAICompatibleModel:

    def __init__(self, config):

        self.config = config
        self._resolved_model = config.model

    def _has_images(self, messages):

        for message in messages or []:

            content = message.get("content")

            if not isinstance(content, list):

                continue

            for part in content:

                if (
                    isinstance(part, dict)
                    and part.get("type") == "image_url"
                ):

                    return True

        return False

    def _has_coding_signals(self, messages):

        for message in messages or []:

            content = message.get("content")

            if isinstance(content, list):

                content = " ".join(
                    part.get("text") or ""
                    for part in content
                    if isinstance(part, dict)
                )

            if not isinstance(content, str):

                continue

            if CODING_SIGNALS.search(content):

                return True

        return False

    def _model_id(self, messages=None):

        if (
            messages
            and self.config.vision
            and self.config.vision_model
            and self._has_images(messages)
        ):

            return self.config.vision_model

        if self._big_context_for(messages):

            return self.config.big_context_model

        if self._resolved_model:

            return self._resolved_model

        try:

            models = self.available_models(timeout=3)

        except ModelError:

            return ""

        if models:

            self._resolved_model = models[0]

        return self._resolved_model

    def _has_attachments(self, messages):

        for message in messages or []:

            content = message.get("content")

            if isinstance(content, list):

                content = " ".join(
                    part.get("text") or ""
                    for part in content
                    if isinstance(part, dict)
                )

            if not isinstance(content, str):

                continue

            if "[Attached files]" in content:

                return True

        return False

    def _big_context_for(self, messages):

        if not self.config.big_context_model:

            return False

        if not getattr(self.config, "auto_big_context", True):

            return False

        if (
            self.config.big_context_model
            == self._resolved_model
        ):

            # Already the active model.

            return False

        return (
            self._has_coding_signals(messages)
            or self._has_attachments(messages)
        )

    def _url(self, path):

        return self.config.base_url.rstrip("/") + path

    def _headers(self):

        headers = {
            "Content-Type": "application/json"
        }

        if self.config.api_key:

            headers["Authorization"] = (
                f"Bearer {self.config.api_key}"
            )

        return headers

    def _connection_message(self):

        return (
            f"Cannot reach the model server at "
            f"{self.config.base_url}. Start your local model server "
            "(Ollama, LM Studio, or another OpenAI-compatible "
            "endpoint), or change the endpoint in Settings."
        )

    def refresh(self):

        self._resolved_model = self.config.model

    def available_models(self, timeout=3):

        try:

            response = requests.get(
                self._url("/models"),
                headers=self._headers(),
                timeout=timeout
            )

            response.raise_for_status()

        except requests.RequestException as error:

            raise ModelError(
                self._connection_message()
            ) from error

        response.encoding = "utf-8"

        payload = response.json()

        return [
            item.get("id")
            for item in payload.get("data", [])
            if item.get("id")
        ]

    def _payload(
        self,
        messages,
        stream,
        temperature,
        max_tokens
    ):

        payload = {
            "messages": messages,
            "stream": stream,
            "temperature": (
                self.config.temperature
                if temperature is None
                else temperature
            ),
            "top_p": self.config.top_p,
            "max_tokens": (
                self.config.max_tokens
                if max_tokens is None
                else max_tokens
            )
        }

        model_id = self._model_id(messages)

        if model_id:

            payload["model"] = model_id

        prompt_chars = 0

        for message in messages or []:

            content = message.get("content")

            if isinstance(content, str):
                prompt_chars += len(content)

            else:
                prompt_chars += len(str(content))

        print(
            f"[model] {model_id or '(server default)'} | "
            f"prompt {prompt_chars} chars"
        )

        return payload

    def stream(
        self,
        messages,
        temperature=None,
        max_tokens=None
    ):

        stream = self.config.stream

        try:

            response = requests.post(
                self._url("/chat/completions"),
                headers=self._headers(),
                json=self._payload(
                    messages,
                    stream,
                    temperature,
                    max_tokens
                ),
                stream=stream,
                timeout=(10, self.config.timeout)
            )

            response.raise_for_status()

        except requests.RequestException as error:

            raise ModelError(
                self._connection_message()
            ) from error

        response.encoding = "utf-8"

        if not stream:

            payload = response.json()

            yield self._content_from(payload)

            return

        with response:

            for raw_line in response.iter_lines(
                decode_unicode=False
            ):

                if not raw_line:

                    continue

                line = raw_line.decode(
                    "utf-8",
                    errors="replace"
                )

                if not line.startswith("data:"):

                    continue

                data = line[5:].strip()

                if not data:

                    continue

                if data == "[DONE]":

                    break

                try:

                    payload = json.loads(data)

                except json.JSONDecodeError:

                    continue

                if payload.get("error"):

                    raise ModelError(
                        str(payload["error"])
                    )

                content = self._content_from(
                    payload,
                    partial=True
                )

                if content:

                    yield content

    def complete(
        self,
        messages,
        temperature=None,
        max_tokens=None
    ):

        try:

            response = requests.post(
                self._url("/chat/completions"),
                headers=self._headers(),
                json=self._payload(
                    messages,
                    False,
                    temperature,
                    max_tokens
                ),
                timeout=(10, self.config.timeout)
            )

            response.raise_for_status()

        except requests.RequestException as error:

            raise ModelError(
                self._connection_message()
            ) from error

        response.encoding = "utf-8"

        try:

            payload = response.json()

        except ValueError as error:

            raise ModelError(
                "The model server returned an unreadable response."
            ) from error

        if payload.get("error"):

            raise ModelError(str(payload["error"]))

        return self._content_from(payload)

    def _content_from(self, payload, partial=False):

        choices = payload.get("choices") or []

        if not choices:

            return ""

        choice = choices[0]

        if partial and "delta" in choice:

            return choice["delta"].get("content") or ""

        message = choice.get("message") or {}

        return message.get("content") or ""
