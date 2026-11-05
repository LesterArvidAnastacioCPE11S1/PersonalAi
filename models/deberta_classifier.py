from transformers import AutoModelForSequenceClassification


class DebertaIntentClassifier:

    def __init__(self, model_name, num_labels):

        print("Loading DeBERTa classification model...")

        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        )

        print("DeBERTa classification model loaded.")

    def get_model(self):
        return self.model