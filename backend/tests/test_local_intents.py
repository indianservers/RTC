"""Local capability and dialogue regressions: no policies, authorization or live feeds invented."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from app import catalog, links, operations, records, schema1a  # noqa: F401
from app.catalog import Layout, Vehicle, VehicleType
from app.domain import Base, Operator, Service, Station, Stop, database
from app.engine import RTCEnquiryEngine
from app.links import ServiceVehicle
from app.local_intents import LOCAL_INTENTS
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp_seed import seed_nlp
from app.operations import DataSource, PlatformAssignment, StationBay, Trip
from app.records import Inventory, ReservationChannel, RouteDistance, TripStopTime
from app.schema1a import ContactPoint
from app.seed import seed
from app.taxonomy_seed import seed_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

NOW = datetime(2026, 11, 8, 6, tzinfo=UTC)


@pytest.fixture(scope="module")
def local_db(tmp_path_factory):
    engine = database("sqlite:///" + str(tmp_path_factory.mktemp("local") / "local.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    seed_nlp(engine)
    seed_taxonomy(engine)
    with Session(engine) as s, s.begin():
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        op = s.get(Operator, service.operator_id)
        op.website = "https://demo-operator.invalid/contact"
        origin = s.scalar(select(Station).where(Station.code == "DEMO0"))
        origin.address = "DEMO Road 5"
        source = DataSource(
            code="LOCAL-TEST",
            name="Synthetic operational fixture",
            dataset_source="DEMO",
        )
        s.add(source)
        kind = VehicleType(
            name="DEMO accessible", ac=True, sleeper=False, wheelchair=True
        )
        layout = Layout(name="DEMO layout", seating_capacity=30, berth_capacity=10)
        s.add_all([kind, layout])
        s.flush()
        vehicle = Vehicle(
            operator_id=op.id,
            type_id=kind.id,
            layout_id=layout.id,
            registration="DEMO-LOCAL-1",
        )
        s.add(vehicle)
        s.flush()
        s.add(ServiceVehicle(service_id=service.id, vehicle_id=vehicle.id))
        trip = Trip(
            service_id=service.id, service_date=date(2026, 11, 8), vehicle_id=vehicle.id
        )
        s.add(trip)
        s.flush()
        s.add(Inventory(trip_id=trip.id, capacity=40))
        s.add(
            ReservationChannel(
                operator_id=op.id,
                name="DEMO counter",
                instructions="Use the recorded local ticket counter",
            )
        )
        s.add(
            ContactPoint(
                station_id=origin.id,
                contact_type="COMPLAINT",
                label="DEMO grievance desk",
                contact_value="DEMO extension 7",
            )
        )
        bays = [
            StationBay(station_id=origin.id, code="L1", floor_or_zone="Lower hall"),
            StationBay(station_id=origin.id, code="U2", floor_or_zone="Upper hall"),
        ]
        s.add_all(bays)
        s.flush()
        for i, bay in enumerate(bays):
            s.add(
                PlatformAssignment(
                    trip_id=trip.id,
                    bay_id=bay.id,
                    source_id=source.id,
                    verified=True,
                    recorded_at=NOW - timedelta(hours=2 - i),
                    effective_at=NOW - timedelta(hours=2 - i),
                    expires_at=NOW + timedelta(hours=1)
                    if i
                    else NOW - timedelta(minutes=30),
                )
            )
        stops = list(
            s.scalars(
                select(Stop)
                .where(Stop.route_id == service.route_id)
                .order_by(Stop.sequence)
            )
        )
        s.add(
            RouteDistance(
                origin_stop_id=stops[0].id,
                destination_stop_id=stops[1].id,
                distance_km=Decimal("149.25"),
            )
        )
        for stop in stops:
            s.add(
                TripStopTime(
                    trip_id=trip.id,
                    stop_id=stop.id,
                    source_id=source.id,
                    verified=True,
                    recorded_at=NOW - timedelta(minutes=10),
                    effective_at=NOW - timedelta(minutes=10),
                    expires_at=NOW + timedelta(minutes=30),
                    actual_departure=NOW - timedelta(minutes=5),
                    actual_arrival=NOW - timedelta(minutes=7),
                    estimated_arrival=NOW + timedelta(minutes=15),
                )
            )
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket

    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("Network attempted")
    )


def query(s, intent, **updates):
    service = s.scalar(select(Service).where(Service.number == "DEMO0"))
    args = {
        "intent": intent,
        "origin": "DEMO0",
        "destination": "DEMO1",
        "station": "DEMO0",
        "service_id": service.id,
        "travel_date": "2026-11-08",
        "at": NOW,
        "filters": {"operator": "DEMO"},
    }
    if intent == "BUS_AT_TIME":
        args["at"] = datetime(2026, 11, 7, 18, 30, tzinfo=UTC)  # midnight local
    args.update(updates)
    return RTCEnquiryEngine(s).enquire(**args)


@pytest.mark.parametrize("intent", sorted(LOCAL_INTENTS))
def test_15_existing_table_handlers(local_db, intent):
    with Session(local_db) as s:
        r = query(s, intent)
        assert r.status == "KNOWN", r.model_dump()
        assert r.results and r.query["intent"] == intent
        assert r.results[0].get("dataset_source") == "DEMO"
        if intent == "BUS_CAPACITY":
            assert r.results[0]["capacity"] == 40
        elif intent == "ROUTE_DISTANCE":
            assert Decimal(r.results[0]["distance_km"]) == Decimal("149.25")
        elif intent == "PLATFORM_CHANGE":
            assert (
                r.results[0]["previous_bay"] == "L1"
                and r.results[0]["current_bay"] == "U2"
                and r.results[0]["changed"]
            )
        elif intent == "ESTIMATED_ARRIVAL":
            assert datetime.fromisoformat(
                r.results[0]["estimated_arrival"]
            ) == NOW + timedelta(minutes=15)
        elif intent == "SERVICE_FREQUENCY":
            assert r.results[0]["count"] == 5
        elif intent == "BUS_AT_TIME":
            assert r.results[0]["service_number"] == "DEMO0"


@pytest.mark.parametrize("intent", sorted(LOCAL_INTENTS))
def test_15_dialogues_with_local_records(local_db, intent):
    with Session(local_db) as s:
        engine = RTCNLPEngine(s)
        initial = engine.process(
            NLPRequest(
                text="Service number DEMO0 to Guntur",
                station_context="DEMO0",
                operator="DEMO",
                language="en",
            ),
            NOW,
        )
        text = (
            "Bus at 12 AM"
            if intent == "BUS_AT_TIME"
            else intent.lower().replace("_", " ")
        )
        r = engine.process(
            NLPRequest(
                text=text, session_id=initial.session_id, language="en", debug=True
            ),
            NOW,
        )
        assert r.results, r.model_dump()
        assert r.results[0]["status"] == "KNOWN", r.model_dump()
        assert r.results[0]["query"]["intent"] == intent
        assert "DEMO" in r.data_source
        assert (
            "does not support" not in r.answer and "Selected service." not in r.answer
        )
        assert r.debug["database_function"] == "RTCEnquiryEngine.enquire"


@pytest.mark.parametrize(
    "intent", ["ESTIMATED_ARRIVAL", "BUS_DEPARTED_STATUS", "BUS_ARRIVED_STATUS"]
)
@pytest.mark.parametrize(
    "mutation",
    [
        "expired",
        "unverified",
        "future_effective",
        "future_recorded",
        "inactive",
        "missing_value",
    ],
)
def test_observations_never_invent_live_facts(local_db, intent, mutation):
    with Session(local_db) as s:
        observations = list(s.scalars(select(TripStopTime)))
        field = {
            "ESTIMATED_ARRIVAL": "estimated_arrival",
            "BUS_DEPARTED_STATUS": "actual_departure",
            "BUS_ARRIVED_STATUS": "actual_arrival",
        }[intent]
        for obs in observations:
            if mutation == "expired":
                obs.expires_at = NOW
            elif mutation == "unverified":
                obs.verified = False
            elif mutation == "future_effective":
                obs.effective_at = NOW + timedelta(minutes=1)
            elif mutation == "future_recorded":
                obs.recorded_at = NOW + timedelta(minutes=1)
            elif mutation == "inactive":
                obs.active = False
            else:
                setattr(obs, field, None)
        s.flush()
        r = query(s, intent)
        assert r.status == "UNKNOWN" and not r.results


@pytest.mark.parametrize(
    "intent",
    ["BOOKING_STATUS", "CANCELLATION_POLICY", "REFUND_POLICY", "LUGGAGE_RULES"],
)
def test_four_unsupported_are_honest(local_db, intent):
    with Session(local_db) as s:
        r = query(s, intent)
        assert r.status == "UNSUPPORTED" and not r.results


def test_missing_inventory_does_not_imply_seats(local_db):
    with Session(local_db) as s:
        inventory = s.scalar(select(Inventory))
        inventory.active = False
        s.flush()
        r = query(s, "BUS_CAPACITY")
        assert r.results[0]["seating_capacity"] == 30
        assert "not seat availability" in " ".join(r.warnings)
        seats = query(s, "SEAT_AVAILABILITY")
        assert seats.results[0]["status"] == "unknown"


def test_platform_history_and_distance_direction(local_db):
    with Session(local_db) as s:
        assignments = list(
            s.scalars(
                select(PlatformAssignment).order_by(PlatformAssignment.effective_at)
            )
        )
        assignments[-1].expires_at = NOW
        s.flush()
        assert query(s, "PLATFORM_CHANGE").status == "UNKNOWN"
        reversed_query = query(s, "ROUTE_DISTANCE", origin="DEMO1", destination="DEMO0")
        assert reversed_query.status == "INVALID_QUERY" and not reversed_query.results


def test_no_phone_or_booking_or_policy_invented(local_db):
    with Session(local_db) as s:
        op = s.scalar(select(Operator))
        op.website = None
        for channel in s.scalars(select(ReservationChannel)):
            channel.active = False
        for contact in s.scalars(select(ContactPoint)):
            contact.active = False
        s.flush()
        for intent in ("BOOKING_OPTIONS", "OPERATOR_CONTACT", "COMPLAINT_GUIDANCE"):
            assert query(s, intent).status == "UNKNOWN"


def test_trip_mismatch_and_missing_time(local_db):
    with Session(local_db) as s:
        trip = s.scalar(select(Trip))
        r = query(s, "ESTIMATED_ARRIVAL", trip_id=trip.id, travel_date="2026-11-09")
        assert r.status == "INVALID_QUERY"
        engine = RTCNLPEngine(s)
        r = engine.process(
            NLPRequest(text="Bus at time", station_context="DEMO0", language="en"), NOW
        )
        assert r.requires_clarification and not r.results


def test_schedule_local_filters_and_exception_precedence(local_db):
    from app.domain import Category, ExceptionDay

    with Session(local_db) as s:
        wrong = s.scalar(select(Category).where(Category.name == "Demo seater"))
        wrong.name = "Only one category"
        other = Category(operator_id=wrong.operator_id, name="Unassigned category")
        s.add(other)
        s.flush()
        for intent in (
            "SPECIAL_DAY_SCHEDULE",
            "SERVICE_FREQUENCY",
            "ACCESSIBLE_BUS_AVAILABILITY",
            "BUS_AT_TIME",
        ):
            assert (
                query(
                    s, intent, filters={"operator": "DEMO", "category": other.id}
                ).status
                == "UNKNOWN"
            )
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        s.add(
            ExceptionDay(
                service_id=service.id, service_date=date(2026, 11, 8), operates=False
            )
        )
        s.flush()
        assert "DEMO0" not in {
            r["service_number"] for r in query(s, "SPECIAL_DAY_SCHEDULE").results
        }
        assert query(s, "SERVICE_FREQUENCY").results[0]["count"] == 4


def test_time_window_and_date_followup(local_db):
    with Session(local_db) as s:
        # 00:00 service is included at the lower bound and excluded at the upper bound.
        lower = datetime(2026, 11, 7, 18, 45, tzinfo=UTC)
        upper = datetime(2026, 11, 7, 18, 15, tzinfo=UTC)
        assert "DEMO0" in {
            r["service_number"] for r in query(s, "BUS_AT_TIME", at=lower).results
        }
        assert "DEMO0" not in {
            r["service_number"] for r in query(s, "BUS_AT_TIME", at=upper).results
        }
        nlp = RTCNLPEngine(s)
        first = nlp.process(
            NLPRequest(
                text="Bus at 12 AM to Guntur", station_context="DEMO0", language="en"
            ),
            NOW,
        )
        following = nlp.process(
            NLPRequest(text="Tomorrow", session_id=first.session_id, language="en"), NOW
        )
        assert following.results[0]["query"]["at"].startswith("2026-11-09T00:00")


def test_future_platform_does_not_mask_current(local_db):
    with Session(local_db) as s:
        trip = s.scalar(select(Trip))
        source = s.scalar(select(DataSource))
        bay = s.scalar(select(StationBay))
        s.add(
            PlatformAssignment(
                trip_id=trip.id,
                bay_id=bay.id,
                source_id=source.id,
                verified=True,
                recorded_at=NOW,
                effective_at=NOW + timedelta(minutes=1),
                expires_at=NOW + timedelta(hours=1),
            )
        )
        s.flush()
        assert query(s, "PLATFORM_CHANGE").results[0]["current_bay"] == "U2"


def test_route_variant_membership_and_conflicting_distance(local_db):
    from app.catalog import Variant

    with Session(local_db) as s:
        distance = s.scalar(select(RouteDistance))
        s.add(
            RouteDistance(
                origin_stop_id=distance.origin_stop_id,
                destination_stop_id=distance.destination_stop_id,
                distance_km=Decimal(120),
            )
        )
        s.flush()
        assert query(s, "ROUTE_DISTANCE").status == "UNKNOWN"
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        variant = Variant(route_id=service.route_id, name="DEMO empty variant")
        s.add(variant)
        s.flush()
        service.route_variant_id = variant.id
        s.flush()
        assert query(s, "ROUTE_DISTANCE").status == "INVALID_QUERY"


def test_explicit_station_controls_eta(local_db):
    with Session(local_db) as s:
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        origin_stop = s.scalar(
            select(Stop).where(Stop.route_id == service.route_id, Stop.sequence == 0)
        )
        observation = s.scalar(
            select(TripStopTime).where(TripStopTime.stop_id == origin_stop.id)
        )
        observation.estimated_arrival = NOW + timedelta(minutes=25)
        s.flush()
        r = query(s, "ESTIMATED_ARRIVAL", station="DEMO0")
        assert r.results[0]["station_id"] == origin_stop.station_id
        assert datetime.fromisoformat(
            r.results[0]["estimated_arrival"]
        ) == NOW + timedelta(minutes=25)
        assert r.results[0]["estimated_arrival"].endswith("+05:30")
