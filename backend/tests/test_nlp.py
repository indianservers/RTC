import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.demo import enrich
from app.domain import Base, database
from app.nlp.components import IntentClassifier, LanguageNormalizer
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.seed import seed
from sqlalchemy.orm import Session


@pytest.fixture
def nlp_db(tmp_path):
    engine = database("sqlite:///" + str(tmp_path / "nlp.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    enrich(engine)
    from app.nlp_seed import seed_nlp

    seed_nlp(engine)
    return engine


@pytest.mark.parametrize(
    "phrase,intent",
    [
        ("next bus", "NEXT_BUS"),
        ("last bus", "LAST_BUS"),
        ("first bus", "FIRST_BUS"),
        ("ticket fare", "TICKET_FARE"),
        ("platform", "BUS_PLATFORM"),
    ],
)
@pytest.mark.parametrize(
    "destination",
    [
        "Nellore",
        "Guntur",
        "Tirupati",
        "Tirumala",
        "Vizag",
        "Bezawada",
        "Ongole",
        "Kavali",
        "Kadapa",
        "Kurnool",
        "Eluru",
        "Kakinada",
        "Hyderabad",
        "Anantapur",
        "Srikakulam",
        "Vizianagaram",
        "Machilipatnam",
        "Bhimavaram",
        "Srisailam",
        "Annavaram",
    ],
)
def test_clean_intent_rules(phrase, intent, destination):
    rules = json.loads(Path("config/nlp_rules.json").read_text(encoding="utf-8"))
    assert intent in IntentClassifier(rules).classify(
        LanguageNormalizer().normalize(f"{destination} ki {phrase} eppudu?")
    )


def test_dialogue(nlp_db):
    now = datetime(2026, 11, 8, tzinfo=UTC)
    with Session(nlp_db) as session, session.begin():
        engine = RTCNLPEngine(session)
        result = engine.process(
            NLPRequest(text="Guntur ki next bus eppudu?", station_context="DEMO0"), now
        )
        assert result.results and result.results[0]["results"]
        sid = result.session_id
        follow = engine.process(NLPRequest(text="AC unda?", session_id=sid), now)
        assert follow.context["filters"]["ac"] is True
        corrected = engine.process(
            NLPRequest(text="No, Tirupati.", session_id=sid), now
        )
        assert corrected.context["destination"] != result.context["destination"]
        tomorrow = engine.process(NLPRequest(text="repu podduna", session_id=sid), now)
        assert tomorrow.context["travel_date"] == "2026-11-09"
        assert tomorrow.context["time_window"] == "morning"
        fresh = engine.process(NLPRequest(text="Next bus?"), now)
        assert fresh.state == "AWAITING_DESTINATION"
        assert fresh.session_id != sid


def test_multilingual(nlp_db):
    now = datetime(2026, 11, 8, tzinfo=UTC)
    with Session(nlp_db) as session:
        engine = RTCNLPEngine(session)
        result = engine.process(
            NLPRequest(text="తిరుపతి next bus fare", station_context="DEMO0"),
            now,
            persist=False,
        )
        assert result.language == "mixed"
        assert "NEXT_BUS" in result.intents and "TICKET_FARE" in result.intents
        assert result.context["destination"]
        result = engine.process(
            NLPRequest(text="చివరి బస్సు తిరుమల", station_context="DEMO0"),
            now,
            persist=False,
        )
        assert result.language == "te"
        assert "LAST_BUS" in result.intents


@pytest.mark.parametrize(
    "destination",
    [
        "Guntur",
        "Nellore",
        "Tirupati",
        "Tirumala",
        "Ongole",
        "Kavali",
        "Kadapa",
        "Kurnool",
        "Eluru",
        "Kakinada",
    ],
)
@pytest.mark.parametrize("change", ["AC unda?", "repu podduna", "No, Hyderabad."])
def test_independent_multiturn_scenarios(nlp_db, destination, change):
    now = datetime(2026, 11, 8, tzinfo=UTC)
    with Session(nlp_db) as session, session.begin():
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(text=f"{destination} ki next bus", station_context="DEMO0"), now
        )
        second = engine.process(
            NLPRequest(text=change, session_id=first.session_id), now
        )
        assert second.session_id == first.session_id
        assert second.context["origin"] == first.context["origin"]
        if change == "AC unda?":
            assert second.context["filters"]["ac"] is True
        elif change == "repu podduna":
            assert second.context["travel_date"] == "2026-11-09"
        else:
            assert second.context["destination"] != first.context["destination"]
        independent = engine.process(NLPRequest(text="Next bus?"), now)
        assert independent.requires_clarification
        assert independent.session_id != first.session_id


def test_nlp_api_offline(nlp_db, monkeypatch):
    import socket

    from app import main
    from fastapi.testclient import TestClient

    def deny(*args, **kwargs):
        raise AssertionError("Network attempted")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(main, "engine", nlp_db)
    with TestClient(main.app) as client:
        assert (
            client.get("/api/v1/nlp/status").json()["data"]["muril"]["status"]
            == "NOT_READY"
        )
        body = {"text": "Guntur ki next bus", "station_context": "DEMO0"}
        response = client.post("/api/v1/conversation/message", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["session_id"]
        assert client.post("/api/v1/nlp/interpret", json=body).status_code == 200
        assert (
            client.post(
                "/api/v1/conversation/reset",
                json={"text": "reset", "session_id": response.json()["session_id"]},
            ).status_code
            == 200
        )


def test_database_content_updates_visible_without_restart(nlp_db):
    from app.catalog import Intent, Template, Utterance
    from sqlalchemy import select

    now = datetime(2026, 11, 8, tzinfo=UTC)
    with Session(nlp_db) as session, session.begin():
        engine = RTCNLPEngine(session)
        missing = engine.process(NLPRequest(text="next bus"), now, persist=False)
        template = session.scalar(
            select(Template).where(
                Template.response_status == "AWAITING_DESTINATION",
                Template.language == "en",
            )
        )
        template.text = "Choose your destination from the updated database."
        intent = session.scalar(select(Intent).where(Intent.code == "NEXT_BUS"))
        session.add(
            Utterance(
                intent_id=intent.id, language="en", text="departnow", source_type="RULE"
            )
        )
        session.flush()
        changed = engine.process(NLPRequest(text="departnow"), now, persist=False)
        assert changed.intents == ["NEXT_BUS"]
        assert changed.answer == template.text
        assert changed.answer != missing.answer
        template.active = False
        session.flush()
        assert (
            engine.process(NLPRequest(text="departnow"), now, persist=False).answer
            == ""
        )
