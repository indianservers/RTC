"""No pretrained MLM output is ever used as an RTC intent prediction."""

import json
from pathlib import Path


class MuRILIntentClassifier:
    def __init__(self, root):
        self.root = Path(root)
        self.model = None

    def status(self):
        registry = self.root / "config/model_registry.yaml"
        if not registry.exists():
            return {"status": "NOT_READY", "reason": "Registry absent"}
        try:
            data = json.loads(registry.read_text(encoding="utf-8"))
            models = data.get("models", [])
            return {
                "status": "NOT_READY",
                "reason": "No validated fine-tuned RTC classification head and label mapping registered",
                "versions": [m.get("version") for m in models],
                "fallback": "deterministic",
            }
        except (ValueError, OSError):
            return {
                "status": "NOT_READY",
                "reason": "Invalid model registry",
                "fallback": "deterministic",
            }
