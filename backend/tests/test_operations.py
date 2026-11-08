from datetime import UTC, date, datetime, timedelta

from app.availability import seat_availability
from app.domain import Base, Service, database
from app.operations import DataSource, SeatSnapshot, Trip
from app.seed import seed
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_inventory_states():
    engine = database("sqlite://")
    Base.metadata.create_all(engine)
    seed(engine)
    at = datetime(2026, 11, 8, tzinfo=UTC)
    with Session(engine) as session:
        service = session.scalar(select(Service))
        trip = Trip(service_id=service.id, service_date=date(2026, 11, 8))
        source = DataSource(code="test", name="DEMO")
        session.add_all([trip, source])
        session.flush()
        assert seat_availability(session, trip.id, at)["status"] == "unknown"
        snapshot = SeatSnapshot(
            trip_id=trip.id,
            source_id=source.id,
            effective_at=at,
            expires_at=at + timedelta(minutes=10),
            available=2,
            verified=True,
        )
        session.add(snapshot)
        session.flush()
        assert seat_availability(session, trip.id, at, 2)["status"] == "available"
        assert seat_availability(session, trip.id, at, 3)["status"] == "not_available"
        assert (
            seat_availability(session, trip.id, at + timedelta(minutes=10))["status"]
            == "stale"
        )
