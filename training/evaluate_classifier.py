import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)

from training.dataset import IntentDataset


MODEL_PATH = "models/deberta_intent"

TRAIN_PATH = "data/intents/train.json"
VALIDATION_PATH = "data/intents/validation.json"


def predict(model, tokenizer, text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(
        outputs.logits,
        dim=-1
    )

    predicted_id = torch.argmax(
        probabilities,
        dim=-1
    ).item()

    confidence = probabilities[0][predicted_id].item()

    return predicted_id, confidence


def main():

    print()
    print("==============================")
    print("Loading evaluation data...")
    print("==============================")
    print()

    dataset = IntentDataset(
        TRAIN_PATH,
        VALIDATION_PATH
    )

    dataset.load()

    validation_data = dataset.get_validation_data()
    id_to_intent = dataset.get_id_to_intent()

    print(f"Validation examples: {len(validation_data)}")
    print()

    # -----------------------------
    # Load trained model
    # -----------------------------

    print("Loading trained DeBERTa model...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_PATH
    )

    model.eval()

    print("Model loaded.")
    print()

    # -----------------------------
    # Evaluate
    # -----------------------------

    correct = 0
    total = len(validation_data)

    intent_results = {}

    print("==============================")
    print("Evaluating classifier...")
    print("==============================")
    print()

    for item in validation_data:

        text = item["text"]
        actual_intent = item["intent"]

        predicted_id, confidence = predict(
            model,
            tokenizer,
            text
        )

        predicted_intent = id_to_intent[predicted_id]

        if predicted_intent == actual_intent:
            correct += 1

        # Track results by intent

        if actual_intent not in intent_results:
            intent_results[actual_intent] = {
                "correct": 0,
                "total": 0
            }

        intent_results[actual_intent]["total"] += 1

        if predicted_intent == actual_intent:
            intent_results[actual_intent]["correct"] += 1

        print(f"Text: {text}")
        print(f"Actual:    {actual_intent}")
        print(f"Predicted: {predicted_intent}")
        print(f"Confidence: {confidence:.4f}")

        if predicted_intent == actual_intent:
            print("Result: CORRECT")
        else:
            print("Result: WRONG")

        print("------------------------------")

    # -----------------------------
    # Overall accuracy
    # -----------------------------

    accuracy = correct / total

    print()
    print("==============================")
    print("Overall Results")
    print("==============================")
    print()

    print(f"Correct: {correct}/{total}")
    print(f"Accuracy: {accuracy:.2%}")

    # -----------------------------
    # Per-intent accuracy
    # -----------------------------

    print()
    print("==============================")
    print("Accuracy by Intent")
    print("==============================")
    print()

    for intent in sorted(intent_results):

        result = intent_results[intent]

        intent_accuracy = (
            result["correct"] / result["total"]
        )

        print(
            f"{intent}: "
            f"{result['correct']}/{result['total']} "
            f"({intent_accuracy:.2%})"
        )

    print()


if __name__ == "__main__":
    main()