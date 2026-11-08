"""Allowlisted offline CSV import. Every file commits atomically."""

import csv
import hashlib
import io
import os
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .catalog import City, District, ImportBatch, Intent, State, Template, Utterance
from .domain import (
    Category,
    ExceptionDay,
    Fare,
    Operator,
    Route,
    Service,
    Station,
    Stop,
)


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    dataset_source: str = Field(min_length=1)


class OperatorRow(Row):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)


class StationRow(OperatorRow):
    timezone: str = "Asia/Kolkata"


class CategoryRow(Row):
    operator_id: str
    name: str = Field(min_length=1)


class RouteRow(Row):
    code: str = Field(min_length=1)


class StopRow(Row):
    route_id: str
    station_id: str
    sequence: int = Field(ge=0)
    offset_minutes: int = Field(ge=0)
    distance_km: Decimal = Field(ge=0)
    boarding: bool = True
    alighting: bool = True


class ServiceRow(Row):
    operator_id: str
    category_id: str
    route_id: str
    number: str = Field(min_length=1)
    departure_minutes: int = Field(ge=0, lt=1440)
    weekdays: str = "0123456"
    valid_from: date
    valid_to: date


class FareRow(Row):
    service_id: str
    origin_id: str
    destination_id: str
    amount: Decimal = Field(ge=0)
    valid_from: date
    valid_to: date


class ExceptionRow(Row):
    service_id: str
    service_date: date
    operates: bool


class StateRow(Row):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)


class DistrictRow(Row):
    state_id: str
    name: str = Field(min_length=1)


class CityRow(Row):
    district_id: str
    name: str = Field(min_length=1)


class IntentRow(Row):
    code: str = Field(min_length=1, max_length=80)
    description: str


class UtteranceRow(Row):
    dataset_split: str | None = None
    normalized_text: str | None = None
    intent_id: str
    language: str
    text: str = Field(min_length=1, max_length=2000)
    source_type: str = "RULE"
    quality_status: str = "PENDING"


class TemplateRow(Row):
    intent_id: str
    language: str
    response_status: str
    text: str = Field(min_length=1, max_length=4000)


RESOURCES: dict[str, tuple[type, type[BaseModel], tuple[str, ...]]] = {
    "nlp-intents": (Intent, IntentRow, ("code",)),
    "nlp-rules": (Utterance, UtteranceRow, ("intent_id", "language", "text")),
    "nlp-templates": (
        Template,
        TemplateRow,
        ("intent_id", "language", "response_status"),
    ),
    "states": (State, StateRow, ("code",)),
    "districts": (District, DistrictRow, ("state_id", "name")),
    "cities": (City, CityRow, ("district_id", "name")),
    "operators": (Operator, OperatorRow, ("code",)),
    "stations": (Station, StationRow, ("code",)),
    "bus-types": (Category, CategoryRow, ("operator_id", "name")),
    "routes": (Route, RouteRow, ("code",)),
    "stops": (Stop, StopRow, ("route_id", "sequence")),
    "schedules": (Service, ServiceRow, ("operator_id", "number")),
    "fares": (
        Fare,
        FareRow,
        ("service_id", "origin_id", "destination_id", "valid_from"),
    ),
    "calendar-exceptions": (ExceptionDay, ExceptionRow, ("service_id", "service_date")),
}


def validate_relations(session, model, values):
    for column in model.__table__.columns:
        for fk in column.foreign_keys:
            value = values.get(column.name)
            if (
                value is not None
                and session.execute(select(fk.column).where(fk.column == value)).first()
                is None
            ):
                raise ValueError(f"Unknown reference: {column.name}")
    if values.get("valid_to", date.max) < values.get("valid_from", date.min):
        raise ValueError("valid_to precedes valid_from")
    if model is Station:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(values["timezone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Invalid station timezone") from exc
    if model is Service:
        if not values["weekdays"] or any(
            x not in "0123456" for x in values["weekdays"]
        ):
            raise ValueError("Invalid weekdays")
        category = session.get(Category, values["category_id"])
        if category.operator_id != values["operator_id"]:
            raise ValueError("Category belongs to another operator")
    if model is Stop:
        rows = session.scalars(
            select(Stop).where(
                Stop.route_id == values["route_id"], Stop.sequence != values["sequence"]
            )
        )
        for row in rows:
            if (
                row.sequence < values["sequence"]
                and (
                    row.distance_km > values["distance_km"]
                    or row.offset_minutes > values["offset_minutes"]
                )
            ) or (
                row.sequence > values["sequence"]
                and (
                    row.distance_km < values["distance_km"]
                    or row.offset_minutes < values["offset_minutes"]
                )
            ):
                raise ValueError("Stop distance/time ordering is inconsistent")


def import_csv(session: Session, resource: str, text: str, dry_run: bool = True):
    if not dry_run and os.getenv("RTC_ALLOW_DEMO_DIRECT_WRITES")!="1":
        raise ValueError("Direct CSV commit is disabled; use staged validation, approval and publication")
    if resource not in RESOURCES:
        raise ValueError("Unsupported import resource")
    if len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("Import exceeds 2 MB")
    model, schema, keys = RESOURCES[resource]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Missing or duplicate CSV headers")
    errors = []
    inserted = 0
    duplicates = 0
    seen = set()
    transaction = session.begin_nested()
    try:
        for number, raw in enumerate(reader, 2):
            if number > 10001:
                errors.append({"row": number, "error": "Maximum 10000 rows"})
                break
            try:
                values = schema.model_validate(raw).model_dump()
                key = tuple(values[k] for k in keys)
                if key in seen:
                    raise ValueError("Duplicate key within CSV")
                seen.add(key)
                existing = session.scalar(
                    select(model).where(*(getattr(model, k) == values[k] for k in keys))
                )
                if existing:
                    if all(getattr(existing, k) == v for k, v in values.items()):
                        duplicates += 1
                        continue
                    raise ValueError("Existing key has conflicting data")
                validate_relations(session, model, values)
                with session.begin_nested():
                    session.add(model(**values))
                    session.flush()
                inserted += 1
            except (ValueError, ValidationError, IntegrityError) as exc:
                errors.append({"row": number, "error": str(exc).split("\n")[0]})
        digest = hashlib.sha256((resource + "\n" + text).encode()).hexdigest()
        if errors or dry_run:
            transaction.rollback()
        else:
            if not session.scalar(
                select(ImportBatch).where(ImportBatch.digest == digest)
            ):
                session.add(
                    ImportBatch(
                        resource=resource,
                        digest=digest,
                        row_count=inserted,
                        dataset_source="LOCAL_IMPORT",
                    )
                )
            transaction.commit()
    except Exception:
        transaction.rollback()
        raise
    return {
        "committed": not dry_run and not errors,
        "inserted": inserted if not errors else 0,
        "duplicates": duplicates,
        "errors": errors,
        "dry_run": dry_run,
    }

from .data_resources import extend

extend(RESOURCES, Row)
