"""Read-only local candidate load smoke. Does not approve or activate a model."""

import hashlib
import json
import os
import socket
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def blocked(*args, **kwargs):
    raise RuntimeError("Outbound network disabled by offline model smoke")


def run():
    # Block every connection, including loopback, before importing the model runtime.
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    import joblib
    from app.nlp.english_model import EnglishIntentModel

    registry = json.loads(
        (ROOT / "config/model_registry.yaml").read_text(encoding="utf-8")
    )
    entry = next(
        m for m in registry["models"] if m.get("model_type") == "english_intent_svm"
    )
    path = (ROOT / entry["local_path"]).resolve()
    assert path.is_relative_to(ROOT)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    assert checksum == entry["sha256"]
    start = perf_counter()
    model = joblib.load(path)
    load_ms = (perf_counter() - start) * 1000
    labels = json.loads((ROOT / entry["label_map_path"]).read_text(encoding="utf-8"))
    assert list(model.classes_) == labels
    start = perf_counter()
    predictions = model.predict(
        [
            "Next bus to Nellore?",
            "How much is the fare?",
            "Which platform?",
            "Show connecting buses",
            "Does it stop at Ongole?",
        ]
    )
    inference_ms = (perf_counter() - start) * 1000
    report = {
        "network": "ALL_SOCKET_CONNECTIONS_BLOCKED",
        "candidate": entry["name"],
        "local_path": entry["local_path"],
        "sha256": checksum,
        "checksum_verified": True,
        "load_ms": load_ms,
        "batch_inference_ms": inference_ms,
        "samples": len(predictions),
        "load_success": True,
        "forward_success": len(predictions) == 5,
        "predictions_are_accuracy_evidence": False,
        "deployment_status": entry["deployment_status"],
        "approved": entry["approved"],
        "application_model_status": EnglishIntentModel(ROOT).predict(
            "Next bus to Nellore?"
        )["status"],
        "note": "Candidate-only technical load verification; runtime approval gates and registry remain unchanged.",
    }
    (ROOT / "docs/phase4c-offline-model.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
