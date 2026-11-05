from transformers import pipeline
from typing import Any

class EntityRecognizer:

    def __init__(self):

        ner_pipeline: Any = pipeline

        self.ner = ner_pipeline(
            "ner",
            model="dslim/bert-base-NER",
            aggregation_strategy="simple"
        )

    def recognize(self, text):

        if not text:
            return []

        results = self.ner(text)

        entities = []

        for result in results:

            entity_text = result["word"]

            entities.append({
                "text": entity_text,
                "label": result["entity_group"],
                "confidence": float(result["score"]),
                "start": result["start"],
                "end": result["end"]
            })

        return entities