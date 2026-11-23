import json
import os
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from features.intent_model import IntentModel


class IntentModelTests(unittest.TestCase):

    def test_default_backend_uses_corpus_without_loading_deberta(self):
        examples = [
            {"text": "start a new story", "intent": "begin_story"},
            {"text": "pause the story", "intent": "pause"}
        ]

        with TemporaryDirectory() as temp:
            data_dir = Path(temp) / "intents"
            data_dir.mkdir()
            for name in ("train", "validation"):
                (data_dir / f"{name}.json").write_text(
                    json.dumps(examples),
                    encoding="utf-8"
                )

            with patch.dict(os.environ, {"PAI_INTENT_BACKEND": ""}):
                model = IntentModel(
                    model_dir=Path(temp) / "missing-model",
                    data_dir=data_dir
                )

            result = model.classify("start a new story")

        self.assertEqual(model.requested_backend, "corpus")
        self.assertEqual(model.backend, "corpus")
        self.assertFalse(model._deberta_ready)
        self.assertEqual(result.label, "begin_story")

    def test_validation_examples_are_not_used_to_fit_the_classifier(self):
        train = [
            {"text": "hello there", "intent": "chat"},
            {"text": "what is photosynthesis", "intent": "question"}
        ]
        validation = [
            {"text": "debug this Luau script", "intent": "coding"}
        ]

        with TemporaryDirectory() as temp:
            data_dir = Path(temp) / "intents"
            data_dir.mkdir()
            (data_dir / "train.json").write_text(
                json.dumps(train),
                encoding="utf-8"
            )
            (data_dir / "validation.json").write_text(
                json.dumps(validation),
                encoding="utf-8"
            )
            model = IntentModel(
                model_dir=Path(temp) / "missing-model",
                data_dir=data_dir
            )

            model.warm()

        self.assertEqual(set(model.labels), {"chat", "question"})


if __name__ == "__main__":
    unittest.main()
