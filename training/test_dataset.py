from training.dataset import IntentDataset


def main():

    dataset = IntentDataset(
        "data/intents/train.json",
        "data/intents/validation.json"
    )

    dataset.load()

    print()
    print("Dataset loaded successfully!")
    print()

    print(f"Training examples: {len(dataset.get_train_data())}")
    print(f"Validation examples: {len(dataset.get_validation_data())}")

    print()
    print("Intents:")

    for intent in dataset.get_intents():
        print(f" - {intent}")

    print()
    print("Intent to ID mapping:")

    for intent, intent_id in dataset.get_intent_to_id().items():
        print(f" - {intent}: {intent_id}")

    print()
    print("First training example:")

    print(dataset.get_train_data()[0])

    print()
    print("First example label ID:")

    first_intent = dataset.get_train_data()[0]["intent"]
    print(dataset.get_intent_to_id()[first_intent])


if __name__ == "__main__":
    main()