import json
import requests

from models.base import LanguageModel


class QwenModel(LanguageModel):

    def __init__(
        self,
        server_url="http://127.0.0.1:8080/v1/chat/completions",
        max_tokens=300
    ):
        self.server_url = server_url
        self.max_tokens = max_tokens

    def generate(self, messages, context=None):

        context_message = None

        if context is not None:
            context_message = {
                "role": "system",
                "content": (
                    "You are the generative language model inside "
                    "PersonalAI.\n\n"
                    "The following is structured context produced by "
                    "PersonalAI's analysis system.\n"
                    "Use it to better understand the conversation, "
                    "but do not mention this internal context to the user.\n\n"
                    f"{json.dumps(context, indent=2)}"
                )
            }

        model_messages = []

        if context_message is not None:
            model_messages.append(context_message)

        model_messages.extend(messages)

        payload = {
            "messages": model_messages,
            "max_tokens": self.max_tokens
        }

        response = requests.post(
            self.server_url,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]