"""Additional normalized reference domains; no passenger answers live here."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .datetimes import UTCDateTime
from .domain import Base, Entity


class State(Entity, Base):
    name_native: Mapped[str | None]
    country_code: Mapped[str | None]
    timezone: Mapped[str | None]
    __tablename__ = "states"
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class District(Entity, Base):
    code: Mapped[str | None]
    name_native: Mapped[str | None]
    __tablename__ = "districts"
    state_id: Mapped[str] = mapped_column(ForeignKey("states.id"))
    name: Mapped[str]


class City(Entity, Base):
    state_id: Mapped[str | None] = mapped_column(ForeignKey("states.id"))
    name_native: Mapped[str | None]
    __tablename__ = "cities"
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"))
    name: Mapped[str]


class Division(Entity, Base):
    __tablename__ = "operator_divisions"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    code: Mapped[str]
    name: Mapped[str]
    __table_args__ = (UniqueConstraint("operator_id", "code"),)


class Depot(Entity, Base):
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id")
    )
    name: Mapped[str | None]
    address: Mapped[str | None]
    __tablename__ = "depots"
    division_id: Mapped[str] = mapped_column(ForeignKey("operator_divisions.id"))
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"))
    code: Mapped[str] = mapped_column(unique=True)


class CityAlias(Entity, Base):
    __tablename__ = "city_aliases"
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"))
    name: Mapped[str] = mapped_column(unique=True)
    language: Mapped[str]


class VehicleType(Entity, Base):
    __tablename__ = "vehicle_types"
    name: Mapped[str]
    ac: Mapped[bool | None]
    sleeper: Mapped[bool | None]
    fuel: Mapped[str | None]
    configuration: Mapped[str | None]
    wheelchair: Mapped[bool | None]


class Layout(Entity, Base):
    __tablename__ = "vehicle_seat_layouts"
    name: Mapped[str]
    seating_capacity: Mapped[int]
    berth_capacity: Mapped[int]
    __table_args__ = (CheckConstraint("seating_capacity >= 0 AND berth_capacity >= 0"),)


class Seat(Entity, Base):
    __tablename__ = "vehicle_seats"
    layout_id: Mapped[str] = mapped_column(ForeignKey("vehicle_seat_layouts.id"))
    label: Mapped[str]
    accessible: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint("layout_id", "label"),)


class Vehicle(Entity, Base):
    __tablename__ = "vehicles"
    operator_id: Mapped[str] = mapped_column(ForeignKey("transport_operators.id"))
    type_id: Mapped[str] = mapped_column(ForeignKey("vehicle_types.id"))
    layout_id: Mapped[str] = mapped_column(ForeignKey("vehicle_seat_layouts.id"))
    registration: Mapped[str] = mapped_column(unique=True)


class Amenity(Entity, Base):
    __tablename__ = "vehicle_amenities"
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))
    name: Mapped[str]
    available: Mapped[bool]
    __table_args__ = (UniqueConstraint("vehicle_id", "name"),)


class BusAlias(Entity, Base):
    __tablename__ = "bus_type_aliases"
    category_id: Mapped[str] = mapped_column(ForeignKey("bus_service_categories.id"))
    name: Mapped[str]
    language: Mapped[str]


class Variant(Entity, Base):
    __tablename__ = "route_variants"
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"))
    name: Mapped[str]


class Calendar(Entity, Base):
    __tablename__ = "service_calendars"
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    valid_from: Mapped[date]
    valid_to: Mapped[date]
    weekdays: Mapped[str]
    departure_minutes: Mapped[int]
    __table_args__ = (
        CheckConstraint(
            "valid_to >= valid_from AND departure_minutes >= 0 AND departure_minutes < 1440"
        ),
    )


class Concession(Entity, Base):
    __tablename__ = "fare_concessions"
    operator_id: Mapped[str] = mapped_column(
        ForeignKey("transport_operators.id"), index=True
    )
    name: Mapped[str]
    valid_from: Mapped[date]
    valid_to: Mapped[date]
    percent: Mapped[Decimal]
    __table_args__ = (
        CheckConstraint("percent >= 0 AND percent <= 100 AND valid_to >= valid_from"),
    )


class Eligibility(Entity, Base):
    __tablename__ = "fare_concession_eligibility"
    concession_id: Mapped[str] = mapped_column(ForeignKey("fare_concessions.id"))
    criterion: Mapped[str]


class Facility(Entity, Base):
    facility_type: Mapped[str | None]
    accessible: Mapped[bool | None]
    is_available: Mapped[bool | None]
    __tablename__ = "station_facilities"
    station_id: Mapped[str] = mapped_column(ForeignKey("bus_stations.id"), index=True)
    name: Mapped[str]
    description: Mapped[str]


class ImportBatch(Entity, Base):
    __tablename__ = "data_import_batches"
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id"), index=True
    )
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id"))
    workflow_state: Mapped[str] = mapped_column(default="PUBLISHED", index=True)
    source_filename: Mapped[str | None]
    source_checksum: Mapped[str | None]
    uploaded_by: Mapped[str | None]
    approved_by: Mapped[str | None]
    published_by: Mapped[str | None]
    created_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True))
    payload: Mapped[dict | None] = mapped_column(JSON)
    validation_report: Mapped[dict | None] = mapped_column(JSON)
    validation_error_count: Mapped[int] = mapped_column(default=0)
    revision: Mapped[int] = mapped_column(default=1)
    resource: Mapped[str]
    digest: Mapped[str] = mapped_column(unique=True)
    row_count: Mapped[int]


class Intent(Entity, Base):
    registry_kind: Mapped[str | None]
    intent_group: Mapped[str | None]
    capability: Mapped[str | None]
    canonical_id: Mapped[str | None] = mapped_column(ForeignKey("nlp_intents.id"))
    taxonomy: Mapped[dict | None] = mapped_column(JSON)
    display_name: Mapped[str | None]
    required_slots_json: Mapped[list | None] = mapped_column(JSON)
    optional_slots_json: Mapped[list | None] = mapped_column(JSON)
    __tablename__ = "nlp_intents"
    code: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]


class Utterance(Entity, Base):
    normalized_text: Mapped[str | None]
    dataset_split: Mapped[str | None]
    source_type: Mapped[str | None]
    quality_status: Mapped[str | None]
    __tablename__ = "nlp_utterances"
    intent_id: Mapped[str] = mapped_column(ForeignKey("nlp_intents.id"))
    language: Mapped[str]
    text: Mapped[str]


class EntityType(Entity, Base):
    specification: Mapped[dict | None] = mapped_column(JSON)
    __tablename__ = "nlp_entity_types"
    code: Mapped[str] = mapped_column(unique=True)


class EntityAlias(Entity, Base):
    __tablename__ = "nlp_entity_aliases"
    type_id: Mapped[str] = mapped_column(ForeignKey("nlp_entity_types.id"))
    entity_id: Mapped[str]
    language: Mapped[str]
    text: Mapped[str]


class Template(Entity, Base):
    response_status: Mapped[str | None]
    required_placeholders_json: Mapped[list | None] = mapped_column(JSON)
    __tablename__ = "nlp_response_templates"
    intent_id: Mapped[str] = mapped_column(ForeignKey("nlp_intents.id"))
    language: Mapped[str]
    text: Mapped[str]


class Conversation(Entity, Base):
    station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    operator_id: Mapped[str | None] = mapped_column(
        ForeignKey("transport_operators.id")
    )
    __tablename__ = "conversation_sessions"
    language: Mapped[str]


class Message(Entity, Base):
    sequence_number: Mapped[int | None]
    detected_intent_id: Mapped[str | None] = mapped_column(ForeignKey("nlp_intents.id"))
    __tablename__ = "conversation_messages"
    session_id: Mapped[str] = mapped_column(ForeignKey("conversation_sessions.id"))
    role: Mapped[str]
    text: Mapped[str]


class Context(Entity, Base):
    origin_station_id: Mapped[str | None] = mapped_column(ForeignKey("bus_stations.id"))
    destination_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("bus_stations.id")
    )
    travel_date: Mapped[date | None]
    passenger_count: Mapped[int | None]
    last_trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"))
    __tablename__ = "conversation_context"
    session_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_sessions.id"), unique=True
    )
    values: Mapped[dict] = mapped_column(JSON)


class Execution(Entity, Base):
    __tablename__ = "enquiry_execution_logs"
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_sessions.id")
    )
    intent_id: Mapped[str] = mapped_column(ForeignKey("nlp_intents.id"))
    parameters: Mapped[dict] = mapped_column(JSON)
    result_count: Mapped[int]
