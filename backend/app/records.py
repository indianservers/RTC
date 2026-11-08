from .datetimes import UTCDateTime

"""Operational observations with explicit freshness and verification."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .domain import Base, Entity
from .operations import OperationalRecord


class DelayEvent(Entity, OperationalRecord, Base):
    __tablename__ = "trip_delay_events"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    delay_minutes: Mapped[int]
    __table_args__ = (
        CheckConstraint("delay_minutes >= 0 AND expires_at >= effective_at"),
    )


class TripStopTime(Entity, OperationalRecord, Base):
    __tablename__ = "trip_stop_times"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    stop_id: Mapped[str] = mapped_column(ForeignKey("route_stops.id"))
    estimated_departure: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    actual_departure: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    estimated_arrival: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    actual_arrival: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True))


class StatusHistory(Entity, OperationalRecord, Base):
    __tablename__ = "trip_status_history"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    status: Mapped[str]


class Location(Entity, OperationalRecord, Base):
    __tablename__ = "vehicle_locations"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))
    latitude: Mapped[Decimal]
    longitude: Mapped[Decimal]
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90 AND longitude >= -180 AND longitude <= 180"
        ),
    )


class Disruption(Entity, OperationalRecord, Base):
    __tablename__ = "service_disruptions"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    description: Mapped[str]


class Alert(Entity, OperationalRecord, Base):
    __tablename__ = "operational_alerts"
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"))
    station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    message: Mapped[str]


class QualityIssue(Entity, Base):
    __tablename__ = "data_quality_issues"
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("data_import_batches.id"))
    description: Mapped[str]
    resolved: Mapped[bool] = mapped_column(default=False)


class Audit(Entity, Base):
    __tablename__ = "audit_logs"
    actor: Mapped[str]
    entity_type: Mapped[str]
    entity_id: Mapped[str]
    operation: Mapped[str]
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))


class ServiceStopTime(Entity, Base):
    __tablename__ = "service_stop_times"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    stop_id: Mapped[str] = mapped_column(ForeignKey("route_stops.id"))
    arrival_offset: Mapped[int]
    departure_offset: Mapped[int]
    __table_args__ = (
        UniqueConstraint("service_id", "stop_id"),
        CheckConstraint("arrival_offset >= 0 AND departure_offset >= arrival_offset"),
    )


class RouteAlias(Entity, Base):
    __tablename__ = "route_aliases"
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"))
    name: Mapped[str]
    language: Mapped[str]


class RouteDistance(Entity, Base):
    __tablename__ = "route_distance_data"
    origin_stop_id: Mapped[str] = mapped_column(ForeignKey("route_stops.id"))
    destination_stop_id: Mapped[str] = mapped_column(ForeignKey("route_stops.id"))
    distance_km: Mapped[Decimal]
    __table_args__ = (CheckConstraint("distance_km >= 0"),)


class ExtraService(Entity, Base):
    __tablename__ = "extra_services"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), unique=True)
    reason: Mapped[str]


class FareTable(Entity, Base):
    __tablename__ = "fare_tables"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    category_id: Mapped[str] = mapped_column(ForeignKey("bus_service_categories.id"))
    name: Mapped[str]
    fare_class: Mapped[str]


class FareRule(Entity, Base):
    __tablename__ = "fare_rules"
    table_id: Mapped[str] = mapped_column(ForeignKey("fare_tables.id"))
    per_km: Mapped[Decimal]
    minimum: Mapped[Decimal]
    __table_args__ = (CheckConstraint("per_km >= 0 AND minimum >= 0"),)


class FareOverride(Entity, Base):
    __tablename__ = "trip_fare_overrides"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"))
    origin_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    destination_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    amount: Mapped[Decimal]
    __table_args__ = (
        UniqueConstraint("trip_id", "origin_id", "destination_id"),
        CheckConstraint("amount >= 0"),
    )


class FareHistory(Entity, Base):
    __tablename__ = "fare_history"
    fare_id: Mapped[str] = mapped_column(ForeignKey("fare_stages.id"))
    old_amount: Mapped[Decimal]
    new_amount: Mapped[Decimal]
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))


class Inventory(Entity, Base):
    __tablename__ = "trip_inventory"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), unique=True)
    reservation_enabled: Mapped[bool | None]
    capacity: Mapped[int | None]
    __table_args__ = (CheckConstraint("capacity IS NULL OR capacity >= 0"),)


class ReservationChannel(Entity, Base):
    __tablename__ = "reservation_channels"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    name: Mapped[str]
    instructions: Mapped[str]


class BookingReference(Entity, Base):
    __tablename__ = "booking_references"
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"))
    channel_id: Mapped[str] = mapped_column(ForeignKey("reservation_channels.id"))
    reference: Mapped[str]
