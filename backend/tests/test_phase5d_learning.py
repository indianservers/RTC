"""Real offline training/evaluation and registry lifecycle in an isolated test root."""

import json
import socket
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.catalog import Intent
from app.data_access import Principal
from app.domain import Base, database
from app.nlp.english_model import EnglishIntentModel
from app.nlp.feedback import record
from app.nlp.learning import train_candidate, transition
from fastapi import HTTPException
from sqlalchemy.orm import Session


def test_actual_candidate_evaluation_approval_deploy_and_rollback(
    tmp_path, monkeypatch
):
    def no_network(*args, **kwargs):
        raise AssertionError("Offline training/model lifecycle attempted networking")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setenv("RTC_NLP_WORKFLOW_ROOT", str(tmp_path))
    engine = database("sqlite:///" + (tmp_path / "learning.db").as_posix())
    Base.metadata.create_all(engine)
    administrator = Principal("fixture-reviewer", "ADMIN")
    variants = [
        "apple",
        "pear",
        "peach",
        "plum",
        "lemon",
        "lime",
        "orange",
        "banana",
        "melon",
        "cherry",
        "mango",
        "papaya",
        "kiwi",
        "berry",
        "grape",
        "apricot",
        "coconut",
        "guava",
        "fig",
        "olive",
        "nectarine",
        "persimmon",
        "quince",
        "raspberry",
        "strawberry",
        "tangerine",
        "watermelon",
        "avocado",
        "blueberry",
        "currant",
    ]
    labels = {
        "NEXT_BUS": "departure timetable buses schedule departure",
        "GET_FARE": "ticket cost price fare rupees amount",
        "OUT_OF_SCOPE": "weather forecast cricket recipes cooking",
    }
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        session.add_all(
            Intent(
                code=code,
                description="Synthetic test-only label",
                registry_kind="ENQUIRY" if code != "OUT_OF_SCOPE" else "DIALOGUE_ACT",
            )
            for code in labels
        )
        session.flush()
        rows = []
        for i, split in enumerate(("train", "validation", "test")):
            for code, prefix in labels.items():
                for variant in variants[i * 10 : (i + 1) * 10]:
                    rows.append(
                        record(
                            session,
                            "NLP_FEEDBACK",
                            {
                                "status": "APPROVED_FOR_TRAINING",
                                "training_eligible": True,
                                "text": (prefix + " ") * 8 + variant,
                                "text_consent": True,
                                "corrected_intent": code,
                                "group_id": str(uuid4()),
                                "split": split,
                                "example_kind": "OUT_OF_SCOPE"
                                if code == "OUT_OF_SCOPE"
                                else "CORRECTION",
                                "independent": split == "test",
                                "reviewer": "synthetic-fixture-reviewer",
                                "label_provenance": "HUMAN_REVIEWED",  # Simulated reviewer, isolated test only.
                                "reviewed_at": now.isoformat(),
                                "expires_at": (now + timedelta(days=1)).isoformat(),
                                "model_version": "TEST_ONLY",
                                "dataset_version": "SYNTHETIC_TEST_FIXTURE",
                            },
                        )
                    )
        run = train_candidate(session, rows, administrator)
        assert run.new_values["status"] == "CANDIDATE"
        assert run.new_values["metrics"]["test"]["records"] == 30
        assert all(run.new_values["gates"].values()), run.new_values
        assert not (tmp_path / "config/model_registry.yaml").exists()
        rejected = False
        try:
            transition(session, run, "deploy", administrator, 1)
        except HTTPException as exc:
            assert getattr(exc, "status_code", None) == 422
            rejected = True
        assert rejected
        transition(session, run, "approve", administrator, 1)
        transition(session, run, "deploy", administrator, 2)
        prediction = EnglishIntentModel(tmp_path).predict(labels["GET_FARE"])
        assert prediction["status"] == "KNOWN" and prediction["intents"] == ["GET_FARE"]
        assert (
            prediction["probability"] is None
            and prediction["threshold_source"] == "validation"
        )
        transition(session, run, "rollback", administrator, 3)
        assert EnglishIntentModel(tmp_path).descriptor() is None
        assert (
            json.loads((tmp_path / "config/model_registry.yaml").read_text())["models"]
            == []
        )
    engine.dispose()


def test_leakage_and_unapproved_data_block_training(tmp_path, monkeypatch):
    from app.nlp.learning import leakage_check

    rows = [
        {
            "text": "same passenger question",
            "intent": "GET_FARE",
            "split": "train",
            "group_id": "one",
        },
        {
            "text": "same passenger question",
            "intent": "GET_FARE",
            "split": "test",
            "group_id": "two",
        },
    ]
    with pytest.raises(ValueError, match="leakage"):
        leakage_check(rows)
    rows[1]["text"] = "different query"
    rows[1]["group_id"] = "one"
    with pytest.raises(ValueError, match="group"):
        leakage_check(rows)


def test_quality_does_not_infer_drift_or_positive_feedback():
    from app.nlp.feedback import quality_report
    from app.nlp.metrics import report

    assert quality_report([])["intent_accuracy"] is None
    assert quality_report([])["missing_feedback_is_positive"] is False
    assert report([])["drift"]["status"] == "INSUFFICIENT_EVIDENCE"
