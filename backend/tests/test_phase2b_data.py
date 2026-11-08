import json
from pathlib import Path

import pytest

from training.generation.generate import generate
from training.validation.records import Example
from training.validation.validate_phase2b import family_leakage, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def resources():
    folder = ROOT / "training/datasets/generated/2b-v1"
    return (
        json.loads((ROOT / "training/config/intent_registry.yaml").read_text()),
        json.loads((folder / "vocabulary.json").read_text(encoding="utf-8")),
    )


def test_all_specs(resources):
    registry, _ = resources
    specs = json.loads(
        (ROOT / "training/generation/intent_specs.json").read_text(encoding="utf-8")
    )
    assert {r["code"] for r in specs} == {r["code"] for r in registry["intents"]}


def test_reproducibility_and_provenance(resources):
    registry, vocabulary = resources
    first = generate(registry, vocabulary)
    second = generate(registry, vocabulary)
    assert first == second
    assert all(
        r["source_type"] == "SYNTHETIC"
        and r["quality_status"] == "PENDING_HUMAN_REVIEW"
        for r in first
    )
    ids = {r["example_id"]: r for r in first}
    for row in first:
        if row["parent_example_id"]:
            assert (
                row["template_family"]
                == ids[row["parent_example_id"]]["template_family"]
            )


def test_measured_validation(resources):
    registry, vocabulary = resources
    rows = generate(registry, vocabulary)
    report = validate(rows, registry, vocabulary)
    assert report["records"] == len(rows) == report["valid_records"]
    assert report["schema_errors"] == []
    assert report["duplicate_normalized_text_pairs"] == 0
    assert report["quantity_targets_met"] is False
    assert set(report["single_intent_shortfalls"]) == {
        r["code"] for r in registry["intents"]
    }


def test_context_and_negation(resources):
    rows = generate(*resources)
    for row in rows:
        if row["dataset_type"] == "CONTEXTUAL":
            assert row["context"] and "expected_context" in row
        if row["text"] == "No AC buses, please.":
            assert row["constraints"]["ac"] is False
        if row["text"] == "Not a sleeper.":
            assert row["constraints"]["sleeper"] is False
        if row["dataset_type"] == "AMBIGUOUS":
            assert not row["intent_codes"] and row["possible_intents"]


def test_corrupt_spans_rejected(resources):
    row = next(r for r in generate(*resources) if r["entities"])
    row["entities"][0]["text"] = "not the span"
    with pytest.raises(ValueError):
        Example.model_validate(row)


def test_family_boundary_guard():
    rows = [
        {"template_family": "shared", "split": "train"},
        {"template_family": "shared", "split": "test"},
    ]
    assert family_leakage(rows) == ["shared"]


def test_unicode_span():
    from training.generation.annotations import annotate

    text = "Bus to విజయవాడ?"
    entities = annotate(
        text, {"places": [("విజయవాడ", "real-fixture-id")], "categories": []}
    )
    assert entities and text[entities[0]["start"] : entities[0]["end"]] == "విజయవాడ"


def test_generation_offline(resources, monkeypatch):
    import socket

    def deny(*args, **kwargs):
        raise AssertionError("Network access attempted")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    assert generate(*resources)
