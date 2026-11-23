import unittest

from features.intents import assistant_mode_for, is_coding_request
from features.intent_model import Turn


class IntentModeTests(unittest.TestCase):

    def test_existing_code_edit_request_overrides_ambiguous_classifier_result(self):
        turn = Turn(
            "begin_story",
            0.287,
            {"begin_story": 0.287, "coding": 0.248}
        )

        self.assertEqual(
            assistant_mode_for(
                "I already have those; edit the codes we currently have "
                "to further improve it.",
                turn,
                project_active=True
            ),
            "coding"
        )

    def test_story_language_stays_in_story_mode(self):
        turn = Turn("roleplay", 0.85, {"roleplay": 0.85})

        self.assertFalse(
            is_coding_request(
                "My character writes a code on the wall and keeps walking.",
                turn,
                phase="story"
            )
        )
        self.assertEqual(
            assistant_mode_for(
                "My character writes a code on the wall and keeps walking.",
                turn,
                phase="story"
            ),
            "story"
        )

    def test_follow_up_after_code_recommendation_keeps_coding_mode(self):
        self.assertEqual(
            assistant_mode_for(
                "go ahead",
                history=[
                    {
                        "role": "assistant",
                        "content": (
                            "I recommend refactoring the Luau movement "
                            "script."
                        )
                    }
                ]
            ),
            "coding"
        )

    def test_story_request_about_programming_stays_story_mode(self):
        turn = Turn("storytelling", 0.9, {"storytelling": 0.9})

        self.assertEqual(
            assistant_mode_for(
                "Write a story about a programmer debugging a strange machine.",
                turn,
                phase="story"
            ),
            "story"
        )

    def test_normal_chat_keeps_general_assistant_mode(self):
        self.assertEqual(
            assistant_mode_for("Hey, how are you?"),
            "assistant"
        )


if __name__ == "__main__":
    unittest.main()
