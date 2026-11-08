"""Selective SVM decisions, approval-preserving adapters and immutable split contracts."""

import hashlib
import json
import sys
from math import nan
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.nlp.english_model import EnglishIntentModel
from app.nlp.selective_svm import decide
from hypothesis import given
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS = {"domain": 0.5, "margin": -0.5, "gap": 0.1}


@pytest.mark.parametrize(
    "scores,domain,status",
    [
        ([1.0, 0.5], 1.0, "KNOWN"),
        ([1.0, 0.5], 0.49, "OUT_OF_SCOPE"),
        ([-0.6, -0.9], 1.0, "CLARIFICATION_REQUIRED"),
        ([1.0, 1.0], 1.0, "CLARIFICATION_REQUIRED"),
        ([1.0, 0.5], 0.5, "KNOWN"),
        ([-0.5, -1.0], 1.0, "KNOWN"),
    ],
)
def test_rejection_contract(scores, domain, status):
    result = decide(scores, domain, ["FIRST_BUS", "NEXT_BUS"], THRESHOLDS)
    assert result["status"] == status
    assert bool(result["intents"]) == (status == "KNOWN")
    assert result["probability"] is None


@pytest.mark.parametrize(
    "scores,domain,classes",
    [
        ([nan, 0.2], 1, ["A", "B"]),
        ([0.1, 0.2], nan, ["A", "B"]),
        ([0.1], 1, ["A"]),
        ([0.1, 0.2], 1, ["A"]),
    ],
)
def test_malformed_scores_fail_closed(scores, domain, classes):
    with pytest.raises(ValueError):
        decide(scores, domain, classes, THRESHOLDS)


@given(
    st.floats(-10, 10, allow_nan=False, allow_infinity=False),
    st.floats(-10, 10, allow_nan=False, allow_infinity=False),
    st.floats(-5, 5, allow_nan=False, allow_infinity=False),
    st.floats(0, 5, allow_nan=False, allow_infinity=False),
)
def test_stricter_gate_never_accepts_a_rejection(a, b, domain, increase):
    first = decide([a, b], domain, ["A", "B"], THRESHOLDS)
    strict = {k: v + increase for k, v in THRESHOLDS.items()}
    second = decide([a, b], domain, ["A", "B"], strict)
    if first["status"] != "KNOWN":
        assert second["status"] != "KNOWN"


def test_approved_adapter_dispatches_selective_rejection(tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.mkdir()
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"fixture, not an approved real model")
    (tmp_path / "labels.json").write_text(json.dumps(["A", "B"]))
    row = {
        "model_type": "english_intent_svm",
        "deployment_status": "ACTIVE",
        "approved": True,
        "independent_evaluation": True,
        "threshold_source": "validation",
        "version": "unit-test",
        "local_path": "model.joblib",
        "label_map_path": "labels.json",
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "decision_threshold": -1,
    }
    (config / "model_registry.yaml").write_text(json.dumps({"models": [row]}))

    class Model:
        classes_ = ("A", "B")

        def predict_selective(self, texts):
            return [{"status": "OUT_OF_SCOPE", "intents": [], "domain_margin": -0.2}]

        def decision_function(self, texts):
            pytest.fail("Selective rejection fell back to forced choice")

    monkeypatch.setitem(
        sys.modules, "joblib", SimpleNamespace(load=lambda path: Model())
    )
    result = EnglishIntentModel(tmp_path).predict("An unrelated request")
    assert result["status"] == "OUT_OF_SCOPE" and not result["intents"]
    assert result["version"] == "unit-test"
    row["deployment_status"] = "CANDIDATE"
    row["approved"] = False
    (config / "model_registry.yaml").write_text(json.dumps({"models": [row]}))
    assert EnglishIntentModel(tmp_path).predict("bus")["status"] == "NOT_READY"


def test_frozen_data_is_disjoint_and_provenance_is_explicit():
    folder = ROOT / "training/datasets/selective-60-v2"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    sets = {}
    groups = {}
    for split, meta in manifest["files"].items():
        path = ROOT / meta["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
        rows = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        ]
        sets[split] = {" ".join(r["text"].casefold().split()) for r in rows}
        groups[split] = {r["family"] for r in rows}
        assert len(rows) == meta["records"]
        assert len({r["intent"] for r in rows if r["kind"] == "IN_SCOPE"}) == 60
        assert all(not r["human_reviewed"] for r in rows)
    assert (
        not sets["train"] & sets["validation"]
        and not groups["train"] & groups["validation"]
    )
    testfile = ROOT / "evaluation/english-svm-v2/holdout.jsonl"
    testmanifest = json.loads(
        (testfile.parent / "manifest.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(testfile.read_bytes()).hexdigest() == testmanifest["sha256"]
    tests = [json.loads(x) for x in testfile.read_text(encoding="utf-8").splitlines()]
    assert len(tests) == 240
    assert not {r["text"].casefold() for r in tests} & (
        sets["train"] | sets["validation"]
    )
    audit = json.loads((folder / "leakage-audit.json").read_text(encoding="utf-8"))
    assert all(
        r["similarity"] < 0.85 for r in audit["decisions"] if r["reason"] is None
    )
    assert {r["split"] for r in audit["excluded"]} == {"train"}


def test_frozen_checkpoint_and_metrics_denominators():
    folder = ROOT / "models/english/nlp/selective-60-v2"
    descriptor = json.loads((folder / "descriptor.json").read_text(encoding="utf-8"))
    assert (
        descriptor["deployment_status"] == "CANDIDATE"
        and descriptor["approved"] is False
    )
    assert (
        descriptor["threshold_source"] == "validation"
        and descriptor["human_reviewed"] is False
    )
    assert (
        hashlib.sha256((folder / "svm.joblib").read_bytes()).hexdigest()
        == descriptor["sha256"]
    )
    assert (
        hashlib.sha256((ROOT / "config/model_registry.yaml").read_bytes()).hexdigest()
        == descriptor["registry_sha256_at_freeze"]
    )
    report = json.loads(
        (ROOT / "evaluation/english-svm-v2/results.json").read_text(encoding="utf-8")
    )
    assert report["registry_sha256_before"] == report["registry_sha256_after"]
    for result in report["models"].values():
        assert sum(sum(row) for row in result["confusion_matrix"]) == result["id_count"]
        assert result["id_accepted"] + result["id_rejected"] == result["id_count"]
        assert (
            result["oos_false_accepted"] + result["oos_rejected"]
            == result["out_of_scope_count"]
        )
        actual = sum(
            r["prediction"]["status"] == "KNOWN"
            and r["prediction"]["intents"] == [r["intent"]]
            for r in result["records"]
            if r["kind"] == "IN_SCOPE"
        )
        assert actual == result["accepted_id_correct"]
        assert len(result["per_class_closed"]) >= 60
