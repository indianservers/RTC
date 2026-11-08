"""Composed multi-turn regression scenarios; checks actual structured DB requests."""

import json
from pathlib import Path

import pytest
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from sqlalchemy.orm import Session
from test_text_dialogue import (
    NAMES,
    NOW,
)
from test_text_dialogue import text_db as _text_db_fixture

text_db = _text_db_fixture

PLANS = [
    ("How much?", "Seats?"),
    ("Seats?", "How much?"),
    ("Which platform?", "How much?"),
    ("The second one.", "How much?"),
    ("The first one.", "How much?"),
    ("Non AC only", "Clear filters"),
    ("AC only", "Clear filters"),
    ("Tomorrow morning.", "How much?"),
    ("Tomorrow morning.", "Which platform?"),
    ("Non AC only", "Tomorrow morning."),
    ("AC only", "Tomorrow morning."),
    ("Tomorrow morning.", "Non AC only"),
    ("Clear filters", "How much?"),
    ("Next bus and ticket fare", "Seats?"),
    ("Seats?", "Which platform?"),
]


@pytest.mark.parametrize("route", range(20))
@pytest.mark.parametrize("plan", PLANS)
def test_300_composed_conversations(text_db, route, plan):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text=f"Next bus to {NAMES[route + 1]}",
                station_context=f"DEMO{route}",
                language="en",
                debug=True,
            ),
            NOW,
        )
        assert first.results and first.results[0]["status"] == "KNOWN"
        origin = first.results[0]["query"]["origin"]
        destination = first.results[0]["query"]["destination"]
        sid = first.session_id
        expected_date = "2026-11-08"
        expected_ac = None
        answer = first
        for text in plan:
            if "Tomorrow" in text:
                expected_date = "2026-11-09"
            if text == "Non AC only":
                expected_ac = False
            elif text == "AC only":
                expected_ac = True
            elif text == "Clear filters":
                expected_ac = None
            selected_before = answer.context.get("service_id")
            answer = engine.process(
                NLPRequest(text=text, session_id=sid, language="en", debug=True), NOW
            )
            assert answer.session_id == sid
            assert (
                answer.context["origin"] == origin
                and answer.context["destination"] == destination
            )
            if text in ("The first one.", "The second one."):
                index = 0 if text == "The first one." else 1
                chosen = first.context["candidates"][index]
                assert answer.context["service_id"] == chosen["service_id"]
                assert chosen["service_number"] in answer.answer
                continue
            if answer.requires_clarification and text in (
                "How much?",
                "Which platform?",
            ):
                # No morning departure was returned: never invent a selected bus/fare/bay.
                assert selected_before is None
                assert not answer.results and answer.answer
                continue
            assert answer.results, (text, answer.model_dump())
            query = answer.results[0]["query"]
            assert query["origin"] == origin and query["destination"] == destination
            assert query["travel_date"] == expected_date
            assert query["filters"]["ac"] == expected_ac
            assert answer.answer
            if text == "Seats?":
                assert "not available" in answer.answer
            if text == "Which platform?":
                assert "not been confirmed" in answer.answer
            if text == "How much?" and expected_ac is None:
                if answer.results[0]["results"]:
                    assert "100.00" in answer.answer
                else:
                    assert answer.state == "NO_RESULTS"
                    assert "100.00" not in answer.answer


def test_frozen_group_boundaries():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (root / "training/datasets/splits/2c-v1/manifest.json").read_text()
    )
    groups = {}
    parents = {}
    for split, item in manifest["files"].items():
        for line in (root / item["path"]).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            group = r["leakage_group"]
            assert group not in groups or groups[group] == split
            groups[group] = split
            parents[r["example_id"]] = split
    assert manifest["independent_test_records"] == 0
    assert (
        sum(v["records"] for v in manifest["files"].values())
        == manifest["source_records"]
    )


def test_health_and_facade(text_db, monkeypatch):
    from app import main
    from app.nlp.inference import EnglishInferenceService
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "engine", text_db)
    with TestClient(main.app) as client:
        data = client.get("/api/v1/nlp/health").json()["data"]
        assert data["database"] == "READY"
        assert data["statistical_model"] == "NOT_APPROVED"
    with Session(text_db) as session:
        service = EnglishInferenceService(session)
        assert service.classify_intent("next bus")["intent"] == "NEXT_BUS"
        assert service.classify_multiple_intents("next bus and fare")
        assert service.identify_dialogue_act("Hello") == ["GREETING"]
        assert service.reset_session("nonexistent")["reset"] is True


def test_features_are_modifiers_not_three_queries(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        response = engine.process(
            NLPRequest(
                text="Cheapest AC sleeper to Guntur tomorrow",
                station_context="DEMO0",
                language="en",
            ),
            NOW,
        )
        assert response.intents == ["CHEAPEST_BUS"]
        assert response.context["filters"]["ac"] is True
        assert response.context["filters"]["sleeper"] is True


def test_parallel_independent_sessions(text_db):
    from concurrent.futures import ThreadPoolExecutor

    def run(route):
        with Session(text_db) as session, session.begin():
            engine = RTCNLPEngine(session)
            first = engine.process(
                NLPRequest(
                    text=f"Next bus to {NAMES[route + 1]}",
                    station_context=f"DEMO{route}",
                    language="en",
                ),
                NOW,
            )
            second = engine.process(
                NLPRequest(
                    text="Non AC only", session_id=first.session_id, language="en"
                ),
                NOW,
            )
            assert second.context["destination"] == first.context["destination"]
            assert second.context["filters"]["ac"] is False
            return second.session_id, second.context["destination"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    assert len({sid for sid, _ in results}) == 4
    assert len({destination for _, destination in results}) == 4
