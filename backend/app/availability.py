from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .operations import SeatSnapshot


def utc(value: datetime) -> datetime:
    # SQLite stores UTC values without the timezone marker.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def seat_availability(
    session: Session,
    trip_id: str,
    at: datetime,
    requested: int = 1,
    origin_station_id: str | None = None,
    destination_station_id: str | None = None,
) -> dict:
    if at.tzinfo is None or requested < 1:
        raise ValueError("Aware timestamp and positive requested seats required")
    query = select(SeatSnapshot).where(
        SeatSnapshot.trip_id == trip_id, SeatSnapshot.active.is_(True)
    )
    if origin_station_id is not None or destination_station_id is not None:
        query = query.where(
            SeatSnapshot.origin_station_id == origin_station_id,
            SeatSnapshot.destination_station_id == destination_station_id,
        )
    rows = session.scalars(query.order_by(SeatSnapshot.effective_at.desc()))
    for row in rows:
        if utc(row.effective_at) > utc(at) or not row.verified:
            continue
        status = (
            "stale"
            if utc(row.expires_at) <= utc(at)
            else (
                "unknown"
                if row.available is None
                else ("available" if row.available >= requested else "not_available")
            )
        )
        return {
            "status": status,
            "known_vacant": row.available,
            "source_id": row.source_id,
            "recorded_at": utc(row.recorded_at),
            "effective_at": utc(row.effective_at),
            "dataset_source": row.dataset_source,
        }
    return {"status": "unknown", "known_vacant": None}
