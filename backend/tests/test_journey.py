"""Deterministic timetable scenarios and itinerary invariants; no network."""

import socket
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from app import main
from app.domain import (
    Base,
    Category,
    ExceptionDay,
    Fare,
    Operator,
    Route,
    Service,
    Station,
    Stop,
    database,
)
from app.journey import Itinerary, JourneyConstraints, JourneyPlanner, RecoveryRequest
from app.operations import Trip
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ZONE = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 11, 8)


@pytest.fixture(scope="module")
def network(tmp_path_factory):
    engine = database(
        "sqlite:///" + str(tmp_path_factory.mktemp("journeys") / "test.db")
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        s.add_all(
            [
                Operator(id="op", code="OP", name="Demo operator"),
                Operator(id="other", code="OTHER", name="Other demo"),
            ]
        )
        s.flush()
        s.add_all(
            [
                Category(id="cat", operator_id="op", name="Express", code="EX"),
                Category(id="cat2", operator_id="other", name="Seater", code="SE"),
            ]
        )
        s.add_all([Station(id=n, code=n, name=n) for n in "ABCDMX"])
        s.flush()
        specs = [
            ("ab", ["A", "M", "B"], [0, 45, 90], 1200, "op"),
            ("bc", ["B", "C"], [0, 60], 1320, "other"),
            ("cd", ["C", "D"], [0, 60], 30, "op"),
            ("ad", ["A", "D"], [0, 420], 1260, "op"),
            ("bd", ["B", "D"], [0, 180], 1380, "op"),
        ]
        for sid, stations, offsets, departure, op in specs:
            s.add(Route(id=sid, code=sid))
            s.flush()
            s.add(
                Service(
                    id=sid,
                    operator_id=op,
                    category_id="cat" if op == "op" else "cat2",
                    route_id=sid,
                    number=sid,
                    departure_minutes=departure,
                    valid_from=DAY - timedelta(days=5),
                    valid_to=DAY + timedelta(days=30),
                )
            )
            s.add_all(
                [
                    Stop(
                        id=sid + str(i),
                        route_id=sid,
                        station_id=n,
                        sequence=i,
                        offset_minutes=offsets[i],
                        distance_km=i * 50,
                    )
                    for i, n in enumerate(stations)
                ]
            )
            s.flush()
            for i, a in enumerate(stations):
                for b in stations[i + 1 :]:
                    s.add(
                        Fare(
                            service_id=sid,
                            origin_id=a,
                            destination_id=b,
                            amount=Decimal(500 if sid == "ad" else 100),
                            valid_from=DAY,
                            valid_to=DAY + timedelta(days=20),
                        )
                    )
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original_connect = socket.socket.connect

    def deny(sock, address):
        # Windows asyncio uses a loopback socketpair even for in-process ASGI tests.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(sock, address)
        raise AssertionError("Outbound network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("Outbound network forbidden")
        ),
    )


def constraints(**kw):
    return JourneyConstraints(
        origin="A",
        destination="D",
        earliest_departure=datetime(2026, 11, 8, 19, tzinfo=ZONE),
        horizon_hours=14,
        **kw,
    )


@pytest.mark.parametrize(
    "ranking",
    [
        "EARLIEST_ARRIVAL",
        "EARLIEST_DEPARTURE",
        "LOWEST_FARE",
        "SHORTEST_DURATION",
        "FEWEST_TRANSFERS",
        "MINIMUM_WAIT",
        "PREFERRED_BUS_CATEGORY",
    ],
)
@pytest.mark.parametrize("transfers", [0, 1, 2])
@pytest.mark.parametrize("wait", [15, 30, 90, 180])
@pytest.mark.parametrize("day", [0, 1, 2])
def test_252_timetable_scenarios(network, ranking, transfers, wait, day):
    c = constraints(
        ranking=ranking,
        max_transfers=transfers,
        maximum_wait_minutes=wait,
        preferred_category="Express",
    )
    c = c.model_copy(
        update={"earliest_departure": c.earliest_departure + timedelta(days=day)}
    )
    with Session(network) as s:
        planner = JourneyPlanner(s)
        result = planner.search(c)
        assert result.itineraries  # direct always remains feasible
        ids = []
        for i in result.itineraries:
            assert i.transfer_count <= transfers
            assert i.total_fare == sum(l.fare for l in i.legs)
            assert all(15 <= t.wait_minutes <= wait for t in i.transfers)
            assert i.departure_at >= c.earliest_departure
            assert i.arrival_at <= result.search_horizon_end
            assert Itinerary.model_validate(i.model_dump()) == i
            for leg in i.legs:
                service = s.get(Service, leg.service_id)
                a = s.get(Stop, leg.boarding_stop_id)
                b = s.get(Stop, leg.alighting_stop_id)
                assert a.route_id == b.route_id == service.route_id
                assert a.sequence < b.sequence and a.boarding and b.alighting
                assert leg.boarding_at.tzinfo and leg.alighting_at.tzinfo
            ids.append(i.journey_id)
        assert len(set(ids)) == len(ids)
        assert [
            i.journey_id for i in planner.rank(result.itineraries, ranking, "Express")
        ] == ids
        if transfers == 0:
            assert all(len(i.legs) == 1 for i in result.itineraries)
        if transfers == 2 and wait >= 90:
            assert any(
                [l.service_id for l in i.legs] == ["ab", "bc", "cd"]
                for i in result.itineraries
            )
        if ranking == "LOWEST_FARE" and transfers == 0:
            assert result.itineraries[0].total_fare == 500


def test_intermediate_direction_and_permissions(network):
    with Session(network) as s:
        planner = JourneyPlanner(s)
        c = constraints().model_copy(update={"origin": "M"})
        result = planner.search(c)
        assert result.itineraries and all(
            i.legs[0].boarding_stop_id == "ab1" for i in result.itineraries
        )
        assert not planner.search(c.model_copy(update={"destination": "A"})).itineraries
        s.get(Stop, "ab1").boarding = False
        s.flush()
        assert not planner.search(c).itineraries


def test_unknown_fares_and_ranking(network):
    from sqlalchemy import select

    with Session(network) as s:
        fare = s.scalar(select(Fare).where(Fare.service_id == "bc"))
        fare.active = False
        s.flush()
        result = JourneyPlanner(s).search(constraints())
        partial = [
            i for i in result.itineraries if any(l.service_id == "bc" for l in i.legs)
        ]
        assert partial and all(
            i.fare_status == "PARTIAL"
            and i.total_fare is None
            and i.known_subtotal == 200
            for i in partial
        )
        assert all(
            i.total_fare is not None
            for i in JourneyPlanner.rank(result.itineraries, "LOWEST_FARE")
        )


def test_calendar_cancellation_and_replan(network):
    with Session(network) as s:
        planner = JourneyPlanner(s)
        before = planner.search(constraints())
        assert any(i.transfer_count == 2 for i in before.itineraries)
        s.add(Trip(id="cancel", service_id="bc", service_date=DAY, status="cancelled"))
        s.flush()
        after = planner.replan_journey(constraints())
        assert not any(l.service_id == "bc" for i in after.itineraries for l in i.legs)
        s.add(ExceptionDay(service_id="ad", service_date=DAY, operates=False))
        s.flush()
        assert all(
            i.transfer_count > 0 for i in planner.search(constraints()).itineraries
        )


def test_hard_filters_deadline_resource_and_stand(network):
    with Session(network) as s:
        planner = JourneyPlanner(s)
        assert not planner.search(constraints(filters={"ac": True})).itineraries
        assert not planner.search(constraints(filters={"accessible": True})).itineraries
        assert not planner.search(constraints(filters={"max_fare": 50})).itineraries
        assert not planner.search(constraints(require_verified_seats=True)).itineraries
        result = planner.search(
            constraints(arrival_deadline=datetime(2026, 11, 9, 2, tzinfo=ZONE))
        )
        assert result.itineraries and all(
            i.arrival_at.hour <= 2 for i in result.itineraries
        )
        assert not planner.search(
            constraints().model_copy(update={"destination": "X"})
        ).itineraries
        capped = planner.search(constraints(max_expansions=1))
        assert capped.search_stats["truncated"]


def test_missed_bus_and_api(network, monkeypatch):
    with Session(network) as s:
        planner = JourneyPlanner(s)
        request = RecoveryRequest(
            search=constraints(),
            missed_service_id="ab",
            missed_service_date=DAY,
            explicitly_missed=True,
        )
        recovery = planner.find_alternatives_after_missed_bus(request)
        assert recovery.recommendations["next_direct"] is not None
        assert not any(
            l.service_id == "ab" and l.service_date == DAY
            for i in recovery.itineraries
            for l in i.legs
        )
        request.missed_service_id = "ad"
        result = planner.find_alternatives_after_missed_bus(request)
        assert all(i.departure_at.hour > 21 for i in result.itineraries)
        request.explicitly_missed = False
        with pytest.raises(ValueError):
            planner.find_alternatives_after_missed_bus(request)
    monkeypatch.setattr(main, "engine", network)
    with TestClient(main.app) as client:
        for action in ["search", "compare", "replan"]:
            r = client.post(
                "/api/v1/journeys/" + action, json=constraints().model_dump(mode="json")
            )
            assert r.status_code == 200, r.text
            assert r.json()["itineraries"]
        assert client.post("/api/v1/journeys/search", json={}).status_code == 422
        assert (
            client.post(
                "/api/v1/journeys/missed-bus", json=request.model_dump(mode="json")
            ).status_code
            == 422
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"max_transfers": 3},
        {"horizon_hours": 49},
        {"minimum_transfer_minutes": 31, "maximum_wait_minutes": 30},
        {"origin": "A", "destination": "A"},
    ],
)
def test_invalid_constraints(updates):
    data = constraints().model_dump()
    data.update(updates)
    with pytest.raises(ValueError):
        JourneyConstraints.model_validate(data)


from hypothesis import given, settings
from hypothesis import strategies as st


@given(
    transfers=st.integers(0, 2), wait=st.integers(15, 180), budget=st.integers(0, 800)
)
@settings(max_examples=40, deadline=None, derandomize=True)
def test_property_itinerary_bounds(network, transfers, wait, budget):
    with Session(network) as s:
        c = constraints(
            max_transfers=transfers,
            maximum_wait_minutes=wait,
            filters={"max_fare": budget},
        )
        for i in JourneyPlanner(s).search(c).itineraries:
            assert i.transfer_count <= transfers
            assert i.total_fare is not None and i.total_fare <= budget
            assert all(15 <= t.wait_minutes <= wait for t in i.transfers)
            Itinerary.model_validate(i.model_dump())
            broken = i.model_dump()
            broken["known_subtotal"] += 1
            with pytest.raises(ValueError):
                Itinerary.model_validate(broken)


def test_verified_arrival_and_stale_observation(network):
    from app.operations import DataSource
    from app.records import TripStopTime

    with Session(network) as s:
        now = constraints().earliest_departure
        s.add(DataSource(id="src", code="SRC", name="Demo observations"))
        s.add(Trip(id="delayed", service_id="ab", service_date=DAY, status="scheduled"))
        s.flush()
        observation = TripStopTime(
            trip_id="delayed",
            stop_id="ab2",
            source_id="src",
            verified=True,
            effective_at=now - timedelta(minutes=1),
            expires_at=now + timedelta(hours=1),
            estimated_arrival=now.replace(hour=23),
        )
        s.add(observation)
        s.flush()
        result = JourneyPlanner(s).search(constraints())
        assert not any(
            [l.service_id for l in i.legs] == ["ab", "bc", "cd"]
            for i in result.itineraries
        )
        observation.expires_at = now - timedelta(seconds=1)
        s.flush()
        result = JourneyPlanner(s).search(constraints())
        assert any(
            [l.service_id for l in i.legs] == ["ab", "bc", "cd"]
            for i in result.itineraries
        )


def test_conversation_planner_and_selection(network):
    from app.nlp.pipeline import RTCQueryOrchestrator
    from app.nlp.state import ContextOperation, ContextUpdateEngine

    with Session(network) as s:
        slots = {
            "origin": "A",
            "destination": "D",
            "travel_date": DAY.isoformat(),
            "filters": {},
        }
        orchestrator = RTCQueryOrchestrator(s)
        result = orchestrator.execute(
            ["CONNECTING_BUSES"], slots, constraints().earliest_departure
        )
        assert result[0]["results"] and slots["journey_candidates"]
        assert any(len(r["legs"]) == 3 for r in result[0]["results"])
        chosen = ContextUpdateEngine().apply(
            slots, ContextOperation(op="SELECT_RESULT", value=1)
        )
        assert (
            chosen["selected_itinerary"]["journey_id"]
            == slots["candidates"][1]["journey_id"]
        )
        changed = ContextUpdateEngine().apply(
            chosen, ContextOperation(op="REPLACE_SLOT", slot="destination", value="B")
        )
        assert not changed.get("selected_itinerary") and not changed.get(
            "journey_candidates"
        )
        result = orchestrator.execute(
            ["CHEAPEST_BUS"], slots, constraints().earliest_departure
        )
        assert result[0]["results"][0]["total_fare"] == "200.00"


def test_disruption_freshness_and_operator_category(network):
    from app.operations import DataSource
    from app.records import Disruption

    with Session(network) as s:
        now = constraints().earliest_departure
        s.add(DataSource(id="disrc", code="DISRC", name="Demo disruption source"))
        s.flush()
        alert = Disruption(
            service_id="ad",
            source_id="disrc",
            description="Demo route suspension",
            verified=True,
            effective_at=now - timedelta(minutes=5),
            expires_at=now + timedelta(hours=1),
        )
        s.add(alert)
        s.flush()
        planner = JourneyPlanner(s)
        assert not any(
            l.service_id == "ad"
            for i in planner.replan_journey(constraints()).itineraries
            for l in i.legs
        )
        assert any(
            l.service_id == "ad"
            for i in planner.search(
                constraints(avoid_verified_disruptions=False)
            ).itineraries
            for l in i.legs
        )
        alert.expires_at = now - timedelta(seconds=1)
        s.flush()
        assert any(
            l.service_id == "ad"
            for i in planner.search(constraints()).itineraries
            for l in i.legs
        )
        for i in planner.search(
            constraints(filters={"operator": "OP", "category": "Express"})
        ).itineraries:
            assert all(
                l.operator_id == "op" and l.category == "Express" for l in i.legs
            )
            assert all(l.operational_status["gps_status"] == "UNKNOWN" for l in i.legs)


def test_festival_calendar_extra_and_intermediate_alighting(network):
    with Session(network) as s:
        s.get(Service, "ad").weekdays = "0"
        s.flush()
        planner = JourneyPlanner(s)
        assert not planner.find_direct_journeys(constraints()).itineraries
        s.add(ExceptionDay(service_id="ad", service_date=DAY, operates=True))
        s.flush()
        assert (
            planner.find_direct_journeys(constraints())
            .itineraries[0]
            .legs[0]
            .service_id
            == "ad"
        )
        result = planner.search(constraints().model_copy(update={"destination": "M"}))
        assert (
            result.itineraries
            and result.itineraries[0].legs[0].alighting_stop_id == "ab1"
        )


def test_seat_snapshot_requires_matching_segment_and_freshness(network):
    from app.operations import DataSource, SeatSnapshot

    with Session(network) as s:
        now = constraints().earliest_departure
        s.add(DataSource(id="seat-source", code="SEATS", name="Demo seat source"))
        s.add(
            Trip(id="seat-trip", service_id="ad", service_date=DAY, status="scheduled")
        )
        s.flush()
        snapshot = SeatSnapshot(
            trip_id="seat-trip",
            origin_station_id="B",
            destination_station_id="D",
            available=4,
            source_id="seat-source",
            verified=True,
            effective_at=now - timedelta(minutes=2),
            expires_at=now + timedelta(minutes=2),
        )
        s.add(snapshot)
        s.flush()
        c = constraints(require_verified_seats=True, passengers=2)
        assert not JourneyPlanner(s).search(c).itineraries
        snapshot.origin_station_id = "A"
        s.flush()
        assert JourneyPlanner(s).search(c).itineraries
        snapshot.expires_at = now - timedelta(seconds=1)
        s.flush()
        assert not JourneyPlanner(s).search(c).itineraries


def test_vehicle_hard_constraints(network):
    from app.catalog import Layout, Vehicle, VehicleType
    from app.links import ServiceVehicle

    with Session(network) as s:
        s.add(
            VehicleType(
                id="type",
                name="Demo AC accessible sleeper",
                ac=True,
                sleeper=True,
                wheelchair=True,
            )
        )
        s.add(Layout(id="layout", name="Demo", seating_capacity=0, berth_capacity=20))
        s.flush()
        s.add(
            Vehicle(
                id="vehicle",
                operator_id="op",
                type_id="type",
                layout_id="layout",
                registration="DEMO-TEST",
            )
        )
        s.flush()
        s.add(ServiceVehicle(service_id="ad", vehicle_id="vehicle"))
        s.flush()
        planner = JourneyPlanner(s)
        result = planner.search(
            constraints(filters={"ac": True, "sleeper": True, "accessible": True})
        )
        assert result.itineraries and all(
            [l.service_id for l in i.legs] == ["ad"] for i in result.itineraries
        )
        assert not planner.search(constraints(filters={"ac": False})).itineraries


def test_fare_engine_prefetch_matches_quote(network):
    from app.fares import FareEngine

    with Session(network) as s:
        result = JourneyPlanner(s).search(constraints())
        for i in result.itineraries:
            for leg in i.legs:
                quote = FareEngine(s).quote(
                    leg.service_id, leg.origin, leg.destination, leg.service_date
                )
                assert quote == leg.fare_breakdown


def test_variant_membership_is_respected(network):
    from app.catalog import Variant
    from app.links import VariantStop

    with Session(network) as s:
        s.add(Variant(id="express-variant", route_id="ab", name="Demo skip M"))
        s.flush()
        s.add_all(
            [
                VariantStop(variant_id="express-variant", stop_id=sid)
                for sid in ("ab0", "ab2")
            ]
        )
        s.flush()
        s.get(Service, "ab").route_variant_id = "express-variant"
        s.flush()
        planner = JourneyPlanner(s)
        assert not planner.search(
            constraints().model_copy(update={"origin": "M"})
        ).itineraries
        assert planner.search(
            constraints().model_copy(update={"destination": "B"})
        ).itineraries


def test_existing_operating_day_api(network):
    from app.enquiry import Enquiry
    from app.timetable import TimetableEngine

    with Session(network) as s:
        rows = TimetableEngine(Enquiry(s)).operating_day(
            "A", "B", DAY, cutoff_minutes=19 * 60
        )
        assert rows and rows[0]["service_id"] == "ab"
