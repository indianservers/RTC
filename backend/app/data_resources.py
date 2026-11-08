"""Extend the existing allowlist with schemas derived from existing domain columns."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import create_model
from sqlalchemy import JSON

from . import catalog, links, operations, records
from .datetimes import UTCDateTime
from .domain import Alias


def extend(resources, base):
    additions = {
        "divisions": (catalog.Division, ("operator_id", "code")),
        "depots": (catalog.Depot, ("code",)),
        "station-aliases": (Alias, ("name",)),
        "bays": (operations.StationBay, ("station_id", "code")),
        "bus-type-aliases": (catalog.BusAlias, ("category_id", "name")),
        "vehicle-types": (catalog.VehicleType, ("name",)),
        "seat-layouts": (catalog.Layout, ("name",)),
        "vehicles": (catalog.Vehicle, ("registration",)),
        "vehicle-amenities": (catalog.Amenity, ("vehicle_id", "name")),
        "vehicle-assignments": (links.ServiceVehicle, ("service_id",)),
        "route-variants": (catalog.Variant, ("route_id", "name")),
        "variant-stops": (links.VariantStop, ("variant_id", "stop_id")),
        "calendars": (catalog.Calendar, ("service_id", "valid_from")),
        "stop-times": (records.ServiceStopTime, ("service_id", "stop_id")),
        "fare-tables": (records.FareTable, ("operator_id", "category_id", "name")),
        "fare-rules": (records.FareRule, ("table_id",)),
        "concessions": (catalog.Concession, ("operator_id", "name", "valid_from")),
        "concession-eligibility": (catalog.Eligibility, ("concession_id", "criterion")),
        "trips": (operations.Trip, ("service_id", "service_date")),
        "platform-assignments": (
            operations.PlatformAssignment,
            ("trip_id", "bay_id", "effective_at"),
        ),
        "delay-events": (records.DelayEvent, ("trip_id", "station_id", "effective_at")),
        "stop-observations": (
            records.TripStopTime,
            ("trip_id", "stop_id", "effective_at"),
        ),
        "service-disruptions": (records.Disruption, ("service_id", "effective_at")),
        "trip-fare-overrides": (
            records.FareOverride,
            ("trip_id", "origin_id", "destination_id"),
        ),
        "quality-issues": (
            records.QualityIssue,
            ("source_id", "batch_id", "description"),
        ),
        "data-sources": (operations.DataSource, ("code",)),
    }
    for name, (model, keys) in additions.items():
        resources[name] = (model, base, keys)
    for name, (model, schema, keys) in list(resources.items()):
        fields = {}
        for column in model.__table__.columns:
            if column.name in {"operational_state", "operational_version"}:
                continue  # Dispatcher projection is changed only through validated events.
            if column.name == "id" or column.name in schema.model_fields:
                continue
            try:
                kind = column.type.python_type
            except NotImplementedError:
                kind = datetime if "time" in str(column.type).lower() else str
            if isinstance(column.type, UTCDateTime):
                kind = datetime
            if isinstance(column.type, JSON):
                kind = dict
            if kind not in (str, int, float, bool, date, datetime, Decimal, dict, list):
                kind = str
            default = (
                column.default.arg
                if column.default is not None and not callable(column.default.arg)
                else ...
            )
            if column.nullable:
                kind = kind | None
                default = None
            fields[column.name] = (kind, default)
        resources[name] = (
            model,
            create_model(model.__name__ + "ManagedRow", __base__=schema, **fields),
            keys,
        )
