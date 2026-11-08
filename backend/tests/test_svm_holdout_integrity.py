"""Integrity checks for a frozen external-to-training evaluation artifact."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "evaluation/english-svm-v1"


def test_frozen_holdout_and_label_coverage():
    manifest = json.loads((FOLDER / "manifest.json").read_text(encoding="utf-8"))
    data = FOLDER / "holdout.jsonl"
    assert hashlib.sha256(data.read_bytes()).hexdigest() == manifest["sha256"]
    rows = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 200
    assert len({r["id"] for r in rows}) == 200
    assert sum(r["type"] == "SINGLE_INTENT" for r in rows) == 180
    assert len({r["expected_intents"][0] for r in rows if r["expected_intents"]}) == 60
    assert all(
        not r["human_reviewed"] and r["source"] == "NEW_AGENT_AUTHORED_EVALUATION_ONLY"
        for r in rows
    )


def test_model_bytes_and_report_denominators():
    report = json.loads((FOLDER / "results.json").read_text(encoding="utf-8"))
    for model in report["models"].values():
        assert (
            hashlib.sha256((ROOT / model["artifact"]).read_bytes()).hexdigest()
            == model["sha256"]
        )
        eligible = [
            r
            for r in model["records"]
            if r["type"] == "SINGLE_INTENT" and r["eligible"]
        ]
        assert len(eligible) == model["single_intent_evaluated"]
        assert sum(r["correct"] for r in eligible) == model["correct"]
        assert sum(sum(row) for row in model["confusion_matrix"]) == len(eligible)
        assert len(model["per_class"]) == 60
        assert model["out_of_scope_false_accepts"] == model["out_of_scope_count"]
        assert model["promotion"].startswith("NONE")


def test_excluded_overlap_does_not_enter_primary_scores():
    report = json.loads((FOLDER / "results.json").read_text(encoding="utf-8"))
    for model in report["models"].values():
        for row in model["records"]:
            assert row["eligible"] == (
                not row["audit"]["exact_overlap"]
                and row["audit"]["nearest_similarity"] < report["audit_threshold"]
            )
