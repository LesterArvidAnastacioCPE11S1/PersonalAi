import json
import requests

from abc import ABC, abstractmethod
from typing import List

from core.semantic_types import SemanticStatement


class SemanticInterpreter(ABC):

    @abstractmethod
    def interpret(
        self,
        message: str,
        entities: list,
        conversation_history: list
    ) -> List[SemanticStatement]:

        pass


class QwenSemanticInterpreter(SemanticInterpreter):

    def __init__(
        self,
        server_url="http://127.0.0.1:8080/v1/chat/completions"
    ):

        self.server_url = server_url

    def interpret(
        self,
        message: str,
        entities: list,
        conversation_history: list
    ) -> List[SemanticStatement]:

        prompt = f"""
Analyze the meaning of the user's message.

Your task is to represent the semantic structure of the message.

Do not assume specific categories such as characters,
worlds, kingdoms, people, places, or objects.

Represent whatever meaning is actually expressed.

You must distinguish between factual statements and questions.

If the user expresses a fact or assertion, use:

type = "statement"

and provide:

subject
predicate
object
confidence

If the user asks a question, use:

type = "question"

and identify what information the question is asking about.

For a question, use null for the object when the
requested value is unknown.

Do not treat question words such as:
what, who, where, when, why, or how
as factual objects or values.

Examples:

User:
There is a world named Lunar

Output:
[
  {{
    "type": "statement",
    "subject": "world",
    "predicate": "has name",
    "object": "Lunar",
    "confidence": 0.95
  }}
]

User:
What is the world called?

Output:
[
  {{
    "type": "question",
    "subject": "world",
    "predicate": "has name",
    "object": null,
    "confidence": 0.95
  }}
]

User:
The capital of Lunar is Arcton.

Output:
[
  {{
    "type": "statement",
    "subject": "Lunar",
    "predicate": "has capital",
    "object": "Arcton",
    "confidence": 0.95
  }}
]

User:
What is the capital of Lunar?

Output:
[
  {{
    "type": "question",
    "subject": "Lunar",
    "predicate": "has capital",
    "object": null,
    "confidence": 0.95
  }}
]

Return ONLY a JSON array.

Each item must have exactly these fields:

type
subject
predicate
object
confidence

User message:
{message}
"""

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": prompt
                }
            ],
            "max_tokens": 500
        }

        response = requests.post(
            self.server_url,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        print("\n--- RAW QWEN RESPONSE ---")
        print(data)
        print("-------------------------\n")

        content = data["choices"][0]["message"]["content"]

        try:
            statements = json.loads(content)

        except json.JSONDecodeError:

            return []

        if not isinstance(statements, list):

            return []

        results = []

        for statement in statements:

            if not isinstance(statement, dict):

                continue

            if not all(
                key in statement
                for key in [
                    "type",
                    "subject",
                    "predicate",
                    "object",
                    "confidence"
                ]
            ):

                continue

            statement_type = str(
                statement["type"]
            ).lower().strip()

            if statement_type not in [
                "statement",
                "question"
            ]:

                continue

            object_value = statement["object"]

            if object_value is not None:

                object_value = str(
                    object_value
                )

            results.append(
                SemanticStatement(
                    subject=str(
                        statement["subject"]
                    ),

                    predicate=str(
                        statement["predicate"]
                    ),

                    object=object_value,

                    confidence=float(
                        statement["confidence"]
                    ),

                    type=statement_type
                )
            )

        return results


class EmptySemanticInterpreter(SemanticInterpreter):

    def interpret(
        self,
        message: str,
        entities: list,
        conversation_history: list
    ) -> List[SemanticStatement]:

        return []