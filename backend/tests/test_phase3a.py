from datetime import datetime

import pytest
from app import main
from app.domain import Service, Stop
from app.nlp.components import TemporalParser
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp.references import ReferentialResolver, stable_results
from app.nlp.state import ContextOperation, ContextUpdateEngine, ConversationState
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_text_dialogue import NAMES, NOW
from test_text_dialogue import text_db as _fixture

text_db = _fixture


@pytest.mark.parametrize(
    "phrase,key,hour",
    [
        ("after 8 pm", "after", 20),
        ("before 6 am", "before", 6),
        ("around 9:30 pm", "after", 21),
        ("in the next two hours", "before", 12),
    ],
)
def test_time_windows(phrase, key, hour):
    from zoneinfo import ZoneInfo

    now = datetime(2026, 11, 8, 10, tzinfo=ZoneInfo("Asia/Kolkata"))
    value = TemporalParser().parse(phrase, now)
    assert datetime.fromisoformat(value["filters"][key]).hour == hour
    assert datetime.fromisoformat(value["filters"][key]).utcoffset() == now.utcoffset()


def test_midnight_and_invalid_clock():
    from zoneinfo import ZoneInfo

    now = datetime(2026, 11, 8, 23, 59, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert (
        TemporalParser().parse("next available after midnight", now)["travel_date"]
        == "2026-11-09"
    )
    with pytest.raises(ValueError):
        TemporalParser().parse("after 8", now)


def test_context_operations():
    engine = ContextUpdateEngine()
    state = {
        "origin": "a",
        "destination": "b",
        "service_id": "s",
        "trip_id": "t",
        "fare": "5",
        "platform": "2",
        "filters": {},
    }
    changed = engine.apply(
        state, ContextOperation(op="REPLACE_SLOT", slot="destination", value="c")
    )
    assert changed["destination"] == "c" and not any(
        k in changed for k in ("service_id", "trip_id", "fare", "platform")
    )
    assert state["destination"] == "b"
    candidate = engine.apply(
        state,
        ContextOperation(
            op="SET_SLOT", slot="destination", value="c", source="CANDIDATE"
        ),
    )
    assert candidate["destination"] == "b"
    confirmed = engine.apply(
        candidate, ContextOperation(op="CONFIRM_SLOT", slot="destination")
    )
    assert confirmed["destination"] == "c"
    ConversationState.model_validate(confirmed)


def test_reference_tie_and_missing_fare():
    rows = stable_results(
        [{"service_id": "a", "fare": "10.00"}, {"service_id": "b", "fare": None}]
    )
    assert ReferentialResolver().resolve("the cheaper one", {"candidates": rows}) == 0
    with pytest.raises(ValueError):
        ReferentialResolver().resolve(
            "the cheaper one",
            {
                "candidates": stable_results(
                    [
                        {"service_id": "a", "fare": "10"},
                        {"service_id": "b", "fare": "10"},
                    ]
                )
            },
        )
    with pytest.raises(ValueError):
        ReferentialResolver().resolve("this one", {})


def test_bound_owner_api(text_db, monkeypatch):
    monkeypatch.setattr(main, "engine", text_db)
    owner = "x" * 40
    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/conversation/message",
            json={
                "text": "Next bus to Guntur",
                "station_context": "DEMO0",
                "language": "en",
                "owner_token": owner,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        sid = data["session_id"]
        assert "_owner_hash" not in data["context"]
        assert (
            client.get(
                f"/api/v1/conversation/{sid}/context",
                headers={"Authorization": "Bearer " + owner},
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/v1/conversation/{sid}/context",
                headers={"Authorization": "Bearer " + "y" * 40},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/conversation/message",
                json={"text": "How much?", "session_id": sid},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/conversation/reset", json={"text": "reset", "session_id": sid}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/conversation/reset",
                json={"text": "reset", "session_id": sid, "owner_token": owner},
            ).status_code
            == 200
        )


PLANS = [
    ["How much?", "Seats?", "Which platform?"],
    ["AC only", "Clear filters", "How much?"],
    ["Non AC only", "Clear filters", "Seats?"],
    ["Tomorrow morning.", "How much?", "Clear filters"],
    ["Next bus and ticket fare", "Seats?", "Which platform?"],
]


@pytest.mark.parametrize("route", range(20))
@pytest.mark.parametrize("turns", [2, 5, 10])
@pytest.mark.parametrize("plan", PLANS)
def test_300_long_dialogues(text_db, route, turns, plan):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text=f"Next bus to {NAMES[route + 1]}",
                station_context=f"DEMO{route}",
                language="en",
            ),
            NOW,
        )
        origin = first.context["origin"]
        destination = first.context["destination"]
        sid = first.session_id
        revision = first.context["revision"]
        for i in range(turns - 1):
            result = engine.process(
                NLPRequest(text=plan[i % len(plan)], session_id=sid, language="en"), NOW
            )
            assert result.session_id == sid
            assert (
                result.context.get("origin") == origin
                and result.context.get("destination") == destination
            )
            assert result.context["revision"] > revision
            revision = result.context["revision"]
            for enquiry in result.results:
                query = enquiry["query"]
                assert query["origin"] == origin and query["destination"] == destination
                for row in enquiry["results"]:
                    if row.get("service_id"):
                        service = session.get(Service, row["service_id"])
                        assert service is not None
                        stops = list(
                            session.scalars(
                                select(Stop)
                                .where(Stop.route_id == service.route_id)
                                .order_by(Stop.sequence)
                            )
                        )
                        assert (
                            stops[0].station_id == origin
                            and stops[-1].station_id == destination
                        )
            if not result.results:
                assert result.requires_clarification or result.answer


def test_shared_results_and_refinement(text_db, monkeypatch):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        calls = []
        original = engine.orchestrator.engine.enquire

        def invoke(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)

        monkeypatch.setattr(engine.orchestrator.engine, "enquire", invoke)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur and ticket fare",
                station_context="DEMO0",
                language="en",
            ),
            NOW,
        )
        assert len(calls) == 1 and len(first.results) == 2
        assert len(first.context["candidates"]) > 1
        ids = [r["result_id"] for r in first.context["candidates"]]
        removed = engine.process(
            NLPRequest(
                text="Remove the first option",
                session_id=first.session_id,
                language="en",
            ),
            NOW,
        )
        assert [r["result_id"] for r in removed.context["candidates"]] == ids[1:]
        assert removed.context.get("service_id") is None
        selected = engine.process(
            NLPRequest(
                text="The first one.", session_id=first.session_id, language="en"
            ),
            NOW,
        )
        assert selected.context["selection_status"] == "USER_CONFIRMED"
        assert (
            selected.context["service_id"]
            == first.context["candidates"][1]["service_id"]
        )


def test_explicit_time_inherits_selected_date(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur tomorrow",
                station_context="DEMO0",
                language="en",
            ),
            NOW,
        )
        second = engine.process(
            NLPRequest(text="After 8 PM", session_id=first.session_id, language="en"),
            NOW,
        )
        assert second.context["temporal_resolution"]["original_text"] == "After 8 PM"
        assert second.results[0]["query"]["filters"]["after"].startswith(
            "2026-11-09T20:00"
        )
        same = engine.process(
            NLPRequest(
                text="Same time tomorrow", session_id=first.session_id, language="en"
            ),
            NOW,
        )
        assert same.context["travel_date"] == "2026-11-09"
        assert same.context["filters"]["after"].startswith("2026-11-09T20:00")


def test_same_recurring_bus_revalidates_date(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        recurring = first.context["service_id"]
        changed = engine.process(
            NLPRequest(
                text="Same bus tomorrow", session_id=first.session_id, language="en"
            ),
            NOW,
        )
        assert changed.results[0]["query"]["service_id"] == recurring
        assert changed.results[0]["query"]["travel_date"] == "2026-11-09"
        assert changed.context.get("trip_id") is None
        for row in changed.results[0]["results"]:
            assert row["service_id"] == recurring
            assert row["service_date"] == "2026-11-09"


def test_negated_passenger_count(text_db):
    from app.nlp.entities import RTCEntityExtractor

    with Session(text_db) as session:
        extractor = RTCEntityExtractor(session)
        assert (
            extractor.extract("actually i need two seats, not three")["passengers"] == 2
        )
        assert extractor.extract("not three seats, two seats")["passengers"] == 2
        with pytest.raises(ValueError):
            extractor.extract("two seats and three passengers")
        with pytest.raises(ValueError):
            extractor.extract("0 passengers")


def test_arrival_bound_is_not_departure_bound(text_db):
    from zoneinfo import ZoneInfo

    from app.engine import RTCEnquiryEngine

    local = datetime(2026, 11, 8, 10, tzinfo=ZoneInfo("Asia/Kolkata"))
    parsed = TemporalParser().parse("show buses arriving before 10 pm", local)
    assert "arrival_before" in parsed["filters"] and "before" not in parsed["filters"]
    with Session(text_db) as session:
        result = RTCEnquiryEngine(session).enquire(
            intent="NEXT_BUS",
            origin="Vijayawada",
            destination="Guntur",
            travel_date="2026-11-08",
            at=local,
            filters=parsed["filters"],
        )
        assert result.results
        assert all(
            datetime.fromisoformat(parsed["filters"]["arrival_before"])
            > datetime.fromisoformat(r["arrival"])
            for r in result.results
        )
