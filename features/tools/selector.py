import json
import threading

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "tools" / "examples.json"
WORD_WEIGHT = 3.0


class ToolSelector:

    def __init__(self, path=None):

        self.path = Path(path or DATA_PATH)
        self._lock = threading.Lock()
        self._ready = False
        self._vectors = None
        self._char_vectors = None
        self._classifier = None
        self._stamp = None
        self.error = ""

    def _stamp_now(self):

        try:

            stat = self.path.stat()

        except OSError:

            return None

        return (stat.st_mtime_ns, stat.st_size)

    def warm(self):

        with self._lock:

            if not self._ready:

                self._load()

    def _load(self):

        self._stamp = self._stamp_now()

        if self._stamp is None:

            self.error = f"missing {self.path}"
            return False

        try:

            import scipy.sparse as sp
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

            with self.path.open("r", encoding="utf-8") as handle:

                items = json.load(handle)

            texts = [item["text"] for item in items]
            targets = [item["tool"] for item in items]

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

            self.error = f"tool selector failed: {error}"
            return False

        self._vectors = word
        self._char_vectors = char
        self._classifier = classifier
        self._ready = True
        self.error = ""

        print(
            f"[tools] selector ready with {len(texts)} examples",
            flush=True
        )

        return True

    def _refresh(self):

        stamp = self._stamp_now()

        if stamp is None or stamp == self._stamp:

            return

        with self._lock:

            if stamp != self._stamp:

                self._ready = False
                self._load()

    def scores(self, text):

        text = " ".join((text or "").split())

        if not text:

            return {}

        self.warm()
        self._refresh()

        if not self._ready:

            return {}

        import scipy.sparse as sp

        matrix = sp.hstack(
            [
                self._vectors.transform([text]) * WORD_WEIGHT,
                self._char_vectors.transform([text])
            ]
        ).tocsr()
        probabilities = self._classifier.predict_proba(matrix)[0]

        return {
            label: float(probability)
            for label, probability in zip(
                self._classifier.classes_,
                probabilities
            )
        }

    def select(self, text, threshold=0.45):

        scores = self.scores(text)

        if not scores:

            return None

        label = max(scores, key=scores.get)
        confidence = scores[label]

        if label == "none" or confidence < threshold:

            return None

        return {
            "tool": label,
            "confidence": confidence,
            "scores": scores
        }


SELECTOR = ToolSelector()
