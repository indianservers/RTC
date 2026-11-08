from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app import main
from app.domain import Base, ExceptionDay, Station, database
from app.enquiry import Enquiry, JourneyQuery
from app.imports import import_csv
from app.operations import Trip
from app.seed import seed
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def db(tmp_path):
    engine = database("sqlite:///" + str(tmp_path / "test.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    return engine


@pytest.fixture
def q():
    return JourneyQuery(
        origin="Vijayawada",
        destination="Guntur",
        at=datetime(2026, 11, 8, tzinfo=ZoneInfo("Asia/Kolkata")),
    )


def test_enquiries(db, q):
    with Session(db) as s:
        e = Enquiry(s)
        rows = e.get_next_buses(q)
        assert rows
        assert e.get_first_bus(q, date(2026, 11, 8))[0] == rows[0]
        assert e.get_last_bus(q, date(2026, 11, 8))[0] == rows[-1]
        assert e.get_bus_fare(q)[0]["amount"] == "100.00"
        assert e.get_available_bus_types(q)
        service = rows[0]["service_id"]
        assert e.get_service_details(service).id == service
        assert [x.sequence for x in e.get_route_stops(service)] == [0, 1]
        assert e.get_journey_duration(q)[0]["minutes"] == 180
        assert e.get_arrival_time(q)[0]["kind"] == "scheduled"
        assert e.get_seat_availability("missing", q.at)["status"] == "unknown"
        assert (
            e.get_service_status(service, date(2026, 11, 8))["status"]
            == "scheduled_only"
        )
        assert e.get_cheapest_services(q)
        assert e.get_fastest_services(q)
        assert e.get_direct_services(q)
        assert e.get_operator_services("DEMO")
        assert e.get_concessions("DEMO", q.at.date()) == []
        assert e.get_station_facilities("Vijayawada") == []
        assert (
            e.get_platform_assignment("missing", "Vijayawada", q.at)["status"]
            == "unknown"
        )
        assert e.get_services_via_stop(q, "Tirupati") == []


def test_cancellation_exception(db, q):
    with Session(db) as s:
        e = Enquiry(s)
        before = e.get_next_buses(q)
        row = before[0]
        s.add(
            Trip(
                service_id=row["service_id"],
                service_date=row["service_date"],
                status="cancelled",
            )
        )
        s.flush()
        assert len(e.get_next_buses(q)) == len(before) - 1
        row = before[1]
        s.add(
            ExceptionDay(
                service_id=row["service_id"],
                service_date=row["service_date"],
                operates=False,
            )
        )
        s.flush()
        assert len(e.get_next_buses(q)) == len(before) - 2


def test_import_atomic_repeat_dry_run(db):
    text = "dataset_source,code,name\nDEMO,NEW,New station\n"
    with Session(db) as s, s.begin():
        assert not import_csv(s, "stations", text, True)["committed"]
        assert s.scalar(select(Station).where(Station.code == "NEW")) is None
        assert import_csv(s, "stations", text, False)["inserted"] == 1
        assert import_csv(s, "stations", text, False)["duplicates"] == 1
        bad = "dataset_source,code,name\nDEMO,ROLLBACK,Valid\nDEMO,,Invalid\n"
        assert import_csv(s, "stations", bad, False)["errors"]
        assert s.scalar(select(Station).where(Station.code == "ROLLBACK")) is None


def test_api_offline(db, monkeypatch, q):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("External network attempt")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(main, "engine", db)
    monkeypatch.setenv("RTC_ADMIN_TOKEN", "test-local-secret")
    with TestClient(main.app) as client:
        assert client.get("/api/v1/operators").status_code == 200
        assert client.get(
            "/api/v1/enquiry/next-bus",
            params={
                "origin": q.origin,
                "destination": q.destination,
                "at": q.at.isoformat(),
            },
        ).json()["data"]
        assert (
            client.get(
                "/api/v1/enquiry/first-bus",
                params={
                    "origin": q.origin,
                    "destination": q.destination,
                    "at": q.at.isoformat(),
                    "day": "2026-11-08",
                },
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/admin/stations",
                json={"dataset_source": "DEMO", "code": "AUTH", "name": "Test"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/admin/stations",
                headers={"Authorization": "Bearer test-local-secret"},
                json={"dataset_source": "DEMO", "code": "AUTH", "name": "Test"},
            ).status_code
            == 201
        )
        assert client.get("/openapi.json").status_code == 200


def test_connections(db, q):
    q = q.model_copy(update={"destination": "Tirupati", "days": 2})
    with Session(db) as s:
        rows = Enquiry(s).get_connecting_services(q)
        assert rows
        for row in rows:
            assert row["legs"][1]["departure"] >= row["legs"][0]["arrival"] + timedelta(
                minutes=15
            )


def test_unicode_and_overnight(db, q):
    from app.demo import enrich
    from app.domain import Repository

    enrich(db)
    with Session(db) as s:
        repo = Repository(s)
        assert repo.resolve_station("విజయవాడ").name == "Vijayawada"
        assert repo.resolve_station("తిరుపతి").id != repo.resolve_station("తిరుమల").id
        rows = Enquiry(s).get_next_buses(
            q.model_copy(update={"at": q.at.replace(hour=23)})
        )
        assert all(r["departure"] >= q.at.replace(hour=23) for r in rows)


def test_verified_delay_and_fare_override(db, q):
    from app.operations import DataSource
    from app.records import FareOverride, TripStopTime

    with Session(db) as s:
        e = Enquiry(s)
        row = e.get_next_buses(q)[0]
        trip = Trip(service_id=row["service_id"], service_date=row["service_date"])
        source = DataSource(code="DEMO-OBS", name="DEMO observation")
        s.add_all([trip, source])
        s.flush()
        stop = e.get_route_stops(row["service_id"])[0]
        s.add(
            TripStopTime(
                trip_id=trip.id,
                stop_id=stop.id,
                source_id=source.id,
                effective_at=q.at,
                expires_at=q.at + timedelta(days=1),
                verified=True,
                estimated_departure=row["departure"] + timedelta(minutes=10),
            )
        )
        origin = s.scalar(select(Station).where(Station.name == q.origin))
        destination = s.scalar(select(Station).where(Station.name == q.destination))
        s.add(
            FareOverride(
                trip_id=trip.id,
                origin_id=origin.id,
                destination_id=destination.id,
                amount=125,
            )
        )
        s.flush()
        changed = next(
            x for x in e.get_next_buses(q) if x["service_id"] == row["service_id"]
        )
        assert changed["departure_kind"] == "estimated"
        assert changed["fare"].startswith("125")
        assert changed["arrival"] - row["arrival"] == timedelta(minutes=10)


def test_api_enquiry_coverage(db, monkeypatch, q):
    monkeypatch.setattr(main, "engine", db)
    with Session(db) as s:
        service = s.scalar(select(Service))
        service_id = service.id
    params = {
        "origin": q.origin,
        "destination": q.destination,
        "at": q.at.isoformat(),
        "day": "2026-11-08",
        "operator": "DEMO",
        "service_id": service_id,
        "station": q.origin,
        "via": "Tirupati",
    }
    with TestClient(main.app) as client:
        for endpoint in [
            "first-bus",
            "last-bus",
            "fare",
            "bus-types",
            "service",
            "route",
            "duration",
            "arrival",
            "platform",
            "availability",
            "status",
            "cheapest",
            "fastest",
            "direct",
            "connections",
            "via",
            "operator-services",
            "concessions",
            "facilities",
        ]:
            response = client.get("/api/v1/enquiry/" + endpoint, params=params)
            assert response.status_code == 200, (endpoint, response.text)
        response = client.get(
            "/api/v1/enquiry/first-bus",
            params={
                "origin": q.origin,
                "destination": q.destination,
                "day": "2026-11-08",
            },
        )
        assert response.status_code == 200


from app.domain import Service
