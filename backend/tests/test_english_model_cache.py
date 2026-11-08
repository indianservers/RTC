import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from app.nlp.english_model import EnglishIntentModel


def test_shared_thread_safe_local_model_cache(tmp_path, monkeypatch):
    import sys

    config = tmp_path / "config"
    config.mkdir()
    model = tmp_path / "model.joblib"
    model.write_bytes(b"local fixture")
    labels = ["FIRST_BUS", "LAST_BUS", "NEXT_BUS"]
    (tmp_path / "labels.json").write_text(json.dumps(labels))
    descriptor = {
        "model_type": "english_intent_svm",
        "deployment_status": "ACTIVE",
        "approved": True,
        "independent_evaluation": True,
        "threshold_source": "validation",
        "version": "test",
        "local_path": "model.joblib",
        "label_map_path": "labels.json",
        "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "decision_threshold": 0.5,
    }
    (config / "model_registry.yaml").write_text(json.dumps({"models": [descriptor]}))
    count = []

    class Scores:
        def argmax(self):
            return 2

        def __getitem__(self, index):
            return 1.0

    class Model:
        classes_ = labels

        def decision_function(self, texts):
            return [Scores()]

    def load(path):
        count.append(str(path))
        return Model()

    monkeypatch.setitem(sys.modules, "joblib", SimpleNamespace(load=load))

    def run(_):
        return EnglishIntentModel(tmp_path).predict("next bus")["intents"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(x == ["NEXT_BUS"] for x in pool.map(run, range(12)))
    assert len(count) == 1
    assert EnglishIntentModel(tmp_path).predict("x" * 2001)["status"] == "INVALID_INPUT"
    model.write_bytes(b"corrupted")
    assert (
        EnglishIntentModel(tmp_path).predict("next bus")["status"]
        == "CHECKSUM_MISMATCH"
    )
    model.unlink()
    assert EnglishIntentModel(tmp_path).predict("next bus")["status"] == "MISSING_MODEL"
