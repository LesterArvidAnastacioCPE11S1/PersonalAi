import json
from pathlib import Path


class IntentDataset:

    def __init__(self, train_path, validation_path):

        self.train_path = Path(train_path)
        self.validation_path = Path(validation_path)

        self.train_data = []
        self.validation_data = []

        self.intents = []
        self.intent_to_id = {}
        self.id_to_intent = {}

    def load(self):

        self.train_data = self._load_file(self.train_path)
        self.validation_data = self._load_file(self.validation_path)

        self._find_intents()
        self._create_label_mapping()

    def _load_file(self, path):

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {path}"
            )

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(
                f"Dataset must contain a JSON list: {path}"
            )

        for item in data:

            if "text" not in item:
                raise ValueError(
                    f"Missing 'text' field: {item}"
                )

            if "intent" not in item:
                raise ValueError(
                    f"Missing 'intent' field: {item}"
                )

        return data

    def _find_intents(self):

        intents = set()

        for item in self.train_data:
            intents.add(item["intent"])

        for item in self.validation_data:
            intents.add(item["intent"])

        self.intents = sorted(intents)

    def _create_label_mapping(self):

        self.intent_to_id = {
            intent: index
            for index, intent in enumerate(self.intents)
        }

        self.id_to_intent = {
            index: intent
            for intent, index in self.intent_to_id.items()
        }

    def get_train_data(self):
        return self.train_data

    def get_validation_data(self):
        return self.validation_data

    def get_intents(self):
        return self.intents

    def get_intent_to_id(self):
        return self.intent_to_id

    def get_id_to_intent(self):
        return self.id_to_intent