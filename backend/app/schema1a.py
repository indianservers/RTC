"""Additive Phase 1A entities; existing identifiers and names are preserved."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .datetimes import UTCDateTime
from .domain import Base, Entity


class ServiceArea(Entity, Base):
    __tablename__ = "operator_service_areas"
    operator_id: Mapped[str] = mapped_column(
        ForeignKey("transport_operators.id"), index=True
    )
    state_id: Mapped[str] = mapped_column(ForeignKey("states.id"), index=True)
    service_area_type: Mapped[str]
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from"),
        UniqueConstraint("operator_id", "state_id", "effective_from"),
    )


class StationAccess(Entity, Base):
    __tablename__ = "operator_station_access"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"))
    __table_args__ = (UniqueConstraint("operator_id", "station_id"),)


class AmenityDefinition(Entity, Base):
    __tablename__ = "amenities"
    code: Mapped[str] = mapped_column(unique=True)
    name_en: Mapped[str]
    name_native: Mapped[str | None]
    description: Mapped[str | None]


class ContactPoint(Entity, Base):
    __tablename__ = "station_contact_points"
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), index=True)
    contact_type: Mapped[str]
    label: Mapped[str]
    contact_value: Mapped[str]
    opening_hours: Mapped[str | None]
    last_verified_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )


class Annotation(Entity, Base):
    __tablename__ = "nlp_entity_annotations"
    utterance_id: Mapped[str] = mapped_column(
        ForeignKey("nlp_utterances.id"), index=True
    )
    entity_type_id: Mapped[str] = mapped_column(ForeignKey("nlp_entity_types.id"))
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    surface_text: Mapped[str]
    canonical_value: Mapped[str]
    review_status: Mapped[str] = mapped_column(default="PENDING")
    __table_args__ = (
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset"),
    )


class AdminUser(Entity, Base):
    __tablename__ = "admin_users"
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]


class AdminRole(Entity, Base):
    __tablename__ = "admin_roles"
    role_code: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]


class AdminUserRole(Entity, Base):
    station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    __tablename__ = "admin_user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("admin_roles.id"))
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id")
    )
