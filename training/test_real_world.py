import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


MODEL_PATH = "models/deberta_intent"


TEST_MESSAGES = [
    "Yo, what's up?",
    "I feel like talking for a bit.",
    "Hey, I'm bored. Let's chat.",

    "Why does my computer need RAM?",
    "What exactly does a motherboard do?",
    "Why does Wi-Fi sometimes slow down?",

    "Can you show me how to install Python?",
    "Walk me through setting up this program.",
    "What are the steps for configuring this?",

    "Can you write a Python program that reads a text file?",
    "My C++ code keeps crashing. Can you help me fix it?",
    "How would I implement a linked list?",

    "Tell me a story about a traveler who discovers a forgotten city.",
    "Make up a fantasy adventure for me.",
    "I'd like to hear a story about a mysterious island.",

    "Let's pretend I'm a knight entering an unknown kingdom.",
    "I want to play as a wizard in a fantasy world.",
    "Let's roleplay a conversation between a detective and a suspect.",

    "Continue from the scene we were just writing.",
    "What happens after the last chapter?",
    "Keep the story going from there.",

    "Write a dramatic description of an abandoned castle.",
    "Create a character who has a mysterious past.",
    "Write some dialogue between two rival characters.",

    "Remember that my character owns a small shop.",
    "Please save this information for later.",
    "Keep this detail in mind for future conversations.",

    "What was the name of my character again?",
    "Do you remember what I told you earlier?",
    "What information did I ask you to remember?",

    "Can you shorten this paragraph?",
    "Give me the main points of this text.",
    "Can you condense this into a few sentences?",

    "The toaster is negotiating with purple clouds.",
    "I don't really have anything to ask.",
    "Bananas are apparently running a space government.",
]


def main():

    print("Loading trained DeBERTa classifier...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_PATH
    )

    model.eval()
    model.float()

    print("Model loaded.\n")

    for message in TEST_MESSAGES:

        inputs = tokenizer(
            message,
            return_tensors="pt",
            truncation=True,
            max_length=128
        )

        with torch.no_grad():
            outputs = model(**inputs)

        probabilities = torch.softmax(outputs.logits, dim=-1)

        confidence, predicted_id = torch.max(
            probabilities,
            dim=-1
        )

        predicted_id = predicted_id.item()
        confidence = confidence.item()

        intent = model.config.id2label[predicted_id]

        print("=" * 70)
        print(f"Message:    {message}")
        print(f"Intent:     {intent}")
        print(f"Confidence: {confidence:.2%}")


if __name__ == "__main__":
    main()