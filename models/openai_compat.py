import json

import requests


class ModelError(RuntimeError):
    pass


class OpenAICompatibleModel:

    def __init__(self, config):

        self.config = config
        self._resolved_model = config.model

    def _model_id(self):

        if self._resolved_model:

            return self._resolved_model

        try:

            models = self.available_models(timeout=3)

        except ModelError:

            return ""

        if models:

            self._resolved_model = models[0]

        return self._resolved_model

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

        model_id = self._model_id()

        if model_id:

            payload["model"] = model_id

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
