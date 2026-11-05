from models.entity_model import EntityRecognizer


recognizer = EntityRecognizer()

text = (
    "There is a character named, Solas. "
    "He is a soldier on a kingdom named, Rinestarg, "
    "a very rich and strong kingdom."
)

entities = recognizer.recognize(text)

print("\n--- Detected Entities ---")

for entity in entities:
    print(
        f"Text: {entity['text']} | "
        f"Type: {entity['label']} | "
        f"Confidence: {entity['confidence']:.2f}"
    )

print("-------------------------")