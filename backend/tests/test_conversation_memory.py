"""Real API/SQLite conversations; fixtures are labelled DEMO, never training data."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from app import main
from app.catalog import Layout, Vehicle, VehicleType
from app.domain import (
    Alias,
    Base,
    Category,
    Fare,
    Operator,
    Route,
    Service,
    Station,
    Stop,
    database,
)
from app.links import ServiceVehicle
from app.nlp_seed import seed_nlp
from app.taxonomy_seed import seed_taxonomy
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_text_dialogue import NOW


@pytest.fixture(scope="module")
def text_db(tmp_path_factory):
    engine = database(
        "sqlite:///" + (tmp_path_factory.mktemp("memory") / "memory.db").as_posix()
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        s.add(Operator(id="operator", code="DEMO-MEMORY", name="DEMO memory operator"))
        s.flush()
        s.add(
            Layout(
                id="layout", name="DEMO layout", seating_capacity=40, berth_capacity=0
            )
        )
        for category in ("express", "luxury", "sleeper"):
            s.add(
                VehicleType(
                    id=category,
                    name="DEMO " + category,
                    ac=category != "express",
                    sleeper=category == "sleeper",
                )
            )
        s.flush()
        s.add_all(
            [
                Category(id="express", operator_id="operator", name="Express"),
                Category(id="luxury", operator_id="operator", name="Super Luxury"),
                Category(id="sleeper", operator_id="operator", name="AC Sleeper"),
            ]
        )
        names = [
            "Vijayawada",
            "Guntur",
            "Tirupati",
            "Tirumala",
            "Nellore",
            "Ongole",
            "Hyderabad",
            "Visakhapatnam",
            "Kakinada",
        ]
        s.add_all(
            Station(id=f"DEMO{i}", code=f"DEMO{i}", name=n) for i, n in enumerate(names)
        )
        s.flush()
        s.add(Alias(station_id="DEMO7", name="Vizag"))
        specs = [
            ("nellore", [0, 5, 4], 480),
            ("tirupati", [0, 5, 2], 490),
            ("hill", [2, 3], 720),
            ("directhill", [0, 3], 900),
            ("hyd", [0, 6], 1200),
            ("vizag", [0, 7], 1100),
            ("kakinada", [0, 8], 1160),
        ]
        for route, ids, departure in specs:
            s.add(Route(id=route, code=route, operator_id="operator"))
            s.flush()
            s.add_all(
                Stop(
                    id=f"{route}-{i}",
                    route_id=route,
                    station_id=f"DEMO{n}",
                    sequence=i,
                    offset_minutes=i * 60,
                    distance_km=i * 50,
                )
                for i, n in enumerate(ids)
            )
            s.flush()
            for index, category in enumerate(("express", "luxury", "sleeper")):
                sid = f"{route}-{category}"
                s.add(
                    Service(
                        id=sid,
                        route_id=route,
                        number=f"DEMO-{route}-{index}",
                        operator_id="operator",
                        category_id=category,
                        departure_minutes=departure + index * 60,
                        valid_from=NOW.date() - timedelta(days=1),
                        valid_to=NOW.date() + timedelta(days=30),
                    )
                )
                s.flush()
                s.add(
                    Vehicle(
                        id=sid,
                        operator_id="operator",
                        type_id=category,
                        layout_id="layout",
                        registration="DEMO-" + sid,
                    )
                )
                s.flush()
                s.add(ServiceVehicle(service_id=sid, vehicle_id=sid))
                if category != "sleeper":
                    for a in range(len(ids) - 1):
                        for b in range(a + 1, len(ids)):
                            s.add(
                                Fare(
                                    service_id=sid,
                                    origin_id=f"DEMO{ids[a]}",
                                    destination_id=f"DEMO{ids[b]}",
                                    amount=101 + index * 104 + a * 7,
                                    valid_from=NOW.date() - timedelta(days=1),
                                    valid_to=NOW.date() + timedelta(days=30),
                                )
                            )
    seed_nlp(engine)
    seed_taxonomy(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def chat(text_db, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)

    monkeypatch.setattr(main, "engine", text_db)
    monkeypatch.setattr(main, "datetime", Clock)
    with TestClient(
        main.app, client=("conversation-memory-" + str(id(monkeypatch)), 50000)
    ) as client:
        yield client


def turn(client, text, previous=None, **extra):
    body = {"text": text, "language": "en", "station_context": "DEMO0", **extra}
    if previous:
        body["session_id"] = previous["session_id"]
    response = client.post("/api/v1/conversation/message", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    if previous:
        assert data["session_id"] == previous["session_id"]
    return data


def test_exact_selected_journey_then_fare(chat):
    first = turn(chat, "How can I reach Nellore?")
    assert len(first["context"]["candidates"]) >= 2
    selected = turn(chat, "2", first)
    chosen = selected["context"]["selected_itinerary"]
    assert chosen["total_fare"] is not None
    fare = turn(chat, "What is the fare?", selected)
    rows = [row for result in fare["results"] for row in result["results"]]
    assert rows and Decimal(str(rows[0].get("amount", rows[0].get("fare")))) == Decimal(
        chosen["total_fare"]
    ), fare


@pytest.mark.parametrize("variant", range(20))
@pytest.mark.parametrize("flow", ["A", "B", "C", "D", "E"])
def test_100_complete_multiturn_scenarios(chat, flow, variant):
    response = None
    origin = "DEMO5" if flow == "A" and variant % 2 else "DEMO0"
    date_phrase = (
        " tomorrow"
        if variant % 3 == 1
        else " on 2026-11-10"
        if variant % 3 == 2
        else ""
    )
    history = []

    def ask(text):
        nonlocal response
        old = response
        response = turn(chat, text, response, station_context=origin)
        assert response["current_context"] == response["context"]
        assert response["context"]["state_version"] == (
            old["context"]["state_version"] + 1 if old else 1
        )
        assert response["context"]["origin_id"]
        assert (
            response["message_id"] and response["response_text"] == response["answer"]
        )
        assert "Demo schedule/data:" not in response["answer"]
        assert response["context"]["last_question"] == text
        history.append(response)
        return response

    if flow == "A":
        ask("Next bus to Nellore?" + date_phrase)
        second = response["context"]["candidates"][1]
        ask(
            [
                "2",
                "Second one.",
                "What about the second bus?",
                "Select the second option.",
            ][variant % 4]
        )
        assert response["selected_journey"]["service_id"] == second["service_id"]
        result_id = response["context"]["selected_result_id"]
        fare = ask("What is the fare?")
        row = fare["results"][0]["results"][0]
        assert row["segments"][0]["service_id"] == second["service_id"]
        assert (
            row["segments"][0]["origin"] == origin
            and row["segments"][0]["destination"] == "DEMO4"
        )
        assert Decimal(row["amount"]) == Decimal(str(second["fare"]))
        ask("Which platform?")
        assert response["results"][0]["query"]["service_id"] == second["service_id"]
        ask("Does it stop at Ongole?")
        assert "recorded stop" in response["answer"]
        assert response["context"]["selected_result_id"] == result_id
    elif flow == "B":
        ask(
            "Any AC bus to Hyderabad tonight?"
            if not date_phrase
            else "Any AC bus to Hyderabad" + date_phrase + " night?"
        )
        ask("Cheapest?")
        assert response["context"]["filters"]["ac"] is True
        ask("How long does it take?")
        ask("What about tomorrow?")
        assert (
            response["context"]["destination"] == "DEMO6"
            and response["context"]["filters"]["ac"] is True
        )
        ask("Is sleeper available?")
        assert (
            response["context"]["destination"] == "DEMO6"
            and response["context"]["filters"]["sleeper"] is True
        )
    elif flow == "C":
        ask("I want to go to Tirumala." + date_phrase)
        ask("Any direct service?")
        ask("What if I change at Tirupati?")
        assert response["context"]["destination"] == "DEMO3"
        ask("Which arrives first?")
        ask("Select the first option.")
        selected = response["selected_journey"]
        assert selected and selected["legs"]
        ask("Fare?")
        row = response["results"][0]["results"][0]
        assert [r["service_id"] for r in row["segments"]] == [
            r["service_id"] for r in selected["legs"]
        ]
        assert Decimal(row["amount"]) == sum(
            Decimal(str(r["fare"])) for r in selected["legs"]
        )
    elif flow == "D":
        ask("Next bus to Vizag." + date_phrase)
        ask("No, I meant Kakinada.")
        assert (
            response["context"]["destination"] == "DEMO8"
            and not response["selected_journey"]
        )
        ask("Only Super Luxury.")
        ask("After 7 PM.")
        ask("What is the fare?")
        assert response["context"]["destination"] == "DEMO8"
        assert all(
            r.get("destination_id", "DEMO8") == "DEMO8"
            for batch in response["results"]
            for r in batch["results"]
        )
    else:
        ask("Show the next three buses.")
        assert len(response["result_set"]) == 3
        first = response["result_set"][0]
        ask("Second one.")
        ask("Actually, the first one.")
        assert response["selected_journey"]["service_id"] == first["service_id"]
        ask("Does that bus have AC?")
        assert response["context"]["selected_result_id"] == first["result_id"]
        assert "AC is not available" in response["answer"]
        ask("Is it cancelled?")
        assert response["context"]["selected_result_id"] == first["result_id"]
    assert len(history) >= 5


OWNER = "memory-owner-capability-" + "a" * 48


def test_missing_selected_fare_is_specific(chat):
    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "3", first)
    answer = turn(chat, "Fare?", selected)
    assert answer["results"][0]["results"][0]["amount"] is None
    assert (
        "fare for that service is not available in the current database"
        in answer["answer"]
    )
    assert "no matching information" not in answer["answer"].lower()


def test_fare_is_refetched_and_not_taken_from_snapshot(chat, text_db):
    from sqlalchemy import select

    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "2", first)
    with Session(text_db) as session, session.begin():
        fare = session.scalar(
            select(Fare).where(
                Fare.service_id == selected["context"]["service_id"],
                Fare.origin_id == "DEMO0",
                Fare.destination_id == "DEMO4",
            )
        )
        old = fare.amount
        fare_id = fare.id
        fare.amount = old + 17
    try:
        answer = turn(chat, "What is the fare?", selected)
        assert Decimal(answer["results"][0]["results"][0]["amount"]) == old + 17
    finally:
        with Session(text_db) as session, session.begin():
            session.get(Fare, fare_id).amount = old


def test_first_message_retry_is_idempotent_and_history_survives_new_request(
    chat, text_db
):
    from uuid import uuid4

    from app.catalog import Message
    from sqlalchemy import func, select

    body = {
        "text": "Next bus to Nellore?",
        "language": "en",
        "station_context": "DEMO0",
        "owner_token": OWNER,
        "client_message_id": str(uuid4()),
        "expected_state_version": 0,
    }
    first = chat.post("/api/v1/conversation/message", json=body)
    assert first.status_code == 200, first.text
    replay = chat.post("/api/v1/conversation/message", json=body)
    assert replay.status_code == 200 and replay.json() == first.json()
    with Session(text_db) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.session_id == first.json()["session_id"])
            )
            == 2
        )
    text_db.dispose()
    restored = chat.post(
        "/api/v1/conversation/state",
        json={"session_id": first.json()["session_id"], "owner_token": OWNER},
    )
    assert restored.status_code == 200, restored.text
    assert len(restored.json()["history"]) == 2
    assert restored.json()["last_message_id"] == body["client_message_id"]
    assert "_owner_hash" not in restored.text and "_receipts" not in restored.text
    changed = chat.post(
        "/api/v1/conversation/message", json={**body, "text": "Only AC"}
    )
    assert changed.status_code == 409


def test_owner_isolation_and_concurrent_state_versions(chat):
    from concurrent.futures import ThreadPoolExecutor
    from uuid import uuid4

    first = turn(
        chat,
        "Next bus to Nellore?",
        owner_token=OWNER,
        client_message_id=str(uuid4()),
        expected_state_version=0,
    )
    wrong = chat.post(
        "/api/v1/conversation/state",
        json={
            "session_id": first["session_id"],
            "owner_token": "other-owner-" + "b" * 48,
        },
    )
    assert wrong.status_code == 403
    wrong = chat.post(
        "/api/v1/conversation/message",
        json={
            "session_id": first["session_id"],
            "text": "Fare?",
            "owner_token": "other-owner-" + "b" * 48,
        },
    )
    assert wrong.status_code == 403

    def submit(text):
        return chat.post(
            "/api/v1/conversation/message",
            json={
                "session_id": first["session_id"],
                "text": text,
                "language": "en",
                "owner_token": OWNER,
                "expected_state_version": 1,
                "client_message_id": str(uuid4()),
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, ["Only AC", "Tomorrow"])) == [200, 409]
    current = chat.post(
        "/api/v1/conversation/state",
        json={"session_id": first["session_id"], "owner_token": OWNER},
    ).json()
    assert current["state_version"] == 2 and len(current["history"]) == 4


def test_date_change_invalidates_selection_and_keeps_time_window(chat):
    first = turn(chat, "Next bus to Nellore tomorrow morning?")
    selected = turn(chat, "2", first)
    changed = turn(chat, "What about 2026-11-10?", selected)
    assert not changed["selected_journey"] and not changed["context"].get(
        "selected_result_id"
    )
    assert changed["context"]["time_window"] == "morning"
    assert changed["context"]["travel_date"] == "2026-11-10"
    assert (
        changed["context"]["result_revision"] > selected["context"]["result_revision"]
    )


def test_public_context_operations_and_private_slot_protection(chat):
    first = turn(chat, "Next bus to Nellore?")
    filtered = turn(
        chat,
        "Next bus",
        first,
        context_action={"op": "SET", "slot": "ac", "value": True},
    )
    assert filtered["context"]["filters"]["ac"] is True
    inherited = turn(
        chat, "Next bus", filtered, context_action={"op": "INHERIT", "slot": "ac"}
    )
    assert inherited["context"]["filters"]["ac"] is True
    cleared = turn(
        chat, "Next bus", inherited, context_action={"op": "CLEAR", "slot": "ac"}
    )
    assert "ac" not in cleared["context"]["filters"]
    invalid = chat.post(
        "/api/v1/conversation/message",
        json={
            "session_id": first["session_id"],
            "text": "Next bus",
            "context_action": {"op": "SET", "slot": "_owner_hash", "value": "hijack"},
        },
    )
    assert invalid.status_code == 422
    invalid = chat.post(
        "/api/v1/conversation/message",
        json={
            "session_id": first["session_id"],
            "text": "Next bus",
            "context_action": {"op": "SET", "slot": "travel_date", "value": {}},
        },
    )
    assert invalid.status_code == 422


def test_personal_expiry_is_configurable_and_reset_clears_server_history(chat, text_db):
    from uuid import uuid4

    from app.catalog import Message
    from sqlalchemy import func, select

    first = turn(
        chat,
        "Next bus to Nellore?",
        session_mode="personal",
        owner_token=OWNER,
        client_message_id=str(uuid4()),
        expected_state_version=0,
    )
    assert datetime.fromisoformat(first["context"]["expires_at"]) == NOW + timedelta(
        days=1
    )
    reset = chat.post(
        "/api/v1/conversation/reset",
        json={"text": "reset", "session_id": first["session_id"], "owner_token": OWNER},
    )
    assert reset.status_code == 200
    with Session(text_db) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.session_id == first["session_id"])
            )
            == 0
        )


def test_platform_added_after_selection_uses_same_service_and_date(chat, text_db):
    from app.operations import DataSource, PlatformAssignment, StationBay, Trip

    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "2", first)
    service = selected["context"]["service_id"]
    with Session(text_db) as session, session.begin():
        session.add(
            DataSource(
                id="memory-source",
                code="MEMORY",
                name="DEMO memory updates",
                operator_id="operator",
                is_demo=True,
            )
        )
        session.add(StationBay(id="memory-bay", station_id="DEMO0", code="DEMO-M2"))
        session.flush()
        trip = Trip(id="memory-trip", service_id=service, service_date=NOW.date())
        session.add(trip)
        session.flush()
        session.add(
            PlatformAssignment(
                trip_id=trip.id,
                bay_id="memory-bay",
                source_id="memory-source",
                effective_at=NOW - timedelta(minutes=1),
                expires_at=NOW + timedelta(hours=4),
                verified=True,
            )
        )
    answer = turn(chat, "Which platform?", selected)
    assert answer["results"][0]["query"]["service_id"] == service
    assert answer["results"][0]["query"]["trip_id"] == "memory-trip"
    assert answer["results"][0]["results"][0]["bay"] == "DEMO-M2"


def test_cancelled_selection_is_reported_then_fare_requires_fresh_options(
    chat, text_db
):
    from app.operations import Trip

    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "2", first)
    with Session(text_db) as session, session.begin():
        trip = session.get(Trip, "memory-trip")
        if not trip:
            trip = Trip(
                id="memory-trip",
                service_id=selected["context"]["service_id"],
                service_date=NOW.date(),
            )
            session.add(trip)
        trip.status = "cancelled"
    try:
        status = turn(chat, "Is it cancelled?", selected)
        assert "cancelled" in status["answer"].lower()
        fare = turn(chat, "Fare?", status)
        assert not fare["selected_journey"] and "cancelled" in fare["answer"].lower()
    finally:
        with Session(text_db) as session, session.begin():
            session.get(Trip, "memory-trip").status = "scheduled"


def test_expiry_redacts_context_and_history_without_exposing_other_owner(chat, text_db):
    from app.catalog import Context, Message
    from app.nlp.pipeline import ConversationManager
    from sqlalchemy import func, select

    first = turn(chat, "Next bus to Nellore?", owner_token=OWNER)
    with Session(text_db) as session, session.begin():
        context = session.scalar(
            select(Context).where(Context.session_id == first["session_id"])
        )
        context.values = {
            **context.values,
            "expires_at": (NOW - timedelta(seconds=1)).isoformat(),
        }
    expired = chat.post(
        "/api/v1/conversation/state",
        json={"session_id": first["session_id"], "owner_token": OWNER},
    )
    assert expired.status_code == 410
    replacement = chat.post(
        "/api/v1/conversation/message",
        json={
            "text": "Fare?",
            "session_id": first["session_id"],
            "owner_token": OWNER,
            "language": "en",
        },
    ).json()
    assert replacement["session_id"] != first["session_id"]
    assert not replacement["context"].get("destination")
    with Session(text_db) as session, session.begin():
        context = session.scalar(
            select(Context).where(Context.session_id == first["session_id"])
        )
        ConversationManager(session).expire(context)
        assert set(context.values) <= {"_owner_hash", "expires_at", "revision"}
        assert (
            session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.session_id == first["session_id"])
            )
            == 0
        )


def test_itinerary_references_previous_and_current_fares(chat, text_db):
    from sqlalchemy import select

    first = turn(chat, "How can I reach Nellore?")
    one = turn(chat, "1", first)
    two = turn(chat, "2", one)
    previous = turn(chat, "Previous one", two)
    assert (
        previous["context"]["selected_result_id"]
        == one["context"]["selected_result_id"]
    )
    # First displayed option becomes more expensive after the list was shown.
    first_id = first["result_set"][0]["legs"][0]["service_id"]
    with Session(text_db) as session, session.begin():
        fare = session.scalar(
            select(Fare).where(
                Fare.service_id == first_id,
                Fare.origin_id == "DEMO0",
                Fare.destination_id == "DEMO4",
            )
        )
        old, fare_id = fare.amount, fare.id
        fare.amount = 9000
    try:
        cheapest = turn(chat, "Cheapest one", previous)
        assert cheapest["selected_journey"]
        assert cheapest["selected_journey"]["legs"][0]["service_id"] != first_id
    finally:
        with Session(text_db) as session, session.begin():
            session.get(Fare, fare_id).amount = old


def test_partial_connection_fare_is_never_presented_as_total(chat):
    first = turn(chat, "I want to go to Tirumala tomorrow")
    options = turn(chat, "What if I change at Tirupati?", first)
    candidate = next(
        (
            i
            for i, r in enumerate(options["result_set"])
            if any(leg.get("fare") is None for leg in r["legs"])
        ),
        None,
    )
    if candidate is None:
        # Ask for sleeper legs, whose fixture deliberately has no fare record.
        options = turn(chat, "Only sleeper", options)
        candidate = 0
    selected = turn(chat, str(candidate + 1), options)
    fare = turn(chat, "Fare?", selected)
    row = fare["results"][0]["results"][0]
    assert row["amount"] is None
    assert "not available" in fare["answer"] or "subtotal" in fare["answer"]


def test_same_service_tomorrow_does_not_keep_old_trip_and_platform_unknown(chat):
    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "1", first)
    platform = turn(chat, "Which platform?", selected)
    assert (
        platform["results"][0]["query"]["service_id"]
        == selected["context"]["service_id"]
    )
    assert platform["results"][0]["results"] == [{"status": "unknown", "bay": None}]
    tomorrow = turn(chat, "Same bus tomorrow?", platform)
    assert (
        tomorrow["context"]["travel_date"]
        == (NOW + timedelta(days=1)).date().isoformat()
    )
    assert not tomorrow["context"].get("trip_id")
    assert all(
        r["service_id"] == selected["context"]["service_id"]
        for r in tomorrow["result_set"]
    )


def test_overnight_boarding_keeps_previous_service_date_and_exact_segment(
    chat, text_db
):
    with Session(text_db) as session, session.begin():
        session.add(
            Route(id="night-memory", code="DEMO-NIGHT-MEMORY", operator_id="operator")
        )
        session.flush()
        session.add_all(
            Stop(
                id=f"night-memory-{i}",
                route_id="night-memory",
                station_id=station,
                sequence=i,
                offset_minutes=offset,
                distance_km=i * 50,
            )
            for i, (station, offset) in enumerate(
                (("DEMO0", 0), ("DEMO5", 150), ("DEMO4", 240))
            )
        )
        session.add(
            Service(
                id="night-memory",
                number="DEMO-NIGHT-MEMORY",
                operator_id="operator",
                category_id="express",
                route_id="night-memory",
                departure_minutes=1410,
                valid_from=NOW.date(),
                valid_to=NOW.date(),
            )
        )
        session.flush()
        session.add(
            Fare(
                service_id="night-memory",
                origin_id="DEMO5",
                destination_id="DEMO4",
                amount=77,
                valid_from=NOW.date(),
                valid_to=NOW.date() + timedelta(days=1),
            )
        )
    first = turn(chat, "Next bus from Ongole to Nellore tomorrow before 3 AM?")
    assert (
        first["result_set"] and first["result_set"][0]["service_id"] == "night-memory"
    )
    selected = turn(chat, "1", first)
    assert selected["selected_journey"]["service_date"] == NOW.date().isoformat()
    assert (
        selected["context"]["travel_date"]
        == (NOW + timedelta(days=1)).date().isoformat()
    )
    fare = turn(chat, "Fare?", selected)
    segment = fare["results"][0]["query"]["segments"][0]
    assert segment["service_date"] == NOW.date().isoformat()
    assert segment["origin"] == "DEMO5" and segment["destination"] == "DEMO4"
    assert Decimal(fare["results"][0]["results"][0]["amount"]) == 77


def test_refining_and_rejecting_results_never_keeps_removed_selection(chat):
    first = turn(chat, "Next bus to Nellore?")
    selected = turn(chat, "1", first)
    removed = turn(chat, "Remove the first option", selected)
    assert not removed["selected_journey"]
    assert removed["context"]["result_revision"] > first["context"]["result_revision"]
    next_selected = turn(chat, "1", removed)
    assert (
        next_selected["selected_journey"]["service_id"]
        == first["result_set"][1]["service_id"]
    )
    rejected = turn(chat, "Not that bus", next_selected)
    assert not rejected["selected_journey"]
    assert rejected["requires_clarification"]


def test_offline_startup_and_eight_turns_in_separate_process(text_db, tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    report = tmp_path / "offline.json"
    script = (
        Path(__file__).resolve().parents[2] / "scripts/verify_conversation_offline.py"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(text_db.url.database),
            "--first-query",
            "Next bus to Nellore tomorrow?",
            "--report",
            str(report),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["passed"] and len(data["turns"]) == 8
    assert data["network"] == "ALL_SOCKET_EGRESS_AND_DNS_BLOCKED_BEFORE_BACKEND_IMPORT"
