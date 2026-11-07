import json
import os
import random
import re
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup
)

ROOT = Path(r"F:\MainProjects\PersonalAi")
TRAIN_PATH = ROOT / "data" / "intents" / "train.json"
VALIDATION_PATH = ROOT / "data" / "intents" / "validation.json"
BASE_DIRS = (
    ROOT / "models" / "deberta_intent_v2",
    ROOT / "models" / "deberta_intent"
)
OUTPUT_DIR = ROOT / "models" / "deberta_intent_v3"
BASE_MODEL = next(
    (path for path in BASE_DIRS if (path / "config.json").exists()),
    BASE_DIRS[-1]
)

MAX_LENGTH = 64
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 3e-5
SEED = 42
FREEZE_LAYERS = 6


def load_examples(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class IntentTexts(Dataset):

    def __init__(self, items, label_to_id):
        self.items = items
        self.label_to_id = label_to_id

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        item = self.items[index]
        return item["text"], self.label_to_id[item["intent"]]


def make_loader(dataset, tokenizer, shuffle):
    def collate(batch):
        texts = [item[0] for item in batch]
        labels = torch.tensor([item[1] for item in batch], dtype=torch.long)
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )
        return encoded, labels

    return DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=shuffle,
        collate_fn=collate
    )


def evaluate(model, loader):
    model.eval()
    predictions = []
    expected = []
    total_loss = 0.0

    with torch.no_grad():
        for encoded, labels in loader:
            output = model(**encoded, labels=labels)
            total_loss += output.loss.item() * labels.size(0)
            predictions.extend(output.logits.argmax(-1).tolist())
            expected.extend(labels.tolist())

    accuracy = float(np.mean(np.array(predictions) == np.array(expected)))
    return total_loss / len(expected), accuracy, predictions, expected


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))

    train_items = load_examples(TRAIN_PATH)
    validation_items = load_examples(VALIDATION_PATH)

    labels = sorted(
        {item["intent"] for item in train_items}
        | {item["intent"] for item in validation_items}
    )
    label_to_id = {label: index for index, label in enumerate(labels)}
    id_to_label = {index: label for label, index in label_to_id.items()}

    print("train", len(train_items), "validation", len(validation_items))
    print("labels", len(labels))

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(labels),
        ignore_mismatched_sizes=True
    )
    model.config.id2label = id_to_label
    model.config.label2id = label_to_id
    model.float()

    frozen = 0

    for name, parameter in model.named_parameters():

        if name.startswith("deberta.embeddings"):

            parameter.requires_grad = False
            frozen += 1
            continue

        match = re.match(r"deberta\.encoder\.layer\.(\d+)\.", name)

        if match and int(match.group(1)) < FREEZE_LAYERS:

            parameter.requires_grad = False
            frozen += 1

    print(
        f"froze {frozen} tensors below layer {FREEZE_LAYERS}",
        flush=True
    )

    train_loader = make_loader(
        IntentTexts(train_items, label_to_id),
        tokenizer,
        True
    )
    validation_loader = make_loader(
        IntentTexts(validation_items, label_to_id),
        tokenizer,
        False
    )

    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=LEARNING_RATE,
        weight_decay=0.01
    )
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(total_steps * 0.1)),
        num_training_steps=total_steps
    )

    started = time.time()

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        seen = 0
        epoch_started = time.time()

        for step, (encoded, labels_batch) in enumerate(train_loader, 1):
            output = model(**encoded, labels=labels_batch)
            output.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            running_loss += output.loss.item() * labels_batch.size(0)
            seen += labels_batch.size(0)

            if step % 20 == 0:
                print(
                    f"epoch {epoch + 1} step {step}/{len(train_loader)} "
                    f"loss {running_loss / seen:.4f}",
                    flush=True
                )

        validation_loss, accuracy, predictions, expected = evaluate(
            model,
            validation_loader
        )

        print(
            f"epoch {epoch + 1} done in {time.time() - epoch_started:.0f}s "
            f"train_loss {running_loss / seen:.4f} "
            f"val_loss {validation_loss:.4f} val_acc {accuracy:.4f}",
            flush=True
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    with open(OUTPUT_DIR / "labels.json", "w", encoding="utf-8") as handle:
        json.dump(label_to_id, handle, indent=2)
        handle.write("\n")

    print("saved", OUTPUT_DIR, "in", round(time.time() - started), "s")

    from collections import Counter

    per_label = {}
    expected_counts = Counter(expected)

    for label, count in expected_counts.items():
        correct = sum(
            1
            for prediction, target in zip(predictions, expected)
            if prediction == target == label
        )
        per_label[id_to_label[label]] = (correct, count)

    for label in sorted(per_label):
        correct, count = per_label[label]
        print(f"  {label:18} {correct}/{count}")


if __name__ == "__main__":
    main()
