"""Transactional staging over existing ImportBatch/Audit records, never live drafts."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .catalog import Calendar, ImportBatch, Variant
from .data_access import authorize_record
from .domain import Alias, ExceptionDay, Fare, Route, Service, Station, Stop
from .imports import RESOURCES, validate_relations
from .operations import DataSource, PlatformAssignment, StationBay, Trip
from .records import Audit, FareHistory, FareOverride, FareRule, ServiceStopTime

MAX_ROWS = 10000


def snapshot(row):
    return (
        jsonable_encoder(
            {c.name: getattr(row, c.name) for c in row.__table__.columns},
            custom_encoder={
                Decimal: lambda v: format(v.normalize(), "f"),
                datetime: lambda v: (
                    v.astimezone(UTC).isoformat() if v.tzinfo else v.isoformat()
                ),
            },
        )
        if row
        else None
    )


def physical_transaction(session, write_lock=False):
    # Python sqlite legacy transaction mode otherwise lets a released top-level savepoint commit.
    connection = session.connection()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE" if write_lock else "BEGIN")
    if write_lock and connection.dialect.name == "postgresql":
        from sqlalchemy import text

        connection.execute(text("SELECT pg_advisory_xact_lock(7041501)"))


def check_values(session, model, values, identifier):
    if values.get("active") is False:
        return
    if any(
        values.get(name, 0) > 10080
        for name in ("arrival_offset", "departure_offset", "offset_minutes")
    ):
        raise ValueError(
            "Elapsed schedule offsets must stay within the supported seven-day horizon"
        )
    if values.get("amount") is not None and values["amount"] != values[
        "amount"
    ].quantize(Decimal("0.01")):
        raise ValueError("Currency amounts support at most two decimal places")
    for name, value in values.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Timezone offset required: " + name)
    if model is not Stop:
        validate_relations(
            session, model, {k: v for k, v in values.items() if v is not None}
        )
    else:
        for name, parent in (("route_id", Route), ("station_id", Station)):
            if not session.get(parent, values[name]):
                raise ValueError("Unknown reference: " + name)
    for name in (
        "amount",
        "percent",
        "per_km",
        "minimum",
        "arrival_offset",
        "departure_offset",
        "offset_minutes",
        "distance_km",
        "delay_minutes",
    ):
        if values.get(name) is not None and values[name] < 0:
            raise ValueError("Negative value: " + name)
    if values.get("percent", 0) > 100:
        raise ValueError("Concession percent exceeds 100")
    if "weekdays" in values and (
        not values["weekdays"] or any(c not in "0123456" for c in values["weekdays"])
    ):
        raise ValueError("Invalid operating weekdays")
    if values.get("expires_at") is not None:
        if values["effective_at"].tzinfo is None or values["expires_at"].tzinfo is None:
            raise ValueError("Operational timestamps require timezone offsets")
        if values["expires_at"] < values["effective_at"]:
            raise ValueError("Operational expiry precedes effective time")
    if values.get("arrival_offset", 0) > values.get("departure_offset", 10**9):
        raise ValueError("Arrival offset exceeds departure offset")
    if model in (Fare, Calendar) and values.get("active", True):
        query = select(model).where(
            model.active.is_(True),
            model.id != identifier,
            model.service_id == values["service_id"],
            model.valid_from <= values["valid_to"],
            model.valid_to >= values["valid_from"],
        )
        if model is Fare:
            query = query.where(
                model.origin_id == values["origin_id"],
                model.destination_id == values["destination_id"],
            )
        if session.scalar(query) is not None:
            raise ValueError("Conflicting overlapping effective records")
    for column in model.__table__.columns:
        for fk in column.foreign_keys:
            value = values.get(column.name)
            if value is not None:
                table = fk.column.table
                if not session.execute(
                    select(table.c.id).where(
                        fk.column == value, table.c.active.is_(True)
                    )
                ).first():
                    raise ValueError("Missing or inactive reference: " + column.name)
    if model is Route and values.get("direction") not in {
        None,
        "OUTBOUND",
        "INBOUND",
        "LOOP",
        "OTHER",
    }:
        raise ValueError("Unsupported route direction")
    if model is Stop:
        arrival = values.get("arrival_offset_minutes")
        departure = values.get("departure_offset_minutes")
        if arrival is not None and (
            arrival < 0 or arrival > 10079 or arrival != values["offset_minutes"]
        ):
            raise ValueError(
                "Route arrival offset must match legacy offset_minutes and stay within the seven-day bound"
            )
        if departure is not None and (
            departure < values["offset_minutes"] or departure > 10079
        ):
            raise ValueError(
                "Route departure precedes arrival or exceeds supported offset bounds"
            )
    if model is Service:
        if values.get("depot_id"):
            from .catalog import Depot

            depot = session.get(Depot, values["depot_id"])
            if depot.operator_id and depot.operator_id != values["operator_id"]:
                raise ValueError("Depot belongs to another operator")
        if values.get("service_type") not in {"REGULAR", "SPECIAL", "SEASONAL"}:
            raise ValueError("Unsupported service type")
    if model in (Fare, FareOverride):
        service = session.get(
            Service,
            values["service_id"]
            if model is Fare
            else session.get(Trip, values["trip_id"]).service_id,
        )
        origin = session.scalar(
            select(Stop).where(
                Stop.route_id == service.route_id,
                Stop.station_id == values["origin_id"],
                Stop.active.is_(True),
            )
        )
        destination = session.scalar(
            select(Stop).where(
                Stop.route_id == service.route_id,
                Stop.station_id == values["destination_id"],
                Stop.active.is_(True),
            )
        )
        if not origin or not destination or origin.sequence >= destination.sequence:
            raise ValueError("Fare segment must follow the service route stop sequence")
    if model is ServiceStopTime:
        service = session.get(Service, values["service_id"])
        stop = session.get(Stop, values["stop_id"])
        if service.route_id != stop.route_id:
            raise ValueError("Stop time belongs to a different service route")
    if model is PlatformAssignment:
        trip = session.get(Trip, values["trip_id"])
        service = session.get(Service, trip.service_id)
        bay = session.get(StationBay, values["bay_id"])
        if not session.scalar(
            select(Stop.id).where(
                Stop.route_id == service.route_id,
                Stop.station_id == bay.station_id,
                Stop.active.is_(True),
            )
        ):
            raise ValueError("Platform station is not on the trip route")
    if model in (ExceptionDay, Calendar):
        service = session.get(Service, values["service_id"])
        first = values.get("service_date") or values["valid_from"]
        last = values.get("service_date") or values["valid_to"]
        if not service.valid_from <= first <= last <= service.valid_to:
            raise ValueError("Calendar/exception lies outside service effective dates")
    if model is ExceptionDay:
        kind = values.get("exception_type")
        if kind:
            if kind not in {
                "ADDED_SERVICE",
                "CANCELLED_SERVICE",
                "TEMPORARY_SUSPENSION",
                "FESTIVAL_EXTRA",
                "CHANGED_DEPARTURE",
                "ROUTE_DIVERSION",
                "PARTIAL_STOP_CANCELLATION",
                "BOARDING_RESTRICTION",
            }:
                raise ValueError("Unsupported service exception type")
            if not values.get("reason") or len(values["reason"].strip()) < 5:
                raise ValueError("An operational exception requires a reason")
            details = values.get("details") or {}
            allowed = {
                "departure_minutes",
                "variant_id",
                "cancelled_stop_ids",
                "boarding_restricted_stop_ids",
            }
            if set(details) - allowed:
                raise ValueError("Unknown service exception detail")
            if (
                kind in {"CANCELLED_SERVICE", "TEMPORARY_SUSPENSION"}
                and values["operates"]
            ):
                raise ValueError("Cancelled/suspended service cannot operate")
            if (
                kind not in {"CANCELLED_SERVICE", "TEMPORARY_SUSPENSION"}
                and not values["operates"]
            ):
                raise ValueError("An added/changed service must be marked operating")
            if kind == "CHANGED_DEPARTURE" and not (
                isinstance(details.get("departure_minutes"), int)
                and not isinstance(details["departure_minutes"], bool)
                and 0 <= details["departure_minutes"] < 1440
            ):
                raise ValueError("Changed departure requires valid departure_minutes")
            service = session.get(Service, values["service_id"])
            if kind == "ROUTE_DIVERSION":
                variant = (
                    session.get(Variant, details.get("variant_id"))
                    if details.get("variant_id")
                    else None
                )
                if (
                    not variant
                    or not variant.active
                    or variant.route_id != service.route_id
                ):
                    raise ValueError(
                        "Diversion requires an active variant on the service route"
                    )
            for key in ("cancelled_stop_ids", "boarding_restricted_stop_ids"):
                if key in details and (
                    not isinstance(details[key], list) or not details[key]
                ):
                    raise ValueError(
                        "Stop restrictions require a nonempty stop ID list"
                    )
                for stop_identifier in details.get(key, []):
                    stop = session.get(Stop, stop_identifier)
                    if not stop or not stop.active or stop.route_id != service.route_id:
                        raise ValueError("Exception stop is not on this route")
            if kind == "PARTIAL_STOP_CANCELLATION" and not details.get(
                "cancelled_stop_ids"
            ):
                raise ValueError("Choose cancelled stops")
            if kind == "BOARDING_RESTRICTION" and not details.get(
                "boarding_restricted_stop_ids"
            ):
                raise ValueError("Choose restricted boarding stops")
    if model is FareRule:
        if (
            values.get("flat_surcharge", 0) < 0
            or values.get("percent_surcharge", 0) < 0
        ):
            raise ValueError("Negative surcharge")
        if not values.get("valid_from") or not values.get("valid_to"):
            raise ValueError("New fare rules require effective dates")
        query = select(FareRule).where(
            FareRule.id != identifier,
            FareRule.table_id == values["table_id"],
            FareRule.active.is_(True),
        )
        for other in session.scalars(query):
            if (
                other.valid_from is None
                or other.valid_to is None
                or other.valid_from <= values["valid_to"]
                and other.valid_to >= values["valid_from"]
            ):
                raise ValueError("Overlapping active fare rules")
    if model is Alias:
        # Alias names never merge station identities. Normalize only for lookup/duplicate detection.
        values["normalized_alias"] = " ".join(values["name"].casefold().split())
        conflict = session.scalar(
            select(Alias).where(
                Alias.active.is_(True),
                Alias.id != identifier,
                func.lower(Alias.name) == values["normalized_alias"],
            )
        )
        station = session.scalar(
            select(Station).where(
                Station.active.is_(True),
                func.lower(Station.name) == values["normalized_alias"],
                Station.id != values["station_id"],
            )
        )
        if conflict or station:
            raise ValueError("Alias conflicts with an existing station name or alias")


def final_integrity(session, commands):
    routes = set()
    services = set()
    variants = set()
    from .links import VariantStop

    for c in commands:
        model = RESOURCES[c["resource"]][0]
        row = session.get(model, c["id"])
        if row and model is Stop:
            routes.add(row.route_id)
        if row and model is VariantStop:
            variants.add(row.variant_id)
        if not row or not row.active:
            continue
        if model is Route:
            routes.add(row.id)
        if model is Stop:
            routes.add(row.route_id)
        if model is Service:
            services.add(row.id)
            routes.add(row.route_id)
        if model is Variant:
            variants.add(row.id)
        if model is VariantStop:
            variants.add(row.variant_id)
        if model is ServiceStopTime:
            services.add(row.service_id)
    for route_id in routes:
        if not session.get(Route, route_id).active:
            continue
        stops = list(
            session.scalars(
                select(Stop)
                .where(Stop.route_id == route_id, Stop.active.is_(True))
                .order_by(Stop.sequence)
            )
        )
        if len(stops) < 2:
            raise ValueError("A published route requires at least two active stops")
        if len({s.sequence for s in stops}) != len(stops) or any(
            (
                a.departure_offset_minutes
                if a.departure_offset_minutes is not None
                else a.offset_minutes
            )
            > (
                b.arrival_offset_minutes
                if b.arrival_offset_minutes is not None
                else b.offset_minutes
            )
            or a.distance_km > b.distance_km
            for a, b in pairwise(stops)
        ):
            raise ValueError(
                "Route stop sequence, distance or elapsed time is inconsistent"
            )
    for variant_id in variants:
        variant = session.get(Variant, variant_id)
        if not variant.active:
            continue
        members = list(
            session.scalars(
                select(Stop)
                .join(VariantStop, VariantStop.stop_id == Stop.id)
                .where(
                    VariantStop.variant_id == variant_id,
                    VariantStop.active.is_(True),
                    Stop.active.is_(True),
                )
            )
        )
        if len(members) < 2 or any(
            stop.route_id != variant.route_id for stop in members
        ):
            raise ValueError(
                "A published route variant requires at least two active stops on its route"
            )
    for service_id in services:
        service = session.get(Service, service_id)
        stops = list(
            session.scalars(
                select(Stop)
                .where(Stop.route_id == service.route_id, Stop.active.is_(True))
                .order_by(Stop.sequence)
            )
        )
        if service.route_variant_id:
            memberships = set(
                session.scalars(
                    select(VariantStop.stop_id).where(
                        VariantStop.variant_id == service.route_variant_id,
                        VariantStop.active.is_(True),
                    )
                )
            )
            stops = [stop for stop in stops if stop.id in memberships]
            if len(stops) < 2:
                raise ValueError("Service variant has no valid ordered stop list")
        times = {
            r.stop_id: r
            for r in session.scalars(
                select(ServiceStopTime).where(
                    ServiceStopTime.service_id == service_id,
                    ServiceStopTime.active.is_(True),
                )
            )
        }
        if times:
            if any(s.id not in times for s in stops):
                raise ValueError(
                    "A stop-wise timetable must cover every active route stop"
                )
            ordered = [times[s.id] for s in stops]
            if any(a.departure_offset > b.arrival_offset for a, b in pairwise(ordered)):
                raise ValueError("Impossible stop arrival/departure order")


def apply_commands(
    session, commands, principal, operator_id=None, expected=False, progress=None
):
    prepared = []
    seen = set()
    for item in commands:
        if progress is not None:
            progress["row"] = item.get("row")
        resource = item["resource"]
        if resource not in RESOURCES:
            raise ValueError("Unsupported resource")
        model, schema, keys = RESOURCES[resource]
        identifier = item["id"]
        if (resource, identifier) in seen:
            raise ValueError("A record occurs more than once in the change set")
        seen.add((resource, identifier))
        row = session.get(model, identifier)
        before = snapshot(row)
        if expected and before != item.get("before"):
            raise HTTPException(
                409,
                "Published records changed after validation; validate and approve again",
            )
        operation = item.get("operation", "CREATE")
        if operation not in {"CREATE", "UPDATE", "DEACTIVATE", "UNCHANGED"}:
            raise ValueError("Unsupported record operation")
        if operation == "CREATE" and row or operation != "CREATE" and not row:
            raise ValueError(
                "Create/update target no longer matches the requested operation"
            )
        if row:
            authorize_record(session, resource, model, before, principal, operator_id)
        raw = item.get("values") or {
            k: before[k] for k in schema.model_fields if k in before
        }
        raw = dict(raw)
        if (
            "source_id" in schema.model_fields
            and "source_id" not in raw
            and item.get("source_id")
        ):
            raw["source_id"] = item["source_id"]
        if "recorded_at" in schema.model_fields and "recorded_at" not in raw:
            raw["recorded_at"] = datetime.now(UTC)
        values = schema.model_validate(raw).model_dump()
        if operation == "DEACTIVATE":
            values["active"] = False
        prepared.append((item, model, values, row, before, keys))
    # Reserve sequence slots before an explicitly approved reorder; retain all stop IDs.
    for item, model, _, row, _, _ in prepared:
        if model is Stop and row and item.get("operation") != "UNCHANGED":
            row.sequence += 1000000
    session.flush()
    changed = []
    for item, model, values, row, before, keys in prepared:
        if progress is not None:
            progress["row"] = item.get("row")
        authorize_record(
            session,
            item["resource"],
            model,
            {**values, "id": item["id"]},
            principal,
            operator_id,
        )
        check_values(session, model, values, item["id"])
        conflict = session.scalar(
            select(model).where(
                *(
                    func.lower(getattr(model, k)) == values[k].casefold()
                    if isinstance(values[k], str) and not k.endswith("_id")
                    else getattr(model, k) == values[k]
                    for k in keys
                ),
                model.id != item["id"],
            )
        )
        if conflict:
            if item.get("operation", "CREATE") == "CREATE" and all(
                getattr(conflict, k) == v for k, v in values.items()
            ):
                changed.append(
                    {
                        **item,
                        "id": conflict.id,
                        "operation": "UNCHANGED",
                        "before": snapshot(conflict),
                        "after": snapshot(conflict),
                    }
                )
                continue
            raise ValueError(
                "Duplicate natural key with an existing record; use explicit update mode and record_id"
            )
        if item.get("operation") == "UNCHANGED":
            if any(getattr(row, k) != v for k, v in values.items()):
                raise ValueError("An unchanged row changed after validation")
            changed.append({**item, "before": before, "after": snapshot(row)})
            continue
        if values.get("dataset_source", "").upper() in {
            "OFFICIAL",
            "APSRTC",
            "TGSRTC",
            "TNSTC",
            "MTC",
        }:
            source = (
                session.get(DataSource, item.get("source_id"))
                if item.get("source_id")
                else None
            )
            if not source or not source.is_official or source.is_demo:
                raise ValueError(
                    "Official provenance requires a reviewed non-demo official data source"
                )
        reviewed_source = (
            session.get(DataSource, item["source_id"])
            if item.get("source_id")
            else None
        )
        if (
            reviewed_source
            and reviewed_source.is_official
            and not reviewed_source.is_demo
        ):
            if values["dataset_source"] in {"DEMO", "SYNTHETIC"}:
                raise ValueError(
                    "Fictional rows cannot be imported as an official source"
                )
            for column in model.__table__.columns:
                for fk in column.foreign_keys:
                    if values.get(column.name) is not None:
                        parent = session.execute(
                            select(fk.column.table.c.dataset_source).where(
                                fk.column == values[column.name]
                            )
                        ).scalar()
                        if parent in {"DEMO", "SYNTHETIC"}:
                            raise ValueError(
                                "Official data cannot depend on fictional reference records"
                            )
        if (
            row
            and before.get("dataset_source") in {"DEMO", "SYNTHETIC"}
            and values["dataset_source"] not in {"DEMO", "SYNTHETIC"}
        ):
            raise ValueError(
                "Demo provenance cannot be relabelled as official or operational data"
            )
        if not row:
            row = model(id=item["id"], **values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        session.flush()
        changed.append({**item, "before": before, "after": snapshot(row)})
    final_integrity(session, changed)
    return changed


def create_batch(
    session,
    commands,
    principal,
    operator_id=None,
    source_id=None,
    filename=None,
    checksum=None,
):
    principal.require("edit")
    if not principal.root and operator_id not in principal.operators:
        raise HTTPException(403, "Choose an authorized operator")
    if not 1 <= len(commands) <= MAX_ROWS:
        raise ValueError("Change set must contain 1 to 10000 rows")
    if source_id:
        source = session.get(DataSource, source_id)
        if (
            not source
            or not source.active
            or source.operator_id not in (None, operator_id)
        ):
            raise ValueError("Unknown or other-operator data source")
    for command in commands:
        if command.get("resource") not in RESOURCES:
            raise ValueError("Unsupported change resource")
        model = RESOURCES[command["resource"]][0]
        if command.get("operation", "CREATE") != "CREATE":
            current = (
                session.get(model, command.get("id")) if command.get("id") else None
            )
            if not current:
                raise HTTPException(404, "Unknown change target")
            authorize_record(
                session,
                command["resource"],
                model,
                snapshot(current),
                principal,
                operator_id,
            )
        elif not principal.root:
            from .data_access import SHARED, owner

            values = command.get("values") or {}
            resolved = owner(session, model, values)
            if (
                command["resource"] in SHARED
                or resolved
                and resolved not in principal.operators
            ):
                raise HTTPException(
                    403, "Record is outside your data-management authorization"
                )
    normalized = []
    for number, item in enumerate(commands, 2):
        normalized.append(
            {
                **item,
                "operation": item.get("operation", "CREATE"),
                "id": item.get("id") or str(uuid4()),
                "row": item.get("row") or number,
                "source_id": source_id,
            }
        )
    digest = hashlib.sha256(
        json.dumps(
            {
                "operator": operator_id,
                "source": source_id,
                "checksum": checksum,
                "commands": commands,
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    existing = session.scalar(select(ImportBatch).where(ImportBatch.digest == digest))
    if existing:
        return existing
    batch = ImportBatch(
        resource=normalized[0]["resource"]
        if len({c["resource"] for c in normalized}) == 1
        else "bundle",
        digest=digest,
        row_count=len(normalized),
        operator_id=operator_id,
        source_id=source_id,
        source_filename=filename,
        source_checksum=checksum or digest,
        uploaded_by=principal.username,
        workflow_state="DRAFT",
        created_at=datetime.now(UTC),
        payload={"commands": normalized},
        dataset_source="LOCAL_STAGING",
    )
    session.add(batch)
    session.flush()
    audit_state(session, batch, principal, "DRAFT")
    return batch


def audit_state(session, batch, principal, operation, reason=None):
    session.add(
        Audit(
            actor=principal.username,
            entity_type="data_import_batches",
            entity_id=batch.id,
            operation=operation,
            recorded_at=datetime.now(UTC),
            batch_id=batch.id,
            operator_id=batch.operator_id,
            reason=reason or (batch.payload or {}).get("reason", "Local data change"),
            new_values={
                "workflow_state": batch.workflow_state,
                "validation_error_count": batch.validation_error_count,
                "validation_report": batch.validation_report,
            }
            if operation == "VALIDATION_FAILED"
            else {"workflow_state": batch.workflow_state},
            dataset_source="LOCAL_AUDIT",
        )
    )


def validate_batch(session, batch, principal):
    principal.require("edit")
    if batch.workflow_state not in {"DRAFT", "VALIDATED"}:
        raise HTTPException(409, "Only draft changes can be validated")
    physical_transaction(session)
    errors = []
    changes = []
    for item in batch.payload["commands"]:
        try:
            schema = RESOURCES[item["resource"]][1]
            raw = dict(item.get("values") or {})
            if item.get("operation") == "DEACTIVATE":
                continue
            if "source_id" in schema.model_fields and item.get("source_id"):
                raw.setdefault("source_id", item["source_id"])
            if "recorded_at" in schema.model_fields:
                raw.setdefault("recorded_at", datetime.now(UTC))
            values = schema.model_validate(raw).model_dump()
            for name, value in values.items():
                if hasattr(value, "is_finite") and not value.is_finite():
                    raise ValueError("Nonfinite decimal: " + name)
        except (ValueError, KeyError) as exc:
            errors.append(
                {
                    "row": item.get("row"),
                    "severity": "CRITICAL",
                    "message": (
                        "; ".join(
                            f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
                            for error in exc.errors(include_input=False)
                        )
                        if isinstance(exc, ValidationError)
                        else str(exc).split("\n")[0]
                    )[:1000],
                }
            )
    if errors:
        batch.validation_report = {
            "errors": errors,
            "valid_rows": 0,
            "total_rows": batch.row_count,
            "preview": [],
        }
        batch.workflow_state = "DRAFT"
        batch.validation_error_count = len(errors)
        batch.revision += 1
        audit_state(session, batch, principal, "VALIDATION_FAILED")
        return batch
    progress = {}
    transaction = session.begin_nested()
    try:
        changes = apply_commands(
            session,
            batch.payload["commands"],
            principal,
            batch.operator_id,
            progress=progress,
        )
    except (ValueError, IntegrityError) as exc:
        errors.append(
            {
                "row": progress.get("row"),
                "severity": "CRITICAL",
                "message": str(exc).split("\n")[0][:400],
            }
        )
    finally:
        transaction.rollback()
    batch.validation_error_count = len(errors)
    batch.validation_report = {
        "errors": errors,
        "valid_rows": len(changes),
        "total_rows": batch.row_count,
        "preview": changes[:100],
        "preview_truncated": len(changes) > 100,
        "duplicates": sum(c.get("operation") == "UNCHANGED" for c in changes),
    }
    if not errors:
        batch.payload = {**batch.payload, "commands": changes}
        batch.workflow_state = "VALIDATED"
    else:
        batch.workflow_state = "DRAFT"
    batch.approved_by = None
    batch.revision += 1
    audit_state(
        session, batch, principal, "VALIDATED" if not errors else "VALIDATION_FAILED"
    )
    return batch


def approve_batch(session, batch, principal):
    principal.require("approve")
    if batch.workflow_state != "VALIDATED" or batch.validation_report.get("errors"):
        raise HTTPException(409, "Validate all records before approval")
    if principal.username == batch.uploaded_by:
        raise HTTPException(
            403, "A different authorized user must approve this change set"
        )
    batch.workflow_state = "APPROVED"
    batch.approved_by = principal.username
    batch.revision += 1
    audit_state(session, batch, principal, "APPROVED")
    return batch


def record_change(session, batch, principal, change, operation=None):
    model = RESOURCES[change["resource"]][0]
    version = (
        session.scalar(
            select(func.max(Audit.version)).where(
                Audit.entity_type == change["resource"], Audit.entity_id == change["id"]
            )
        )
        or 0
    ) + 1
    before, after = change["before"], change["after"]
    fields = [
        k
        for k in (after or before or {})
        if (before or {}).get(k) != (after or {}).get(k)
    ]
    session.add(
        Audit(
            actor=principal.username,
            entity_type=change["resource"],
            entity_id=change["id"],
            operation=operation or change.get("operation", "CREATE"),
            recorded_at=datetime.now(UTC),
            batch_id=batch.id,
            operator_id=batch.operator_id,
            version=version,
            previous_values=before,
            new_values=after,
            changed_fields=fields,
            dataset_source="LOCAL_AUDIT",
        )
    )
    if model is Fare and before and before["amount"] != after["amount"]:
        session.add(
            FareHistory(
                fare_id=change["id"],
                old_amount=before["amount"],
                new_amount=after["amount"],
                recorded_at=datetime.now(UTC),
                dataset_source=after["dataset_source"],
            )
        )


def publish_batch(session, batch, principal):
    principal.require("publish")
    if batch.workflow_state != "APPROVED":
        raise HTTPException(409, "Only approved changes may be published")
    changes = apply_commands(
        session, batch.payload["commands"], principal, batch.operator_id, expected=True
    )
    for change in changes:
        record_change(session, batch, principal, change)
    batch.workflow_state = "PUBLISHED"
    batch.published_by = principal.username
    batch.published_at = datetime.now(UTC)
    batch.revision += 1
    audit_state(session, batch, principal, "PUBLISHED")
    return batch


def rollback_batch(session, batch, principal, reason):
    principal.require("rollback")
    if batch.workflow_state != "PUBLISHED" or not batch.payload:
        raise HTTPException(409, "This batch is not eligible for rollback")
    entries = list(
        session.scalars(
            select(Audit)
            .where(Audit.batch_id == batch.id, Audit.version.is_not(None))
            .order_by(Audit.recorded_at.desc(), Audit.id.desc())
        )
    )
    affected = {
        (RESOURCES[a.entity_type][0].__tablename__, a.entity_id) for a in entries
    }
    for entry in entries:
        model = RESOURCES[entry.entity_type][0]
        row = session.get(model, entry.entity_id)
        if snapshot(row) != entry.new_values:
            raise HTTPException(
                409,
                "A record changed since publication; rollback would overwrite newer work",
            )
        if entry.previous_values is None:
            for table in model.metadata.tables.values():
                for column in table.columns:
                    for fk in column.foreign_keys:
                        if fk.column.table is model.__table__:
                            for ref in session.execute(
                                select(table.c.id).where(
                                    column == entry.entity_id, table.c.active.is_(True)
                                )
                            ):
                                if (table.name, ref[0]) not in affected:
                                    raise HTTPException(
                                        409,
                                        "New dependent records prevent safe rollback",
                                    )
    # Reserve existing stop sequences before restoring an earlier ordering.
    for entry in entries:
        model = RESOURCES[entry.entity_type][0]
        row = session.get(model, entry.entity_id)
        if model is Stop:
            row.sequence += 2000000
    session.flush()
    for entry in entries:
        model, schema, _ = RESOURCES[entry.entity_type]
        row = session.get(model, entry.entity_id)
        if entry.previous_values is None:
            row.active = False
        else:
            values = schema.model_validate(
                {
                    k: v
                    for k, v in entry.previous_values.items()
                    if k in schema.model_fields
                }
            ).model_dump()
            for key, value in values.items():
                setattr(row, key, value)
        session.flush()
        record_change(
            session,
            batch,
            principal,
            {
                "resource": entry.entity_type,
                "id": entry.entity_id,
                "before": entry.new_values,
                "after": snapshot(row),
            },
            "ROLLBACK",
        )
    batch.workflow_state = "ARCHIVED"
    batch.revision += 1
    audit_state(session, batch, principal, "ROLLED_BACK", reason)
    return batch
