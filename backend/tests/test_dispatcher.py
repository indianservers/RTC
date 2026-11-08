"""Dispatcher integration against real SQLite and optional local PostgreSQL."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.domain import Service, Station, Stop
from app.operations import DataSource, StationBay, Trip
from app.records import Audit
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_data_management import ROOT
from test_data_management import managed as _managed

managed = _managed


@pytest.fixture
def ops(managed):
    client, engine, _reviewer = managed
    day = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    with Session(engine) as s, s.begin():
        s.add(
            Station(
                id="mid", code="MID", name="DEMO intermediate", dataset_source="DEMO"
            )
        )
        s.add(
            DataSource(
                id="dispatch-source",
                code="DISPATCH",
                name="DEMO dispatcher desk",
                operator_id="op-a",
                is_demo=True,
                is_official=False,
                dataset_source="DEMO",
            )
        )
        s.flush()
        s.get(Stop, "stop-b").sequence = 2
        s.flush()
        s.add(
            Stop(
                id="stop-mid",
                route_id="route",
                station_id="mid",
                sequence=1,
                offset_minutes=60,
                distance_km=50,
                dataset_source="DEMO",
            )
        )
        s.add_all(
            [
                StationBay(id="bay1", station_id="a", code="1", dataset_source="DEMO"),
                StationBay(id="bay2", station_id="a", code="2", dataset_source="DEMO"),
                StationBay(
                    id="bay-b", station_id="b", code="B1", dataset_source="DEMO"
                ),
            ]
        )
        s.add(
            Trip(
                id="dispatch-trip",
                service_id="svc",
                service_date=day,
                dataset_source="DEMO",
            )
        )
    caps = {}
    for username, role, stations in (
        ("dispatch-user", "DISPATCHER", ["a", "b", "mid"]),
        ("supervisor", "STATION_SUPERVISOR", ["a", "b", "mid"]),
        ("viewer", "OPERATIONS_VIEWER", ["a"]),
        ("station-a-only", "DISPATCHER", ["a"]),
    ):
        response = client.post(
            "/api/v1/admin/data/users",
            headers=ROOT,
            json={
                "username": username,
                "role": role,
                "operator_ids": ["op-a"],
                "station_ids": stations,
            },
        )
        assert response.status_code == 201, response.text
        caps[username] = {"Authorization": "Bearer " + response.json()["data"]["token"]}
    return client, engine, day, caps


def submit(
    ops, kind, details=None, station="a", headers=None, expected=200, **override
):
    client, engine, _, caps = ops
    with Session(engine) as s:
        version = s.get(Trip, "dispatch-trip").operational_version
    body = {
        "event_type": kind,
        "station_id": station,
        "source_id": "dispatch-source",
        "expected_version": version,
        "idempotency_key": str(uuid4()),
        "occurred_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "reason": "DEMO locally observed operator update",
        "details": details or {},
    }
    body.update(override)
    response = client.post(
        "/api/v1/operations/trips/dispatch-trip/events",
        headers=headers or caps["dispatch-user"],
        json=body,
    )
    assert response.status_code == expected, response.text
    return response.json().get("data", response.json()), body


def board(ops, station="a", **params):
    client, _, day, _ = ops
    response = client.get(
        "/api/v1/operations/board",
        params={"station_id": station, "service_date": day.isoformat(), **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_scheduled_board_does_not_infer_departure(ops):
    row = board(ops)["data"][0]
    assert row["status"] == "SCHEDULED" and row["actual_departure"] is None
    assert row["gps_status"] == "UNKNOWN"
    assert board(ops)["counts"]["scheduled_departures"] == 1


def test_delay_eta_and_boarding_are_orthogonal(ops):
    submit(ops, "DELAYED", {"delay_minutes": 20})
    row = board(ops)["data"][0]
    assert row["delay_minutes"] == 20 and row["estimated_departure"]
    submit(ops, "BOARDING")
    row = board(ops)["data"][0]
    assert row["phase"] == "BOARDING" and row["delay_minutes"] == 20
    client, engine, _, _ = ops
    from app.nlp_seed import seed_nlp
    from app.taxonomy_seed import seed_taxonomy

    seed_nlp(engine)
    seed_taxonomy(engine)
    answer = client.post(
        "/api/v1/conversation/message",
        json={
            "text": "Is service DEMO-1 delayed?",
            "language": "en",
            "station_context": "a",
        },
    ).json()
    assert (
        "BUS_DELAY" in answer["intents"]
        and "20" in answer["answer"]
        and "Revised departure" in answer["answer"]
    ), answer


def test_platform_reassignment_updates_existing_passenger_api_and_history(ops):
    _client, engine, _, _ = ops
    submit(ops, "PLATFORM", {"bay_id": "bay1"})
    submit(ops, "PLATFORM", {"bay_id": "bay2"})
    from app.enquiry import Enquiry

    with Session(engine) as s:
        assert (
            Enquiry(s).get_platform_assignment("dispatch-trip", "a", datetime.now(UTC))[
                "bay"
            ]
            == "2"
        )
        assert (
            len(list(s.scalars(select(Audit).where(Audit.entity_type == "operations"))))
            == 2
        )
    assert board(ops)["data"][0]["platform"]["kind"] == "DISPATCHER_CONFIRMED"


def test_arrival_and_departure_at_intermediate_stop(ops):
    submit(ops, "ARRIVED_AT_STOP", station="mid")
    assert board(ops, "mid")["data"][0]["actual_arrival"]
    submit(ops, "DEPARTED_FROM_STOP", station="mid")
    assert board(ops, "mid")["data"][0]["actual_departure"]
    submit(ops, "ARRIVED_AT_STOP", station="a", expected=409)


@pytest.mark.parametrize("kind", ["CANCELLED", "SUSPENDED"])
def test_cancel_excludes_journeys_and_reinstatement_requires_independent_supervisor(
    ops, kind
):
    from app.enquiry import Enquiry, JourneyQuery

    _client, engine, day, caps = ops
    submit(ops, kind)
    assert board(ops)["data"][0]["status"] == kind
    with Session(engine) as s:
        rows = Enquiry(s).get_next_buses(
            JourneyQuery(
                origin="a",
                destination="b",
                at=datetime.combine(day, datetime.min.time(), ZoneInfo("Asia/Kolkata")),
            )
        )
        assert not any(r["trip_id"] == "dispatch-trip" for r in rows)
    submit(ops, "BOARDING", expected=409)
    submit(ops, "REINSTATE_REQUEST")
    submit(ops, "REINSTATE", expected=403)
    submit(ops, "REINSTATE", headers=caps["supervisor"])
    assert board(ops)["data"][0]["status"] == "SCHEDULED"


@pytest.mark.parametrize("kind", ["READY", "IN_TRANSIT", "COMPLETED"])
def test_invalid_transition_is_rejected(ops, kind):
    submit(ops, kind, expected=409)


def test_duplicate_idempotency_is_exact_and_version_conflicts(ops):
    client, _, _, caps = ops
    result, body = submit(ops, "BOARDING")
    duplicate = client.post(
        "/api/v1/operations/trips/dispatch-trip/events",
        headers=caps["dispatch-user"],
        json=body,
    )
    assert (
        duplicate.status_code == 200 and duplicate.json()["data"]["id"] == result["id"]
    )
    changed = {**body, "reason": "different reason"}
    assert (
        client.post(
            "/api/v1/operations/trips/dispatch-trip/events",
            headers=caps["dispatch-user"],
            json=changed,
        ).status_code
        == 409
    )
    submit(ops, "READY", expected_version=0, expected=409)


def test_operator_station_viewer_and_missing_auth_are_blocked(ops):
    client, _, _, caps = ops
    submit(ops, "BOARDING", station="mid", headers=caps["station-a-only"], expected=403)
    submit(ops, "BOARDING", headers=caps["viewer"], expected=403)
    submit(ops, "BOARDING", headers={"Authorization": "Bearer invalid"}, expected=401)
    response = client.get(
        "/api/v1/operations/events?station_id=a&operator_id=op-b",
        headers=caps["dispatch-user"],
    )
    assert response.status_code == 403


def test_stale_eta_and_missing_gps_remain_explicit(ops):
    from app.status import OperationalStatusEngine

    _client, engine, _, _ = ops
    submit(
        ops,
        "DELAYED",
        {"delay_minutes": 10},
        occurred_at=(datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )
    row = board(ops)["data"][0]
    assert row["delay_status"] == "STALE" and row["estimated_departure"] is None
    with Session(engine) as s:
        status = OperationalStatusEngine(s).status("dispatch-trip", datetime.now(UTC))
        assert status["delay_status"] == "STALE" and status["gps_status"] == "UNKNOWN"


def test_out_of_order_events_and_actual_order(ops):
    submit(ops, "ARRIVED_AT_STOP")
    submit(
        ops,
        "DEPARTED_FROM_STOP",
        occurred_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        expected=409,
    )
    submit(ops, "DEPARTED_FROM_STOP")
    submit(ops, "BOARDING", expected=409)


def test_platform_invalid_reference_and_conflict(ops):
    _client, engine, day, _ = ops
    submit(ops, "PLATFORM", {"bay_id": "bay-b"}, expected=422)
    submit(ops, "PLATFORM", {"bay_id": "bay1"})
    with Session(engine) as s, s.begin():
        s.add(
            Service(
                id="svc-2",
                operator_id="op-a",
                route_id="route",
                category_id="cat",
                number="DEMO2",
                departure_minutes=1300,
                valid_from=day,
                valid_to=day,
                dataset_source="DEMO",
            )
        )
        s.flush()
        s.add(
            Trip(
                id="other-trip",
                service_id="svc-2",
                service_date=day,
                dataset_source="DEMO",
            )
        )
    with Session(engine) as s:
        from app.data_access import Principal
        from app.dispatch import EventInput, apply_event

        with pytest.raises(Exception) as error:
            apply_event(
                s,
                s.get(Trip, "other-trip"),
                EventInput(
                    event_type="PLATFORM",
                    station_id="a",
                    source_id="dispatch-source",
                    expected_version=0,
                    idempotency_key=str(uuid4()),
                    occurred_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                    reason="DEMO conflicting bay",
                    details={"bay_id": "bay1"},
                ),
                Principal("root", "ADMIN"),
            )
        assert error.value.status_code == 409


def test_notice_requires_independent_approval_and_is_passenger_visible(ops):
    client, _engine, _, caps = ops
    _event, body = submit(
        ops,
        "NOTICE_REQUEST",
        {
            "description": "DEMO road closure observed locally",
            "disruption_type": "ROAD_CLOSURE",
            "severity": "HIGH",
        },
    )
    assert not client.get(
        "/api/v1/operations/disruptions?station_id=a&operator_id=op-a"
    ).json()["data"]
    submit(
        ops,
        "PUBLISH_NOTICE",
        {"target_event_id": body["idempotency_key"]},
        expected=403,
    )
    submit(
        ops,
        "PUBLISH_NOTICE",
        {"target_event_id": body["idempotency_key"]},
        headers=caps["supervisor"],
    )
    assert (
        client.get(
            "/api/v1/operations/disruptions?station_id=a&operator_id=op-a"
        ).json()["data"][0]["approved_by"]
        == "supervisor"
    )


def test_announcement_preview_review_and_no_fabricated_fields(ops):
    client, _, _, caps = ops
    _, body = submit(ops, "ANNOUNCEMENT_REQUEST")
    submit(
        ops,
        "PUBLISH_ANNOUNCEMENT",
        {"target_event_id": body["idempotency_key"]},
        headers=caps["supervisor"],
    )
    text = client.get("/api/v1/operations/announcements?station_id=a").json()["data"][
        0
    ]["message"]
    assert "enquiry counter" in text and "Platform" not in text


def test_correction_preserves_audit_and_replaces_projection(ops):
    _, _, _, caps = ops
    event, _ = submit(ops, "ARRIVED_AT_STOP")
    submit(
        ops,
        "CORRECTION",
        {"target_event_id": event["id"], "corrected_event_type": "ARRIVED_AT_STOP"},
        headers=caps["supervisor"],
    )
    assert board(ops)["data"][0]["actual_arrival"]


def test_websocket_invalidates_and_reconnect_sends_authoritative_revision(ops):
    client, _, _, _ = ops
    with client.websocket_connect("/api/v1/operations/stream?station_id=a") as ws:
        first = ws.receive_json()
        assert first["type"] == "INVALIDATE"
        submit(ops, "BOARDING")
        update = ws.receive_json()
        while update["type"] == "HEARTBEAT":
            update = ws.receive_json()
        assert update["version"] > first["version"]
    with client.websocket_connect("/api/v1/operations/stream?station_id=a") as ws:
        assert ws.receive_json()["version"] == update["version"]


def test_missing_provenance_and_foreign_station_are_rejected(ops):
    submit(ops, "BOARDING", source_id="missing", expected=422)
    submit(ops, "BOARDING", station="does-not-exist", headers=ROOT, expected=422)


def test_completion_requires_actual_destination_arrival(ops):
    submit(ops, "ARRIVED_AT_STOP", station="b")
    submit(ops, "COMPLETED", station="b")
    assert board(ops, "b")["data"][0]["phase"] == "COMPLETED"


def test_departed_event_is_available_to_existing_nlp_handler(ops):
    client, engine, day, _ = ops
    submit(ops, "DEPARTED_FROM_STOP")
    from app.status import OperationalStatusEngine

    with Session(engine) as s:
        status = OperationalStatusEngine(s).status(
            "dispatch-trip", datetime.now(UTC), station_id="a"
        )
        assert status["actual_departure"] and status["gps_status"] == "UNKNOWN"
    response = client.post(
        "/api/v1/enquiry",
        json={
            "intent": "BUS_DEPARTED_STATUS",
            "service_id": "svc",
            "origin": "a",
            "station": "a",
            "travel_date": day.isoformat(),
            "at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["actual_departure"]
    from app.nlp_seed import seed_nlp
    from app.taxonomy_seed import seed_taxonomy

    seed_nlp(engine)
    seed_taxonomy(engine)
    response = client.post(
        "/api/v1/conversation/message",
        json={
            "text": "Has service DEMO-1 departed?",
            "language": "en",
            "station_context": "a",
        },
    )
    assert response.status_code == 200, response.text
    assert "BUS_DEPARTED_STATUS" in response.json()["intents"], response.text
    assert "recorded as departed" in response.json()["answer"], response.text


def test_concurrent_events_have_one_winner_and_append_only_history(ops):
    from concurrent.futures import ThreadPoolExecutor

    client, engine, _, caps = ops
    body = {
        "event_type": "BOARDING",
        "station_id": "a",
        "source_id": "dispatch-source",
        "expected_version": 0,
        "occurred_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "reason": "DEMO concurrent dispatcher observation",
    }

    def send(_):
        return client.post(
            "/api/v1/operations/trips/dispatch-trip/events",
            headers=caps["dispatch-user"],
            json={**body, "idempotency_key": str(uuid4())},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [200, 409]
    with Session(engine) as session:
        event = session.scalar(select(Audit).where(Audit.entity_type == "operations"))
        event.reason = "attempted rewrite"
        with pytest.raises(ValueError, match="append-only"):
            session.flush()


def test_verified_delay_rechecks_connection_timing(ops):
    from app.enquiry import Enquiry, JourneyQuery

    _client, engine, day, _ = ops
    query = JourneyQuery(
        origin="a",
        destination="b",
        at=datetime.combine(day, datetime.min.time(), ZoneInfo("Asia/Kolkata")),
    )
    with Session(engine) as s:
        before = next(
            r
            for r in Enquiry(s).get_next_buses(query)
            if r["trip_id"] == "dispatch-trip"
        )
    submit(ops, "DELAYED", {"delay_minutes": 45})
    query = query.model_copy(update={"at": datetime.now(UTC)})
    with Session(engine) as s:
        after = next(
            r
            for r in Enquiry(s).get_next_buses(query)
            if r["trip_id"] == "dispatch-trip"
        )
        assert (after["departure"] - before["departure"]).total_seconds() == 2700
        assert after["arrival"] > before["arrival"]


def test_boarding_platform_is_only_actual_when_explicitly_observed(ops):
    submit(ops, "PLATFORM", {"bay_id": "bay1"})
    assert board(ops)["data"][0]["platform"]["kind"] == "DISPATCHER_CONFIRMED"
    submit(ops, "BOARDING", {"bay_id": "bay1"})
    assert board(ops)["data"][0]["platform"]["kind"] == "ACTUAL_BOARDING"


def test_new_actual_observation_does_not_resurrect_expired_estimates(ops):
    submit(
        ops,
        "DELAYED",
        {"delay_minutes": 10},
        occurred_at=(datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )
    submit(ops, "ARRIVED_AT_STOP")
    row = board(ops)["data"][0]
    assert (
        row["actual_arrival"]
        and row["estimated_departure"] is None
        and row["delay_minutes"] is None
    )


def test_publication_rechecks_requested_source_ownership(ops):
    _client, engine, _, caps = ops
    _, body = submit(
        ops,
        "NOTICE_REQUEST",
        {
            "description": "DEMO scoped notice",
            "disruption_type": "OTHER",
            "severity": "LOW",
        },
    )
    with Session(engine) as session, session.begin():
        session.get(DataSource, "dispatch-source").operator_id = "op-b"
        session.add(
            DataSource(
                id="replacement-source",
                code="REPLACEMENT",
                name="DEMO current source",
                operator_id="op-a",
                is_demo=True,
            )
        )
    submit(
        ops,
        "PUBLISH_NOTICE",
        {"target_event_id": body["idempotency_key"]},
        source_id="replacement-source",
        headers=caps["supervisor"],
        expected=409,
    )


def test_demo_source_cannot_change_non_demo_operational_projection(ops):
    _client, engine, _, _ = ops
    with Session(engine) as session, session.begin():
        session.get(Trip, "dispatch-trip").dataset_source = "OFFICIAL_OPERATOR_DATA"
    submit(ops, "BOARDING", expected=422)
