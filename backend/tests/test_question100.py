"""Integrity of actual 100-question executions and their non-independent training use."""

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evaluation/question100-v1"
DATA = ROOT / "training/datasets/question100-v1"


@pytest.fixture(
    autouse=True,
    params=[
        "question100-v1",
        "question100-v2",
        "question100-v3",
        "question100-v4",
        "question100-v5",
    ],
)
def batch(request, monkeypatch):
    monkeypatch.setattr(
        sys.modules[__name__], "OUT", ROOT / "evaluation" / request.param
    )
    monkeypatch.setattr(
        sys.modules[__name__], "DATA", ROOT / "training/datasets" / request.param
    )


@lru_cache(maxsize=64)
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("number", range(100))
def test_each_actual_question_has_expected_before_control_after(number):
    expected = read(OUT / "expected.json")[number]
    identifier = (
        f"Q{number + 1:03}"
        if OUT.name == "question100-v1"
        else f"{OUT.name}-Q{number + 1:03}"
    )
    assert expected["id"] == identifier and expected["human_reviewed"] is False
    for filename in ["before.json", "previous-shadow.json", "after-shadow.json"]:
        report = read(OUT / filename)
        row = report["records"][number]
        assert (
            row["question"] == expected["question"]
            and row["expected"] == expected["expected"]
        )
        assert row["actual"]["answer"]
        assert row["evaluation"]["passed"] == all(row["evaluation"]["checks"].values())
        # No owner capabilities or private state is retained in published evidence.
        assert "owner_token" not in json.dumps(row) and "_owner_hash" not in json.dumps(
            row
        )


def test_all_100_are_unique_and_counts_are_actual():
    expected = read(OUT / "expected.json")
    assert len(expected) == len({r["question"].casefold() for r in expected}) == 100
    for filename in ["before.json", "previous-shadow.json", "after-shadow.json"]:
        r = read(OUT / filename)
        assert len(r["records"]) == r["evaluated_questions"] == 100
        assert r["passed"] == sum(x["evaluation"]["passed"] for x in r["records"])
        assert sum(v["total"] for v in r["by_kind"].values()) == 100


def test_training_excludes_dialogue_multi_and_holdout_records():
    manifest = read(DATA / "manifest.json")
    partitions = {}
    for split, meta in manifest["files"].items():
        path = ROOT / meta["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
        partitions[split] = [
            json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
        ]
    new = [
        r
        for r in partitions["train"]
        if r["id"] in manifest.get("new_classifier_ids", [])
        or (OUT.name == "question100-v1" and r["id"].startswith("Q"))
    ]
    assert len(new) == 70 and sum(r["kind"] == "IN_SCOPE" for r in new) == 60
    assert len((DATA / "structured_targets.jsonl").read_text().splitlines()) == 30
    train = {r["normalized_text"] for r in partitions["train"]}
    assert not train & {
        r["normalized_text"]
        for r in partitions["validation"] + partitions["synthetic_challenge"]
    }
    assert read(OUT / "leakage-audit.json")["near_overlaps"] == []


@pytest.mark.parametrize(
    "model", ["previous_svm", "trained_svm", "previous_cnn", "trained_cnn"]
)
def test_model_metrics_have_complete_denominators(model):
    for result in read(OUT / "model-comparison.json")["models"][model].values():
        assert sum(map(sum, result["confusion_matrix"])) == result["count"]
        inside = [r for r in result["records"] if r["expected"] != "OUT_OF_SCOPE"]
        assert result["raw_in_scope_accuracy"] == sum(
            r["raw_prediction"] == r["expected"] for r in inside
        ) / len(inside)


def test_new_models_are_candidates_not_deployments():
    entries = [
        r
        for r in read(ROOT / "config/model_registry.yaml")["models"]
        if r.get("version") == OUT.name
    ]
    assert len(entries) == 2 and all(
        r["deployment_status"] == "CANDIDATE"
        and not r["approved"]
        and not r["independent_evaluation"]
        for r in entries
    )
