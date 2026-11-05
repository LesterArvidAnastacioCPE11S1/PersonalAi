import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


MODEL_PATH = "models/deberta_intent"


def predict(model, tokenizer, text, id_to_intent):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    print("Logits:", outputs.logits)
    print("Contains NaN:", torch.isnan(outputs.logits).any().item())
    print("Contains Inf:", torch.isinf(outputs.logits).any().item())

    probabilities = torch.softmax(outputs.logits, dim=-1)

    predicted_id = torch.argmax(probabilities, dim=-1).item()
    confidence = probabilities[0][predicted_id].item()

    predicted_intent = id_to_intent[predicted_id]

    return predicted_intent, confidence

def main():

    print("Loading trained DeBERTa classifier...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_PATH
    )

    model.eval()

    id_to_intent = {
        int(key): value
        for key, value in model.config.id2label.items()
    }

    print("Model loaded.")
    print()

    test_messages = [
        "Can you explain what a black hole is?",
        "Write me a fantasy story about a wandering knight.",
        "Let's roleplay as two adventurers entering a mysterious city.",
        "Continue the story from where we left off.",
        "Please remember that my favorite color is green.",
        "Can you summarize this paragraph for me?",
        "How do I create a Python class?",
        "What is the capital of France?"
    ]

    for message in test_messages:

        intent, confidence = predict(
            model,
            tokenizer,
            message,
            id_to_intent
        )

        print(f"Input: {message}")
        print(f"Intent: {intent}")
        print(f"Confidence: {confidence:.4f}")
        print()


if __name__ == "__main__":
    main()