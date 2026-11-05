from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)

from training.dataset import IntentDataset

MODEL_NAME = "microsoft/deberta-v3-base"

TRAIN_PATH = "data/intents/train.json"
VALIDATION_PATH = "data/intents/validation.json"

OUTPUT_DIR = "models/deberta_intent"

def main():

    # -----------------------------
    # Load our intent dataset
    # -----------------------------

    intent_dataset = IntentDataset(
        TRAIN_PATH,
        VALIDATION_PATH
    )

    intent_dataset.load()

    train_data = intent_dataset.get_train_data()
    validation_data = intent_dataset.get_validation_data()

    intents = intent_dataset.get_intents()
    intent_to_id = intent_dataset.get_intent_to_id()

    print()
    print("Dataset loaded.")
    print(f"Training examples: {len(train_data)}")
    print(f"Validation examples: {len(validation_data)}")
    print(f"Number of intents: {len(intents)}")

    # -----------------------------
    # Convert JSON into HF Dataset
    # -----------------------------

    train_dataset = Dataset.from_list(train_data)
    validation_dataset = Dataset.from_list(validation_data)

    # -----------------------------
    # Load tokenizer
    # -----------------------------

    print()
    print("Loading tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    print("Tokenizer loaded.")

    # -----------------------------
    # Tokenization function
    # -----------------------------

    def tokenize_function(examples):

        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=128
        )

    print()
    print("Tokenizing training data...")

    train_dataset = train_dataset.map(
        tokenize_function,
        batched=True
    )

    print("Tokenizing validation data...")

    validation_dataset = validation_dataset.map(
        tokenize_function,
        batched=True
    )

    # -----------------------------
    # Convert intent names to IDs
    # -----------------------------

    def convert_labels(example):

        example["labels"] = intent_to_id[example["intent"]]
        return example

    train_dataset = train_dataset.map(
        convert_labels
    )

    validation_dataset = validation_dataset.map(
        convert_labels
    )

    # -----------------------------
    # Load classification model
    # -----------------------------

    print()
    print("Loading DeBERTa classifier...")

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(intents),
        id2label={
            index: intent
            for intent, index in intent_to_id.items()
        },
        label2id=intent_to_id
    )
    
    model = model.float()

    print("DeBERTa classifier loaded.")

    # -----------------------------
    # Training configuration
    # -----------------------------

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,

        num_train_epochs=5,

        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,

        learning_rate=1e-5,

        weight_decay=0.01,

        eval_strategy="epoch",
        save_strategy="no",

        logging_steps=1,

        report_to="none",
        
        fp16=False,
        bf16=False
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    # -----------------------------
    # Create Trainer
    # -----------------------------

    trainer = Trainer(
        model=model,

        args=training_args,

        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=data_collator
    )

    # -----------------------------
    # Start training
    # -----------------------------

    print()
    print("==============================")
    print("Starting DeBERTa training...")
    print("==============================")
    print()

    trainer.train()

    # -----------------------------
    # Save final model
    # -----------------------------

    print()
    print("Saving trained model...")

    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print()
    print("==============================")
    print("Training complete!")
    print("==============================")
    print()
    print(f"Model saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()