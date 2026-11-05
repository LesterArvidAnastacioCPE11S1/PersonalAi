from transformers import AutoTokenizer
from training.dataset import IntentDataset


class IntentTokenizer:

    def __init__(self, model_name="microsoft/deberta-v3-base"):

        print("Loading DeBERTa tokenizer...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name
        )

        print("Tokenizer loaded.")

    def tokenize_text(self, text):

        return self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128
        )

    def tokenize_dataset(self, data, intent_to_id):

        tokenized_data = []

        for item in data:

            encoded = self.tokenize_text(item["text"])

            encoded["label"] = intent_to_id[item["intent"]]

            tokenized_data.append(encoded)

        return tokenized_data