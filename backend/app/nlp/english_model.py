"""Only explicitly approved, validation-calibrated local models may classify."""

import hashlib
import json
from pathlib import Path
from threading import RLock
from typing import Any, ClassVar


class EnglishIntentModel:
    _cache: ClassVar[dict[tuple[str, str, str], Any]] = {}
    _lock = RLock()

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.model = None
        self.version = None

    def descriptor(self):
        registry = self.root / "config/model_registry.yaml"
        if not registry.is_file():
            return None
        try:
            entries = json.loads(registry.read_text(encoding="utf-8")).get("models", [])
        except (ValueError, OSError):
            return None
        candidates = [
            e
            for e in entries
            if e.get("deployment_status") == "ACTIVE"
            and e.get("model_type") == "english_intent_svm"
        ]
        if len(candidates) != 1:
            return None
        row = candidates[0]
        if (
            row.get("decision_threshold") is None
            or not row.get("label_map_path")
            or not row.get("approved")
            or not row.get("independent_evaluation")
            or row.get("threshold_source") != "validation"
        ):
            return None
        return row

    def predict(self, text):
        if not isinstance(text, str) or not 1 <= len(text) <= 2000:
            return {"status": "INVALID_INPUT", "intents": []}
        row = self.descriptor()
        if row is None:
            return {"status": "NOT_READY", "intents": []}
        path = (self.root / row["local_path"]).resolve()
        if not path.is_relative_to(self.root):
            return {"status": "INVALID_MODEL_PATH", "intents": []}
        if not path.is_file():
            return {"status": "MISSING_MODEL", "intents": []}
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            return {"status": "CHECKSUM_MISMATCH", "intents": []}
        with self._lock:
            key = (str(path), row["version"], row["sha256"])
            if key not in self._cache:
                import joblib

                loaded = joblib.load(path)
                label_path = (self.root / row["label_map_path"]).resolve()
                if not label_path.is_relative_to(self.root):
                    return {"status": "INVALID_LABEL_MAP", "intents": []}
                labels = json.loads(label_path.read_text(encoding="utf-8"))
                if list(loaded.classes_) != labels:
                    return {"status": "LABEL_MAP_MISMATCH", "intents": []}
                self._cache[key] = loaded
            self.model = self._cache[key]
            self.version = row["version"]
            if callable(getattr(self.model, "predict_selective", None)):
                prediction = self.model.predict_selective([text])[0]
                return {**prediction, "version": self.version}
            scores = self.model.decision_function([text])[0]
        # Multiclass SVM decision values are margins, not probabilities.
        if not hasattr(scores, "argmax"):
            return {"status": "UNSUPPORTED_BINARY_MODEL", "intents": []}
        index = int(scores.argmax())
        margin = float(scores[index])
        if margin < float(row["decision_threshold"]):
            return {
                "status": "CLARIFICATION_REQUIRED",
                "intents": [],
                "decision_margin": margin,
            }
        return {
            "status": "KNOWN",
            "intents": [str(self.model.classes_[index])],
            "decision_margin": margin,
            "version": self.version,
        }
