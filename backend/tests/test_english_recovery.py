"""Frozen corpus and actual measured candidate results, without activation."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "training/datasets/recovery-60-v3"
REPORT = ROOT / "evaluation/english-recovery-v3"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataset_coverage_provenance_and_disjoint_splits():
    from app.nlp.components import LanguageNormalizer

    manifest = read(DATA / "manifest.json")
    assert (
        hashlib.sha256((DATA / "train-bank.txt").read_bytes()).hexdigest()
        == manifest["bank_sha256"]
    )
    assert (
        hashlib.sha256((DATA / "leakage-audit.json").read_bytes()).hexdigest()
        == manifest["audit_sha256"]
    )
    labels = set(manifest["labels"])
    assert len(labels) == 60 and manifest["independent_human_test"] == 0
    assert manifest["minimum_train_examples"] >= 30
    groups = {}
    exact = {}
    for split, info in manifest["files"].items():
        path = ROOT / info["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"]
        records = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        assert len(records) == info["count"]
        for row in records:
            assert row["normalized_text"] == LanguageNormalizer().normalize(row["text"])
            assert (
                row["human_reviewed"] is False
                and row["review_status"] == "PENDING_HUMAN_REVIEW"
            )
            assert (
                row["intent"] in labels
                if row["kind"] == "IN_SCOPE"
                else row["intent"] is None
            )
            for key, store in [
                (row["group_id"], groups),
                (row["normalized_text"], exact),
            ]:
                assert key not in store or store[key] == split
                store[key] = split
    assert set(manifest["files"]["train"]["intent_counts"]) == labels


@pytest.mark.parametrize(
    "model",
    [
        "deterministic_rules",
        "grouped_svm",
        "selective_svm_v2",
        "new_svm",
        "old_textcnn",
        "new_textcnn",
    ],
)
def test_actual_report_counts_and_confusion_denominators(model):
    report = read(REPORT / "comparison.json")
    assert (
        report["independent_human_test_count"] == 0
        and report["promotion"] == "DO_NOT_PROMOTE"
    )
    for metrics in report["models"][model].values():
        assert sum(map(sum, metrics["confusion_matrix"])) == metrics["count"] == 240
        assert metrics["in_scope_count"] == 180 and metrics["out_of_scope_count"] == 60
        records = [r for r in metrics["records"] if r["expected"] != "OUT_OF_SCOPE"]
        assert metrics["accuracy"] == sum(r["correct"] for r in records) / 180
        assert (
            len(
                [
                    k
                    for k in metrics["per_intent"]
                    if k in read(DATA / "manifest.json")["labels"]
                ]
            )
            == 60
        )


def test_candidate_registry_does_not_enable_models():
    registry = read(ROOT / "config/model_registry.yaml")
    candidates = [m for m in registry["models"] if m.get("version") == "recovery-60-v3"]
    assert len(candidates) == 2
    assert all(
        m["deployment_status"] == "CANDIDATE"
        and not m["approved"]
        and not m["independent_evaluation"]
        for m in candidates
    )
    assert not any(
        m.get("deployment_status") == "ACTIVE"
        and m.get("model_type") in {"english_intent_svm", "english_intent_textcnn"}
        for m in registry["models"]
    )


def test_shadow_dialogue_preserves_grounded_selection_and_repairs():
    report = read(REPORT / "conversation.json")
    assert (
        report["models"]["new_svm"]["passed"]
        == report["models"]["new_svm"]["total"]
        == 7
    )
    assert report["models"]["new_svm"]["fallback_was_exercised"]
    names = {s["case"] for s in report["models"]["new_svm"]["steps"]}
    assert {
        "How much?",
        "Same bus.",
        "Second one.",
        "What about tomorrow?",
        "No, Tirumala.",
    } <= names


def test_cnn_failed_calibration_never_claims_precision():
    calibration = read(REPORT / "textcnn-validation-calibration.json")
    assert calibration["selected"] is None
    result = read(REPORT / "comparison.json")["models"]["new_textcnn"][
        "synthetic_challenge"
    ]
    assert result["accepted_id_count"] == 0 and result["accepted_id_precision"] is None
