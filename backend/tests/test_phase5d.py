"""250 database-backed recovery/failure scenarios; never production training data."""

from datetime import timedelta
from uuid import uuid4

import pytest
from app import main
from app.catalog import Context
from app.domain import Station, database
from sqlalchemy.orm import Session
from test_conversation_memory import NOW, OWNER, turn
from test_conversation_memory import chat as _chat
from test_conversation_memory import text_db as _text_db

chat = _chat
text_db = _text_db
ROOT = {"Authorization": "Bearer phase5d-root"}


@pytest.mark.parametrize("variant", range(10))
@pytest.mark.parametrize(
    "family",
    [
        "intent_last",
        "entity",
        "date",
        "wrong_bus",
        "fare_repair",
        "fare_missing",
        "platform_missing",
        "fare_limit",
        "time_window",
        "coverage",
        "direct",
        "ambiguous_station",
        "ambiguous_bus",
        "conflict",
        "out_of_scope",
        "unsupported",
        "model_unavailable",
        "database_unavailable",
        "feedback",
        "review",
        "export",
        "wrong_owner",
        "privacy",
        "data_error",
        "expiry",
    ],
)
def test_250_recovery_scenarios(chat, text_db, monkeypatch, tmp_path, family, variant):
    from app.nlp import feedback

    monkeypatch.setattr(feedback, "datetime", main.datetime)
    monkeypatch.setenv("RTC_ADMIN_TOKEN", "phase5d-root")
    monkeypatch.setenv("RTC_FEEDBACK_RETAIN_TEXT", "1")
    day = (NOW + timedelta(days=variant)).date().isoformat()
    first = turn(chat, f"Next bus to Nellore on {day}?", owner_token=OWNER)
    response = first

    def ask(text):
        nonlocal response
        previous = response
        response = turn(chat, text, previous, owner_token=OWNER)
        assert (
            response["context"]["state_version"]
            == previous["context"]["state_version"] + 1
        )
        return response

    def submit(target=None, **extra):
        target = target or response
        return chat.post(
            "/api/v1/conversation/feedback",
            json={
                "session_id": target["session_id"],
                "message_id": target["message_id"],
                "owner_token": OWNER,
                "category": "WRONG_INTENT",
                "retain_question": True,
                **extra,
            },
        )

    def label(identifier, group="MODEL_ERROR", status="APPROVED_FOR_TRAINING"):
        return chat.post(
            f"/api/v1/admin/nlp/reviews/{identifier}/review",
            headers=ROOT,
            json={
                "expected_version": 1,
                "status": status,
                "error_group": group,
                "error_category": "INTENT_MISCLASSIFICATION"
                if group == "MODEL_ERROR"
                else "DATA_NOT_AVAILABLE",
                "corrected_intent": "GET_FARE",
                "notes": "Authored DEMO regression review; not independent passenger evidence",
                "split": "train",
            },
        )

    if family == "intent_last":
        ask("No, I meant the last bus.")
        assert (
            response["intents"] == ["LAST_BUS"]
            and response["context"]["destination"] == "DEMO4"
        )
        assert response["reliability"]["repair"] == "INTENT_CORRECTION"
        assert response["result_set"][-1]["service_id"] == "nellore-sleeper"
    elif family == "entity":
        ask("I said Tirumala, not Tirupati.")
        assert (
            response["context"]["destination"] == "DEMO3"
            and not response["selected_journey"]
        )
    elif family == "date":
        ask("2")
        ask("No, tomorrow morning.")
        assert (
            response["context"]["travel_date"]
            == (NOW + timedelta(days=1)).date().isoformat()
        )
        assert (
            response["context"]["time_window"] == "morning"
            and not response["selected_journey"]
        )
    elif family == "wrong_bus":
        ask("2")
        ask("That's the wrong bus.")
        assert response["requires_clarification"] and not response["selected_journey"]
        ask("1")
        assert (
            response["selected_journey"]["service_id"]
            == first["result_set"][0]["service_id"]
        )
    elif family == "fare_repair":
        ask("2")
        ask("I asked for the fare, not the timing.")
        assert response["intents"] == ["TICKET_FARE"]
        assert float(response["results"][0]["results"][0]["amount"]) == 205
        assert response["results"][0]["query"]["service_id"] == "nellore-luxury"
    elif family == "fare_missing":
        ask("3")
        ask("Fare?")
        assert response["results"][0]["results"][0]["amount"] is None
        assert (
            response["reliability"]["error_category"] == "DATA_NOT_AVAILABLE"
            and response["reliability"]["failure_group"] == "DATA_ERROR"
        )
    elif family == "platform_missing":
        ask("2")
        ask("Which platform?")
        assert response["results"][0]["results"][0]["bay"] is None
        assert response["reliability"]["error_category"] == "DATA_NOT_AVAILABLE"
    elif family == "fare_limit":
        ask("Under 1")
        assert (
            response["state"] == "NO_RESULTS"
            and response["context"]["filters"]["max_fare"] == "1"
        )
        assert any(
            d["code"] == "FARE_LIMIT" and d["evidence_count"] > 0
            for d in response["reliability"]["diagnosis"]
        )
        assert response["reliability"]["failure_group"] == "DATA_ERROR"
    elif family == "time_window":
        ask("Before 7 AM")
        assert any(
            d["code"] == "TIME_WINDOW" for d in response["reliability"]["diagnosis"]
        )
        assert response["context"]["filters"]["before"].endswith("07:00:00+05:30")
    elif family == "coverage":
        ask("Next bus on 2027-12-01?")
        assert response["reliability"]["diagnosis"][0]["code"] == "OUTSIDE_COVERAGE"
    elif family == "direct":
        ask("Next bus to Guntur?")
        assert response["reliability"]["diagnosis"][0]["code"] == "NO_DIRECT_ROUTE"
    elif family == "ambiguous_station":
        with Session(text_db) as session, session.begin():
            name = "DEMO Central " + str(uuid4())
            session.add_all(
                [
                    Station(code=str(uuid4()), name=name),
                    Station(code=str(uuid4()), name=name),
                ]
            )
        ask("Next bus to " + name)
        assert (
            response["requires_clarification"]
            and response["reliability"]["error_category"] == "ENTITY_RESOLUTION_ERROR"
        )
        assert response["context"]["destination"] == "DEMO4"
    elif family == "ambiguous_bus":
        ask("2")
        ask("The other one")
        assert (
            response["requires_clarification"]
            and response["selected_journey"]["service_id"] == "nellore-luxury"
        )
    elif family == "conflict":
        ask("First or next bus?")
        assert (
            response["requires_clarification"]
            and len(response["clarification_choices"]) == 2
            and not response["results"]
        )
        ask("Next bus")
        ask("Only AC and non AC")
        assert response["reliability"]["error_category"] == "CONTRADICTORY_FILTERS"
    elif family == "out_of_scope":
        ask("2")
        ask("Tell me a joke")
        assert (
            response["reliability"]["confidence_state"] == "OUT_OF_SCOPE"
            and not response["results"]
            and response["selected_journey"]["service_id"] == "nellore-luxury"
        )
    elif family == "unsupported":
        ask("Booking status")
        assert (
            response["results"][0]["status"] == "UNSUPPORTED"
            and response["reliability"]["confidence_state"] == "UNSUPPORTED"
        )
    elif family == "model_unavailable":
        ask("zxyqu unknown utterance")
        assert (
            response["reliability"]["confidence_state"] == "LOW_CONFIDENCE"
            and response["reliability"]["probability"] is None
        )
    elif family == "database_unavailable":
        empty = database("sqlite:///" + (tmp_path / "unavailable.db").as_posix())
        monkeypatch.setattr(main, "engine", empty)
        failed = chat.post(
            "/api/v1/conversation/message",
            json={
                "text": "Fare?",
                "session_id": response["session_id"],
                "owner_token": OWNER,
            },
        )
        assert (
            failed.status_code == 503
            and failed.json()["error"]["code"] == "DATABASE_ERROR"
        )
        monkeypatch.setattr(main, "engine", text_db)
        empty.dispose()
        ask("2")
        ask("Fare?")
        assert float(response["results"][0]["results"][0]["amount"]) == 205
    elif family in {
        "feedback",
        "review",
        "export",
        "wrong_owner",
        "privacy",
        "data_error",
    }:
        ask("2")
        ask("Fare?")
        if family == "wrong_owner":
            assert submit(owner_token="not-the-owner-" + "x" * 48).status_code == 403
            assert chat.get("/api/v1/admin/nlp/reviews").status_code == 401
        else:
            if family == "privacy":
                monkeypatch.setenv("RTC_FEEDBACK_RETAIN_TEXT", "0")
            saved = submit()
            assert saved.status_code == 200, saved.text
            identifier = saved.json()["id"]
            assert submit().json()["duplicate"] is True
            queue = chat.get("/api/v1/admin/nlp/reviews?limit=200", headers=ROOT).json()
            record = next(r for r in queue["data"] if r["id"] == identifier)
            assert record["operator_id"] == "operator" and record[
                "predicted_intents"
            ] == ["TICKET_FARE"]
            assert not any(
                k in str(record) for k in ("owner_token", "_owner_hash", "_receipts")
            )
            if family == "privacy":
                assert record["text"] is None and label(identifier).status_code == 422
            elif family == "data_error":
                assert label(identifier, group="DATA_ERROR").status_code == 422
                assert (
                    label(
                        identifier, group="DATA_ERROR", status="NEEDS_DATA_FIX"
                    ).status_code
                    == 200
                )
            elif family in {"review", "export"}:
                approved = label(identifier)
                assert approved.status_code == 200, approved.text
                assert approved.json()["data"]["training_eligible"]
                export = chat.get("/api/v1/admin/nlp/export", headers=ROOT)
                assert export.status_code == 200
                assert (
                    '"approval_status": "APPROVED_FOR_TRAINING"' in export.text
                    and "owner_token" not in export.text
                )
                stale = label(identifier)
                assert stale.status_code == 409
            else:
                assert record["status"] == "NEW" and not record["training_eligible"]
    else:
        ask("2")
        with Session(text_db) as session, session.begin():
            context = session.scalar(
                __import__("sqlalchemy")
                .select(Context)
                .where(Context.session_id == response["session_id"])
            )
            context.values = {
                **context.values,
                "expires_at": (NOW - timedelta(seconds=1)).isoformat(),
            }
        assert submit().status_code == 410
        restore = chat.post(
            "/api/v1/conversation/state",
            json={"session_id": response["session_id"], "owner_token": OWNER},
        )
        assert restore.status_code == 410


def test_no_ac_diagnosis_does_not_relax_the_request(chat, text_db):
    from app.catalog import VehicleType
    from sqlalchemy import select

    with Session(text_db) as session, session.begin():
        rows = list(session.scalars(select(VehicleType)))
        old = {r.id: r.ac for r in rows}
        for row in rows:
            row.ac = False
    try:
        first = turn(chat, "Next bus to Nellore tomorrow?", owner_token=OWNER)
        result = turn(chat, "Only AC", first, owner_token=OWNER)
        assert (
            result["state"] == "NO_RESULTS"
            and result["context"]["filters"]["ac"] is True
        )
        assert result["reliability"]["diagnosis"][0]["code"] == "CATEGORY_RESTRICTION"
        assert result["reliability"]["diagnosis"][0]["constraint_changed"] is False
    finally:
        with Session(text_db) as session, session.begin():
            for identifier, value in old.items():
                session.get(VehicleType, identifier).ac = value


def test_retention_redacts_opt_in_question(chat, text_db, monkeypatch):
    from app.nlp import feedback
    from app.records import Audit

    monkeypatch.setenv("RTC_ADMIN_TOKEN", "phase5d-root")
    monkeypatch.setenv("RTC_FEEDBACK_RETAIN_TEXT", "1")
    monkeypatch.setattr(feedback, "datetime", main.datetime)
    first = turn(chat, "Next bus to Nellore tomorrow?", owner_token=OWNER)
    saved = chat.post(
        "/api/v1/conversation/feedback",
        json={
            "session_id": first["session_id"],
            "message_id": first["message_id"],
            "owner_token": OWNER,
            "category": "NOT_HELPFUL",
            "retain_question": True,
        },
    )
    assert saved.status_code == 200
    identifier = saved.json()["id"]
    with Session(text_db) as session, session.begin():
        row = session.get(Audit, identifier)
        row.new_values = {
            **row.new_values,
            "expires_at": (NOW - timedelta(days=1)).isoformat(),
        }
    result = chat.post("/api/v1/admin/nlp/retention", headers=ROOT)
    assert result.status_code == 200 and result.json()["redacted"] >= 1
    row = next(
        r
        for r in chat.get("/api/v1/admin/nlp/reviews?limit=200", headers=ROOT).json()[
            "data"
        ]
        if r["id"] == identifier
    )
    assert (
        row["anonymized"]
        and "text" not in row
        and "context" not in row
        and not row["training_eligible"]
    )


def test_expired_platform_is_identified_without_confirming_old_bay(chat, text_db):
    from app.operations import DataSource, PlatformAssignment, StationBay, Trip

    sid = "nellore-express"
    tag = uuid4().hex
    with Session(text_db) as session, session.begin():
        source = DataSource(
            id=str(uuid4()),
            code=tag,
            name="DEMO stale platform evidence",
            operator_id="operator",
            is_demo=True,
        )
        bay = StationBay(id=str(uuid4()), station_id="DEMO0", code="DEMO-OLD")
        session.add_all([source, bay])
        session.flush()
        trip = Trip(id=str(uuid4()), service_id=sid, service_date=NOW.date())
        session.add(trip)
        session.flush()
        session.add(
            PlatformAssignment(
                trip_id=trip.id,
                bay_id=bay.id,
                source_id=source.id,
                effective_at=NOW - timedelta(hours=2),
                expires_at=NOW - timedelta(minutes=1),
                verified=True,
            )
        )
    first = turn(chat, "Next bus to Nellore?", owner_token=OWNER)
    selected = turn(chat, "1", first, owner_token=OWNER)
    answer = turn(chat, "Which platform?", selected, owner_token=OWNER)
    assert answer["results"][0]["results"][0]["bay"] is None
    assert answer["reliability"]["error_category"] == "STALE_OPERATIONAL_DATA"
    assert answer["reliability"]["diagnosis"][0]["code"] == "STALE_PLATFORM_RECORD"


def test_filter_after_platform_returns_new_journey_options(chat):
    first = turn(chat, "Next bus to Nellore tomorrow?", owner_token=OWNER)
    selected = turn(chat, "2", first, owner_token=OWNER)
    platform = turn(chat, "Which platform?", selected, owner_token=OWNER)
    budget = turn(chat, "Under 1", platform, owner_token=OWNER)
    assert budget["intents"] == ["NEXT_BUS"] and budget["state"] == "NO_RESULTS"
    assert (
        budget["context"]["filters"]["max_fare"] == "1"
        and not budget["selected_journey"]
    )
    assert budget["reliability"]["diagnosis"][0]["code"] == "FARE_LIMIT"
