from training.dataset import IntentDataset
from models.deberta_classifier import DebertaIntentClassifier


def main():

    dataset = IntentDataset(
        "data/intents/train.json",
        "data/intents/validation.json"
    )

    dataset.load()

    intents = dataset.get_intents()

    print()
    print("Number of intents:", len(intents))

    print()
    print("Intents:")

    for intent in intents:
        print(f" - {intent}")

    classifier = DebertaIntentClassifier(
        model_name="microsoft/deberta-v3-base",
        num_labels=len(intents)
    )

    model = classifier.get_model()

    print()
    print("Classifier test successful!")
    print()

    print("Number of output labels:")
    print(model.config.num_labels)

    print()
    print("Label mapping:")

    for intent, intent_id in dataset.get_intent_to_id().items():
        print(f" - {intent_id}: {intent}")


if __name__ == "__main__":
    main()