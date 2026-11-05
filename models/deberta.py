import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from core.context import Context, ContextAnalyzer


class DebertaAnalyzer(ContextAnalyzer):

    def __init__(self):

        self.model_path = "models/deberta_intent"

        print("Loading trained DeBERTa classifier...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_path
        )

        self.model.eval()
        self.model.float()

        print("Trained DeBERTa classifier loaded.")

    def analyze(self, message, conversation_history):

        inputs = self.tokenizer(
            message,
            return_tensors="pt",
            truncation=True,
            max_length=128
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )

        confidence, predicted_id = torch.max(
            probabilities,
            dim=-1
        )

        predicted_id = predicted_id.item()
        confidence = confidence.item()

        intent = self.model.config.id2label[predicted_id]

        return Context(
            intent=intent,
            confidence=confidence,
            additional_data={
                "predicted_id": predicted_id,
                "message": message,
                "history": conversation_history
            }
        )