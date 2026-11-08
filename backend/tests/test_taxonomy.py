import json
from collections import Counter
from pathlib import Path

import pytest
from app import main
from app.catalog import Intent, Utterance
from app.domain import Base, database
from app.engine import RTCEnquiryEngine
from app.nlp.content import NLPContentRepository
from app.nlp.taxonomy import IntentRegistry
from app.nlp_seed import seed_nlp
from app.seed import seed
from app.taxonomy_seed import seed_taxonomy
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def taxonomy_db(tmp_path):
    engine = database("sqlite:///" + str(tmp_path / "taxonomy.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    seed_nlp(engine)
    seed_taxonomy(engine)
    return engine


def test_exact_taxonomy_and_slots(taxonomy_db):
    with Session(taxonomy_db) as s:
        intents = IntentRegistry(s).list()
        assert len(intents) == 60
        assert len({i.code for i in intents}) == 60
        assert len({i.definition for i in intents}) == 60
        assert Counter(i.intent_group for i in intents) == {
            "TIMINGS": 12,
            "BUS_TYPES": 10,
            "ROUTES": 10,
            "FARES_AND_BOOKINGS": 12,
            "OPERATIONS": 10,
            "STATION_ASSISTANCE": 6,
        }
        for i in intents:
            assert i.capability in ("IMPLEMENTED", "PARTIAL", "UNSUPPORTED")
            assert len(i.examples) == 5
            assert i.required_slots or i.model_extra["required_slot_alternatives"]
            assert i.model_extra["clarifications"]
            if i.capability == "UNSUPPORTED":
                assert i.backend_code is None
        assert len(IntentRegistry(s).entities()) == 32
        assert (
            s.scalar(
                select(func.count())
                .select_from(Intent)
                .where(Intent.registry_kind == "DIALOGUE_ACT")
            )
            == 14
        )


def test_idempotent_preserve_edits(taxonomy_db):
    with Session(taxonomy_db) as s, s.begin():
        row = s.scalar(select(Intent).where(Intent.code == "NEXT_BUS"))
        identifier = row.id
        row.display_name = "Operator custom display"
    seed_taxonomy(taxonomy_db)
    with Session(taxonomy_db) as s:
        assert s.get(Intent, identifier).display_name == "Operator custom display"
        assert (
            s.scalar(
                select(func.count())
                .select_from(Utterance)
                .where(Utterance.source_type == "TAXONOMY_SEED")
            )
            == 300
        )


def test_legacy_rules_and_unavailable_booking(taxonomy_db):
    with Session(taxonomy_db) as s:
        r = IntentRegistry(s)
        assert r.get("TICKET_FARE").code == "GET_FARE"
        assert r.get("GET_STOPS").code == "ROUTE_STOPS"
        assert "fare" in NLPContentRepository(s).rules()["GET_FARE"]
        response = RTCEnquiryEngine(s).enquire(
            intent="BOOKING_STATUS", travel_date="2026-11-08"
        )
        assert response.status == "UNSUPPORTED" and not response.results
        result = RTCEnquiryEngine(s).enquire(
            intent="TICKET_FARE",
            origin="Vijayawada",
            destination="Guntur",
            travel_date="2026-11-08",
        )
        assert result.intent == "GET_FARE" and result.results


def test_composition_and_examples():
    data = json.loads(Path("training/config/dialogue_acts.yaml").read_text())
    canonical = {
        i["code"]
        for i in json.loads(Path("training/config/intent_registry.yaml").read_text())[
            "intents"
        ]
    }
    assert not canonical.intersection(a["code"] for a in data["dialogue_acts"])
    for composition in data["compositions"]:
        assert set(composition["intents"]) <= canonical
        for target, deps in composition.get("dependencies", {}).items():
            assert target in composition["intents"] and set(deps) <= set(
                composition["intents"]
            )
    examples = [
        json.loads(line)
        for line in Path("training/datasets/phase2a_seed_examples.jsonl")
        .read_text()
        .splitlines()
    ]
    assert len(examples) == len({r["text"].casefold() for r in examples}) == 300
    assert all(r["review_status"] == "PENDING_HUMAN_REVIEW" for r in examples)


def test_taxonomy_api_offline(taxonomy_db, monkeypatch):
    import socket

    def deny(*args, **kwargs):
        raise AssertionError("Unexpected network")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(main, "engine", taxonomy_db)
    with TestClient(main.app) as client:
        assert len(client.get("/api/v1/nlp/intents").json()["data"]) == 60
        assert (
            client.get("/api/v1/nlp/intents/TICKET_FARE").json()["data"]["code"]
            == "GET_FARE"
        )
        assert client.get("/api/v1/nlp/intents/GREETING").status_code == 404
        assert len(client.get("/api/v1/nlp/entities").json()["data"]) == 32
