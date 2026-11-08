"""Database-grounded English dialogue acceptance tests; evaluation-only, not training data."""

from datetime import UTC, datetime, timedelta

import pytest
from app.demo import enrich
from app.domain import Base, Fare, Station, database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp.text_support import registry
from app.nlp_seed import seed_nlp
from app.seed import seed
from sqlalchemy import select
from sqlalchemy.orm import Session

NOW = datetime(2026, 11, 8, 0, 0, tzinfo=UTC)
NAMES = [
    "Vijayawada",
    "Guntur",
    "Tirupati",
    "Tirumala",
    "Nellore",
    "Ongole",
    "Kavali",
    "Rajahmundry",
    "Visakhapatnam",
    "Kakinada",
    "Kurnool",
    "Kadapa",
    "Anantapur",
    "Eluru",
    "Srikakulam",
    "Vizianagaram",
    "Machilipatnam",
    "Bhimavaram",
    "Srisailam",
    "Annavaram",
    "Hyderabad",
]


@pytest.fixture(scope="module")
def text_db(tmp_path_factory):
    engine = database(
        "sqlite:///" + str(tmp_path_factory.mktemp("dialogue") / "test.db")
    )
    Base.metadata.create_all(engine)
    seed(engine)
    enrich(engine)
    seed_nlp(engine)
    from app.taxonomy_seed import seed_taxonomy

    seed_taxonomy(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket

    def deny(*args, **kwargs):
        raise AssertionError("Network is forbidden during text tests")

    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.mark.parametrize("route", range(20))
@pytest.mark.parametrize(
    "pattern",
    [
        "single",
        "fare",
        "multi",
        "tomorrow",
        "correction",
        "non_ac",
        "clear",
        "selection",
        "platform",
        "seats",
        "expiry",
        "independent",
    ],
)
def test_240_database_dialogues(text_db, route, pattern):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        destination = NAMES[route + 1]
        first = engine.process(
            NLPRequest(
                text=f"Next bus to {destination}",
                station_context=f"DEMO{route}",
                debug=True,
                language="en",
            ),
            NOW,
        )
        assert first.results[0]["status"] == "KNOWN"
        query = first.results[0]["query"]
        assert query["intent"] == "NEXT_BUS"
        assert query["travel_date"] == "2026-11-08"
        station_ids = {s.code: s.id for s in session.scalars(select(Station))}
        assert query["origin"] == station_ids[f"DEMO{route}"]
        assert query["destination"] == station_ids[f"DEMO{route + 1}"]
        first_row = first.results[0]["results"][0]
        assert first_row["service_number"] in first.answer
        assert "Demo schedule/data:" in first.answer
        assert "100.00" in first.answer
        sid = first.session_id

        def ask(text, **kwargs):
            return engine.process(
                NLPRequest(text=text, session_id=sid, language="en", debug=True),
                kwargs.get("now", NOW),
            )

        if pattern == "single":
            assert first.debug["database_function"] == "RTCEnquiryEngine.enquire"
            assert first.debug["matching_service_ids"]
            assert first.debug["queries"][0] == query
        elif pattern == "fare":
            r = ask("How much?")
            assert r.results[0]["query"]["service_id"] == first.context["service_id"]
            assert "fare INR 100.00" in r.answer
        elif pattern == "multi":
            r = ask(f"Next bus to {destination} and ticket fare")
            assert {"NEXT_BUS", "TICKET_FARE"} <= set(r.intents)
            assert len(r.results) == 2 and "fare INR 100.00" in r.answer
        elif pattern == "tomorrow":
            r = ask("Tomorrow morning.")
            assert r.context["destination"] == first.context["destination"]
            assert r.results[0]["query"]["travel_date"] == "2026-11-09"
            assert "T06:00:00" in r.results[0]["query"]["at"]
            assert "T12:00:00" in r.results[0]["query"]["filters"]["before"]
        elif pattern == "correction":
            new = NAMES[(route + 3) % 21]
            r = ask(f"No, {new}.")
            assert r.context["destination"] == station_ids[f"DEMO{(route + 3) % 21}"]
            assert r.results[0]["query"]["service_id"] is None
            assert not r.results[0]["results"]
            assert "No matching information" in r.answer
        elif pattern == "non_ac":
            r = ask("Non AC only")
            assert r.results[0]["query"]["filters"]["ac"] is False
            assert r.context["destination"] == first.context["destination"]
            # Seed deliberately has no vehicle-type assertion: unknown must not count as non-AC.
            assert not r.results[0]["results"]
        elif pattern == "clear":
            ask("AC only")
            r = ask("Clear filters")
            assert r.context["filters"].get("ac") is None
            assert r.results[0]["query"]["filters"]["ac"] is None
        elif pattern == "selection":
            chosen = first.context["candidates"][1]
            r = ask("The second one.")
            assert r.context["service_id"] == chosen["service_id"]
            assert chosen["service_number"] in r.answer
            fare = ask("How much?")
            assert fare.results[0]["query"]["service_id"] == chosen["service_id"]
            assert "fare INR 100.00" in fare.answer
        elif pattern == "platform":
            r = ask("Is the platform still the same?")
            assert r.results[0]["query"]["service_id"] == first.context["service_id"]
            assert "The platform has not been confirmed." in r.answer
            assert r.answer.startswith("Demo schedule/data:")
        elif pattern == "seats":
            r = ask("Seats?")
            assert r.results[0]["query"]["service_id"] == first.context["service_id"]
            assert "Seat availability information is not available." in r.answer
        elif pattern == "expiry":
            r = ask("How much?", now=NOW + timedelta(minutes=16))
            assert r.session_id != sid and r.requires_clarification
            assert "destination" not in r.context and not r.results
        elif pattern == "independent":
            r = engine.process(NLPRequest(text="How much?", language="en"), NOW)
            assert r.session_id != sid and r.requires_clarification
            assert r.state == "AWAITING_DESTINATION"


@pytest.mark.parametrize("record", registry(), ids=lambda r: r["code"])
def test_all_60_registry_routes(text_db, record):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        r = engine.process(
            NLPRequest(text=record["examples"][0], language="en"), NOW, persist=False
        )
        assert r.intents == [record.get("backend_code") or record["code"]]
        if not record.get("backend_code"):
            assert r.results[0]["status"] == "UNSUPPORTED"
            assert "does not support" in r.answer
        else:
            assert r.requires_clarification or r.results


@pytest.mark.parametrize(
    "text",
    [
        "When is the bus?",
        "Is it AC?",
        "How much?",
        "Tomorrow?",
        "The second one.",
        "Not that bus.",
        "Actually, Tirumala.",
        "Only AC and no AC",
        "cricket score please",
    ],
)
def test_targeted_clarifications(text_db, text):
    with Session(text_db) as session:
        r = RTCNLPEngine(session).process(NLPRequest(text=text, language="en"), NOW)
        assert r.requires_clarification
        assert not r.results and r.answer
        assert not r.debug


def test_unknown_fare_and_reset(text_db):
    with Session(text_db) as session:
        for row in session.scalars(select(Fare)):
            row.active = False
        session.flush()
        engine = RTCNLPEngine(session)
        r = engine.process(
            NLPRequest(
                text="Ticket fare to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        assert "Fare information is not available." in r.answer
        cleared = engine.process(
            NLPRequest(text="reset", session_id=r.session_id, language="en"), NOW
        )
        assert not cleared.context.get("destination")
        after = engine.process(
            NLPRequest(text="How much?", session_id=r.session_id, language="en"), NOW
        )
        assert after.requires_clarification


def test_switch_station_and_out_of_scope(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        r = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        changed = engine.process(
            NLPRequest(text="from Tirupati", session_id=r.session_id, language="en"),
            NOW,
        )
        assert changed.context["origin"] != r.context["origin"]
        assert changed.results[0]["query"]["service_id"] is None
        unrelated = engine.process(
            NLPRequest(text="weather please", session_id=r.session_id, language="en"),
            NOW,
        )
        assert unrelated.requires_clarification and not unrelated.results


def test_cross_midnight_actual_database(text_db):
    late = datetime(2026, 11, 8, 17, 0, tzinfo=UTC)  # 22:30 local
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        r = engine.process(
            NLPRequest(
                text="Next bus to Bhimavaram", station_context="DEMO16", language="en"
            ),
            late,
        )
        row = r.results[0]["results"][0]
        assert row["service_number"] == "DEMO37"
        assert row["departure"].startswith("2026-11-08T22:49")
        assert row["arrival"].startswith("2026-11-09T01:49")
        after = engine.process(
            NLPRequest(text="Arrival time?", session_id=r.session_id, language="en"),
            late,
        )
        assert "9 Nov 2026 at 1:49 AM" in after.answer
        assert after.results[0]["query"]["service_id"] == r.context["service_id"]


def test_contradiction_does_not_erase_context(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        r = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        conflict = engine.process(
            NLPRequest(
                text="Only AC and no AC", session_id=r.session_id, language="en"
            ),
            NOW,
        )
        assert conflict.requires_clarification and not conflict.results
        assert conflict.context["destination"] == r.context["destination"]
        assert "Contradictory" in conflict.answer


def test_unknown_destination_never_reuses_previous(text_db):
    with Session(text_db) as session:
        engine = RTCNLPEngine(session)
        first = engine.process(
            NLPRequest(
                text="Next bus to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        bad = engine.process(
            NLPRequest(
                text="Next bus to ImaginaryTown",
                session_id=first.session_id,
                language="en",
            ),
            NOW,
        )
        assert bad.requires_clarification and not bad.results
        assert "Which destination station" in bad.answer


def test_api_debug_is_opt_in(text_db, monkeypatch):
    from app import main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "engine", text_db)
    with TestClient(main.app) as client:
        payload = {
            "text": "Next bus to Guntur",
            "station_context": "DEMO0",
            "language": "en",
        }
        response = client.post("/api/v1/conversation/message", json=payload)
        assert response.status_code == 200
        assert not response.json()["debug"]
        response = client.post(
            "/api/v1/conversation/message", json=dict(payload, debug=True)
        )
        assert response.status_code == 200
        assert (
            response.json()["debug"]["database_function"] == "RTCEnquiryEngine.enquire"
        )
