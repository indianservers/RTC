from .datetimes import UTCDateTime

"""Dated operational records; separate from recurring schedules."""

from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .domain import Base, Entity


class Trip(Entity, Base):
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"))
    planned_departure_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id"))
    __tablename__ = "trips"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(default="scheduled")
    __table_args__ = (
        UniqueConstraint("service_id", "service_date"),
        CheckConstraint("status IN ('scheduled','cancelled','running','completed')"),
    )


class DataSource(Entity, Base):
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id")
    )
    source_type: Mapped[str | None]
    trust_level: Mapped[str | None]
    is_official: Mapped[bool | None]
    is_demo: Mapped[bool | None]
    __tablename__ = "data_sources"
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class OperationalRecord:
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    recorded_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    effective_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))
    verified: Mapped[bool] = mapped_column(default=False)


class SeatSnapshot(Entity, OperationalRecord, Base):
    origin_station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    destination_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("bus_stations.id")
    )
    seat_class: Mapped[str | None]
    __tablename__ = "seat_availability_snapshots"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    available: Mapped[int | None]
    __table_args__ = (
        CheckConstraint("available IS NULL OR available >= 0"),
        CheckConstraint("expires_at >= effective_at"),
    )


class StationBay(Entity, Base):
    bay_name: Mapped[str | None]
    floor_or_zone: Mapped[str | None]
    accessible: Mapped[bool | None]
    __tablename__ = "station_bays"
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), index=True)
    code: Mapped[str]
    __table_args__ = (UniqueConstraint("station_id", "code"),)


class PlatformAssignment(Entity, OperationalRecord, Base):
    __tablename__ = "platform_assignments"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    bay_id: Mapped[str] = mapped_column(ForeignKey("station_bays.id"))
    __table_args__ = (CheckConstraint("expires_at >= effective_at"),)
