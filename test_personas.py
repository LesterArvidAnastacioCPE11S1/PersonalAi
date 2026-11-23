import sqlite3
import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace

from core.engine import ChatEngine
from core.persona import (
    DEFAULT_ASSISTANT_PERSONA_ID,
    DEFAULT_CODING_PERSONA_ID
)
from core.store import Store


class PersonaTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "personal_ai.db"
        self.store = Store(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_assistant_is_the_default_and_coding_persona_is_available(self):
        default = self.store.default_persona()
        coding = self.store.get_persona(DEFAULT_CODING_PERSONA_ID)

        self.assertEqual(default["id"], DEFAULT_ASSISTANT_PERSONA_ID)
        self.assertEqual(default["name"], "AI Assistant")
        self.assertEqual(coding["name"], "Coding assistant")
        self.assertIn("not as requests for generic advice", coding["instructions"])

    def test_chat_prompt_uses_general_assistant_by_default(self):
        conversation = self.store.create_conversation()

        prompt = ChatEngine(self.config, self.store, None)._assemble(
            conversation,
            [],
            "What can you help me with?",
            ""
        )

        self.assertIn("default general-purpose assistant", prompt[0]["content"])
        self.assertNotIn(
            "narrator inside the user's private fiction",
            prompt[0]["content"]
        )

    def test_upgrade_moves_existing_chat_to_assistant_but_preserves_story(self):
        chat = self.store.create_conversation(persona_id="default")
        story = self.store.create_conversation(persona_id="default")
        self.store.set_phase(story["id"], "story")

        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                "DELETE FROM personas WHERE id IN (?, ?)",
                (
                    DEFAULT_ASSISTANT_PERSONA_ID,
                    DEFAULT_CODING_PERSONA_ID
                )
            )
            connection.commit()
        finally:
            connection.close()

        upgraded = Store(self.db_path)

        self.assertEqual(
            upgraded.get_conversation(chat["id"])["persona_id"],
            DEFAULT_ASSISTANT_PERSONA_ID
        )
        self.assertEqual(
            upgraded.get_conversation(story["id"])["persona_id"],
            "default"
        )

    def test_story_uses_the_selected_story_persona(self):
        custom = self.store.create_persona(
            "Mystery narrator",
            "Narrate as a restrained mystery writer."
        )
        conversation = self.store.create_conversation(
            persona_id=custom["id"]
        )
        conversation = self.store.set_phase(
            conversation["id"],
            "story"
        )

        prompt = ChatEngine(self.config, self.store, None)._assemble(
            conversation,
            [],
            "Continue the story.",
            ""
        )

        self.assertIn("restrained mystery writer", prompt[0]["content"])
        self.assertNotIn("default general-purpose assistant", prompt[0]["content"])

    def test_story_uses_unfiltered_persona_when_assistant_is_selected(self):
        conversation = self.store.create_conversation()
        conversation = self.store.set_phase(
            conversation["id"],
            "story"
        )

        prompt = ChatEngine(self.config, self.store, None)._assemble(
            conversation,
            [],
            "Continue the story.",
            ""
        )

        self.assertIn(
            "The characters go along with the premise",
            prompt[0]["content"]
        )
        self.assertNotIn(
            "default general-purpose assistant",
            prompt[0]["content"]
        )

    def test_coding_turn_temporarily_switches_out_of_story_mode(self):
        conversation = self.store.create_conversation(
            persona_id="default"
        )
        conversation = self.store.set_phase(
            conversation["id"],
            "story"
        )

        prompt = ChatEngine(self.config, self.store, None)._assemble(
            conversation,
            [],
            "Fix this Luau script.",
            "",
            assistant_mode="coding"
        )

        self.assertIn("default coding assistant", prompt[0]["content"])
        self.assertIn("private general-purpose assistant", prompt[0]["content"])
        self.assertNotIn("narrator inside the user's private fiction", prompt[0]["content"])
        self.assertEqual(conversation["phase"], "story")

    @property
    def config(self):
        return SimpleNamespace(
            behavior=SimpleNamespace(
                custom_instructions="",
                no_refusals=False
            ),
            tools=SimpleNamespace(enabled=False),
            context=SimpleNamespace(max_messages=20, max_chars=5000),
            memory=SimpleNamespace(max_lore_chars=5000)
        )


if __name__ == "__main__":
    unittest.main()
