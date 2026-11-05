from training.dataset import IntentDataset
from training.tokenizer import IntentTokenizer


def main():

    dataset = IntentDataset(
        "data/intents/train.json",
        "data/intents/validation.json"
    )

    dataset.load()

    tokenizer = IntentTokenizer()

    tokenized_data = tokenizer.tokenize_dataset(
        dataset.get_train_data(),
        dataset.get_intent_to_id()
    )

    print()
    print("Tokenization successful!")
    print()

    print("First original example:")
    print(dataset.get_train_data()[0])

    print()
    print("First tokenized example:")

    first = tokenized_data[0]

    print("input_ids:")
    print(first["input_ids"])

    print()
    print("attention_mask:")
    print(first["attention_mask"])

    print()
    print("label:")
    print(first["label"])


if __name__ == "__main__":
    main()