from pathlib import Path

import pytest
from app.nlp.english_model import EnglishIntentModel
from app.nlp.model_lifecycle import transition


def test_pilot_cannot_be_promoted():
    with pytest.raises(ValueError):
        transition(
            {"deployment_status": "CANDIDATE", "training_metrics": {"macro_f1": 1}},
            "EVALUATED",
        )


def test_runtime_has_no_active_pilot():
    assert (
        EnglishIntentModel(Path.cwd()).predict("unrelated request")["status"]
        == "NOT_READY"
    )


def test_rollback_retains_descriptor():
    entry = {"deployment_status": "ACTIVE", "local_path": "models/old.joblib"}
    assert transition(entry, "ROLLED_BACK")["local_path"] == entry["local_path"]
