"""Explicit candidate-only offline text inference; does not enable the model in chat."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from offline_guard import enforce_offline

enforce_offline()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect a frozen selective SVM candidate, without deployment"
    )
    parser.add_argument("text")
    args = parser.parse_args()
    if not 1 <= len(args.text) <= 2000:
        parser.error("Text length must be 1 to 2000 characters")
    folder = ROOT / "models/english/nlp/selective-60-v2"
    descriptor = json.loads((folder / "descriptor.json").read_text(encoding="utf-8"))
    path = folder / "svm.joblib"
    if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
        raise SystemExit("Candidate checksum mismatch")
    import joblib

    model = joblib.load(path)
    result = model.predict_selective([args.text])[0]
    print(
        json.dumps(
            {
                "candidate_version": descriptor["version"],
                "deployment_status": "CANDIDATE",
                "chat_model_enabled": False,
                "prediction": result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
