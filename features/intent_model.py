import json
import os
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODEL_DIRS = (
    ROOT / "models" / "deberta_intent_v4",
    ROOT / "models" / "deberta_intent_v3",
    ROOT / "models" / "deberta_intent_v2",
    ROOT / "models" / "deberta_intent"
)
DATA_DIR = ROOT / "data" / "intents"
DEBERTA_WEIGHT = 0.15
WORD_WEIGHT = 3.0
MAX_LENGTH = 64


def corpus_labels(data_dir):

    labels = set()

    for name in ("train", "validation"):

        path = Path(data_dir) / f"{name}.json"

        if not path.exists():

            continue

        with open(path, "r", encoding="utf-8") as handle:

            for item in json.load(handle):

                intent = (item.get("intent") or "").strip()

                if intent:

                    labels.add(intent)

    return labels


class Turn:

    def __init__(self, label, confidence, scores):

        self.label = label
        self.confidence = confidence
        self.scores = scores

    def __repr__(self):

        return (
            f"Turn(label={self.label!r}, "
            f"confidence={self.confidence:.3f})"
        )


class IntentModel:

    def __init__(self, model_dir=None, data_dir=None, backend=None):

        self.model_dirs = (
            (Path(model_dir),)
            if model_dir
            else MODEL_DIRS
        )
        self.data_dir = Path(data_dir or DATA_DIR)
        self.requested_backend = (
            backend
            or os.environ.get("PAI_INTENT_BACKEND")
            or "auto"
        ).strip().lower()

        self.backend = "unloaded"
        self.labels = []
        self.load_error = ""
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._loaded = False
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._vectors = None
        self._char_vectors = None
        self._classifier = None
        self._corpus_ready = False
        self._deberta_ready = False
        self._stamp = None

    def warm(self):

        with self._lock:

            if not self._loaded:

                self._load()

    def _load(self):

        self._loaded = True

        mode = self.requested_backend

        if mode in {"auto", "corpus"}:

            self._load_corpus()

        if mode in {"auto", "deberta"}:

            self._load_deberta()

        self._set_backend()

    def _set_backend(self):

        if self._deberta_ready and self._corpus_ready:

            self.backend = "blend"

        elif self._deberta_ready:

            self.backend = "deberta"

        elif self._corpus_ready:

            self.backend = "corpus"

        else:

            self.backend = "none"

            print(
                "[intent] no understanding backend available; "
                f"{self.load_error or 'check the model and data files'}",
                flush=True
            )

    def _load_deberta(self):

        try:

            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer
            )
            from transformers.utils import logging as hf_logging

            hf_logging.disable_progress_bar()

        except Exception as error:

            self.load_error = f"torch/transformers unavailable: {error}"
            return False

        for model_dir in self.model_dirs:

            if self._read_deberta(model_dir, torch):

                return True

        return False

    def _read_deberta(self, model_dir, torch):

        config_path = model_dir / "config.json"

        if not config_path.exists():

            self.load_error = f"missing model config at {config_path}"
            return False

        try:

            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer
            )

            with open(config_path, "r", encoding="utf-8") as handle:

                config = json.load(handle)

            id2label = config.get("id2label") or {}
            labels = [
                id2label[str(index)]
                for index in range(len(id2label))
            ]

            missing = corpus_labels(self.data_dir) - set(labels)

            if missing:

                self.load_error = (
                    f"{model_dir.name} is missing labels: "
                    + ", ".join(sorted(missing))
                )
                return False

            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_dir
            )
            model.eval()

        except Exception as error:

            self.load_error = f"DeBERTa load failed: {error}"
            return False

        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._deberta_labels = labels
        self._deberta_ready = True

        print(
            f"[intent] {model_dir.name} ready with {len(labels)} labels",
            flush=True
        )

        return True

    def _load_corpus(self):

        try:

            import scipy.sparse as sp
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

        except Exception as error:

            self.load_error = (
                f"{self.load_error}; sklearn unavailable: {error}"
            ).strip("; ")
            return False

        items = []

        for name in ("train", "validation"):

            path = self.data_dir / f"{name}.json"

            if not path.exists():

                continue

            with open(path, "r", encoding="utf-8") as handle:

                items.extend(json.load(handle))

        if not items:

            self.load_error = f"no training data in {self.data_dir}"
            return False

        texts = [item["text"] for item in items]
        targets = [item["intent"] for item in items]

        try:

            word = TfidfVectorizer(
                ngram_range=(1, 2),
                lowercase=True,
                sublinear_tf=True
            )
            char = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=True,
                sublinear_tf=True
            )
            matrix = sp.hstack(
                [
                    word.fit_transform(texts) * WORD_WEIGHT,
                    char.fit_transform(texts)
                ]
            ).tocsr()
            classifier = LogisticRegression(
                max_iter=5000,
                C=20.0,
                class_weight="balanced"
            )
            classifier.fit(matrix, targets)

        except Exception as error:

            self.load_error = f"corpus model failed: {error}"
            return False

        self._vectors = word
        self._char_vectors = char
        self._classifier = classifier
        self._corpus_ready = True
        self._stamp = self._data_stamp()
        self.labels = list(classifier.classes_)

        print(
            f"[intent] corpus-trained classifier ready with "
            f"{len(self.labels)} labels from {len(items)} examples",
            flush=True
        )

        return True

    def _data_stamp(self):

        stamp = []

        for name in ("train", "validation"):

            path = self.data_dir / f"{name}.json"

            try:

                stat = path.stat()

            except OSError:

                stamp.append((name, 0, 0))
                continue

            stamp.append((name, stat.st_mtime_ns, stat.st_size))

        return tuple(stamp)

    def _refresh(self):

        stamp = self._data_stamp()

        if stamp == self._stamp:

            return

        with self._lock:

            if stamp == self._stamp:

                return

            self._stamp = stamp

            if self.requested_backend in {"auto", "corpus"}:

                self._load_corpus()
                self._set_backend()

    def classify(self, message):

        text = " ".join((message or "").split())

        if not text:

            return Turn("unknown", 0.0, {})

        self.warm()
        self._refresh()

        if self.backend == "blend":

            return self._classify_blend(text)

        if self.backend == "deberta":

            return self._classify_deberta(text)

        if self.backend == "corpus":

            return self._classify_corpus(text)

        return Turn("unknown", 0.0, {})

    def _classify_blend(self, text):

        corpus_turn = self._classify_corpus(text)
        deberta_turn = self._classify_deberta(text)

        scores = {
            label: (1.0 - DEBERTA_WEIGHT) * value
            for label, value in corpus_turn.scores.items()
        }

        for label, value in deberta_turn.scores.items():

            scores[label] = (
                scores.get(label, 0.0)
                + DEBERTA_WEIGHT * value
            )

        label = max(scores, key=scores.get)

        return Turn(label, scores[label], scores)

    def _classify_deberta(self, text):

        with self._inference_lock:

            encoded = self._tokenizer(
                text,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt"
            )

            with self._torch.no_grad():

                logits = self._model(**encoded).logits[0]

            probabilities = self._torch.softmax(logits, -1)

        scores = {
            label: float(probabilities[index])
            for index, label in enumerate(self._deberta_labels)
        }

        label = max(scores, key=scores.get)

        return Turn(label, scores[label], scores)

    def _classify_corpus(self, text):

        import scipy.sparse as sp

        matrix = sp.hstack(
            [
                self._vectors.transform([text]) * WORD_WEIGHT,
                self._char_vectors.transform([text])
            ]
        ).tocsr()
        probabilities = self._classifier.predict_proba(matrix)[0]

        scores = {
            label: float(probability)
            for label, probability in zip(
                self._classifier.classes_,
                probabilities
            )
        }

        label = max(scores, key=scores.get)

        return Turn(label, scores[label], scores)


_MODEL = IntentModel()
_WARM_THREAD = None


def get_intent_model():

    return _MODEL


def start_warmup():

    global _WARM_THREAD

    if _WARM_THREAD is not None and _WARM_THREAD.is_alive():

        return

    _WARM_THREAD = threading.Thread(
        target=_MODEL.warm,
        name="intent-warmup",
        daemon=True
    )
    _WARM_THREAD.start()
