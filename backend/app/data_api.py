# ruff: noqa: B008
"""Local import/publication actions; existing master CRUD remains the record editor."""

import base64
import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .catalog import ImportBatch
from .data_access import Principal, read_scope
from .import_files import csv_template, map_rows, parse_file, template
from .imports import RESOURCES
from .publication import (
    approve_batch,
    audit_state,
    create_batch,
    publish_batch,
    rollback_batch,
    snapshot,
    validate_batch,
)
from .records import Audit
from .schema1a import AdminRole, AdminUser, AdminUserRole


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileUpload(Input):
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str = Field(max_length=14000000)
    operator_id: str | None = None
    source_id: str | None = None
    mapping: dict[str, str] | None = None
    mode: Literal["insert_only", "update"] = "insert_only"


class Command(Input):
    resource: str = Field(min_length=1, max_length=100)
    id: str | None = Field(default=None, min_length=1, max_length=100)
    operation: Literal["CREATE", "UPDATE", "DEACTIVATE"] = "CREATE"
    values: dict = Field(default_factory=dict)
    row: int | None = Field(default=None, ge=2)


class ChangeSet(Input):
    commands: list[Command] = Field(min_length=1, max_length=10000)
    operator_id: str | None = None
    source_id: str | None = None
    reason: str = Field(min_length=5, max_length=1000)


class Action(Input):
    revision: int = Field(ge=1)
    reason: str = Field(default="Reviewed local change", min_length=5, max_length=1000)


class Identity(Input):
    username: str = Field(min_length=3, max_length=100)
    role: Literal["EDITOR", "APPROVER"]
    operator_ids: list[str] = Field(default_factory=list, max_length=30)
    global_scope: bool = False


def batch_data(batch, detail=False):
    row = {
        c.name: getattr(batch, c.name)
        for c in batch.__table__.columns
        if c.name not in {"payload", "validation_report"}
    }
    row["rollback_eligible"] = bool(
        batch.workflow_state == "PUBLISHED"
        and batch.payload
        and batch.payload.get("commands")
    )
    if detail:
        row["validation_report"] = batch.validation_report
        row["preview_rows"] = (batch.payload or {}).get("raw_rows", [])[:20]
        row["headers"] = (batch.payload or {}).get("headers", [])
        row["mapping"] = (batch.payload or {}).get("mapping", {})
        row["command_preview"] = (batch.payload or {}).get("commands", [])[:100]
    return jsonable_encoder(row)


def allowed_batch(session, identifier, principal, lock=False):
    query = select(ImportBatch).where(ImportBatch.id == identifier)
    if lock:
        query = query.with_for_update()
    batch = session.scalar(query)
    if not batch:
        raise HTTPException(404, "Unknown change set")
    if (
        not (principal.root or principal.global_scope)
        and batch.operator_id not in principal.operators
    ):
        raise HTTPException(403, "Change set belongs to another operator")
    return batch


def management_router(get_engine, authenticate):
    router = APIRouter(prefix="/api/v1/admin")

    @router.get("/data/templates/{resource}")
    def get_template(
        resource: str,
        format: Literal["json", "csv"] = "json",
        principal: Principal = Depends(authenticate),
    ):
        if resource not in RESOURCES:
            raise HTTPException(404, "Unknown resource")
        return (
            Response(
                csv_template(resource),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="DEMO-template-{resource}.csv"'
                },
            )
            if format == "csv"
            else {"data": template(resource)}
        )

    @router.get("/data/users")
    def users(
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        principal: Principal = Depends(authenticate),
    ):
        if not principal.root:
            raise HTTPException(403, "Global administrator required")
        with Session(get_engine()) as s:
            rows = list(
                s.scalars(
                    select(AdminUser)
                    .order_by(AdminUser.username)
                    .offset(offset)
                    .limit(limit)
                )
            )
            return {
                "data": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "active": user.active,
                        "grants": [
                            {"role": role, "operator_id": operator}
                            for role, operator in s.execute(
                                select(AdminRole.role_code, AdminUserRole.operator_id)
                                .join(
                                    AdminUserRole, AdminUserRole.role_id == AdminRole.id
                                )
                                .where(
                                    AdminUserRole.user_id == user.id,
                                    AdminUserRole.active.is_(True),
                                )
                            )
                        ],
                    }
                    for user in rows
                ],
                "total": s.scalar(select(func.count()).select_from(AdminUser)),
                "limit": limit,
                "offset": offset,
            }

    @router.delete("/data/users/{identifier}")
    def revoke_user(identifier: str, principal: Principal = Depends(authenticate)):
        if not principal.root:
            raise HTTPException(403, "Global administrator required")
        with Session(get_engine()) as s, s.begin():
            user = s.get(AdminUser, identifier)
            if not user:
                raise HTTPException(404, "Unknown local user")
            user.active = False
            s.add(
                Audit(
                    actor=principal.username,
                    entity_type="admin_users",
                    entity_id=user.id,
                    operation="REVOKE",
                    recorded_at=datetime.now(UTC),
                    dataset_source="LOCAL_AUDIT",
                )
            )
            return {"data": {"id": user.id, "active": False}}

    @router.post("/data/users", status_code=201)
    def provision(body: Identity, principal: Principal = Depends(authenticate)):
        if not principal.root:
            raise HTTPException(403, "Global administrator required")
        from .domain import Operator

        with Session(get_engine()) as s, s.begin():
            if s.scalar(select(AdminUser).where(AdminUser.username == body.username)):
                raise HTTPException(409, "Username already exists")
            if (
                body.global_scope
                and body.role != "APPROVER"
                or not body.global_scope
                and not body.operator_ids
            ):
                raise HTTPException(
                    422,
                    "Global scope is for independent approvers; operator roles require operator IDs",
                )
            if any(not s.get(Operator, o) for o in body.operator_ids):
                raise HTTPException(422, "Unknown operator")
            role = s.scalar(select(AdminRole).where(AdminRole.role_code == body.role))
            if not role:
                role = AdminRole(
                    role_code=body.role,
                    description="Local data publication " + body.role,
                    dataset_source="LOCAL_ADMIN",
                )
                s.add(role)
                s.flush()
            token = secrets.token_urlsafe(36)
            user = AdminUser(
                username=body.username,
                password_hash="token:" + hashlib.sha256(token.encode()).hexdigest(),
                dataset_source="LOCAL_ADMIN",
            )
            s.add(user)
            s.flush()
            for op in {None} if body.global_scope else set(body.operator_ids):
                s.add(
                    AdminUserRole(
                        user_id=user.id,
                        role_id=role.id,
                        operator_id=op,
                        dataset_source="LOCAL_ADMIN",
                    )
                )
            s.add(
                Audit(
                    actor=principal.username,
                    entity_type="admin_users",
                    entity_id=user.id,
                    operation="PROVISION",
                    recorded_at=datetime.now(UTC),
                    dataset_source="LOCAL_AUDIT",
                )
            )
            return {
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "role": body.role,
                    "operator_ids": body.operator_ids,
                    "global_scope": body.global_scope,
                    "token": token,
                    "notice": "Copy once; only the token hash is stored. Never put this capability in a shared URL.",
                }
            }

    @router.post("/data/changes", status_code=201)
    def stage(body: ChangeSet, principal: Principal = Depends(authenticate)):
        with Session(get_engine()) as s, s.begin():
            try:
                batch = create_batch(
                    s,
                    [command.model_dump(mode="json") for command in body.commands],
                    principal,
                    body.operator_id,
                    body.source_id,
                )
                return {"data": batch_data(batch, True)}
            except (ValueError, IntegrityError) as exc:
                raise HTTPException(422, str(exc).split("\n")[0]) from exc

    @router.post("/imports/files/{resource}", status_code=201)
    def upload_file(
        resource: str, body: FileUpload, principal: Principal = Depends(authenticate)
    ):
        principal.require("edit")
        try:
            content = base64.b64decode(body.content_base64, validate=True)
            headers, rows, checksum = parse_file(body.filename, content)
            if resource not in RESOURCES:
                raise ValueError("Unsupported import resource")
            fields = RESOURCES[resource][1].model_fields
            mapping = body.mapping or {
                h: h if h in fields or h == "record_id" else "" for h in headers
            }
            # Unknown headers require explicit user mapping; do not silently drop input columns.
            if body.mapping is None and any(not v for v in mapping.values()):
                mapping = {
                    h: h
                    for h in headers
                    if h in RESOURCES[resource][1].model_fields or h == "record_id"
                }
                commands = [{"resource": resource, "operation": "CREATE", "values": {}}]
            else:
                commands = map_rows(resource, headers, rows, mapping, body.mode)
            with Session(get_engine()) as s, s.begin():
                batch = create_batch(
                    s,
                    commands,
                    principal,
                    body.operator_id,
                    body.source_id,
                    body.filename,
                    checksum,
                )
                if batch.workflow_state == "DRAFT":
                    batch.payload = {
                        **batch.payload,
                        "headers": headers,
                        "raw_rows": rows,
                        "mapping": mapping,
                        "mode": body.mode,
                        "needs_mapping": len(mapping) != len(headers),
                    }
                return {"data": batch_data(batch, True)}
        except (ValueError, KeyError, IntegrityError) as exc:
            raise HTTPException(422, str(exc).split("\n")[0][:400]) from exc

    @router.put("/imports/batches/{identifier}/mapping")
    def map_file(
        identifier: str, body: dict, principal: Principal = Depends(authenticate)
    ):
        principal.require("edit")
        with Session(get_engine()) as s, s.begin():
            from .publication import physical_transaction

            physical_transaction(s, write_lock=True)
            batch = allowed_batch(s, identifier, principal, True)
            if batch.workflow_state not in {"DRAFT", "VALIDATED"}:
                raise HTTPException(409, "Only draft mappings can change")
            if body.get("revision") != batch.revision:
                raise HTTPException(409, "Change set revision changed")
            try:
                commands = map_rows(
                    batch.resource,
                    batch.payload["headers"],
                    batch.payload["raw_rows"],
                    body["mapping"],
                    body.get("mode", "insert_only"),
                )
            except (ValueError, KeyError) as exc:
                raise HTTPException(422, str(exc)) from exc
            commands = [
                {
                    **c,
                    "id": c.get("id") or __import__("uuid").uuid4().hex,
                    "source_id": batch.source_id,
                }
                for c in commands
            ]
            batch.payload = {
                **batch.payload,
                "commands": commands,
                "mapping": body["mapping"],
                "mode": body.get("mode", "insert_only"),
                "needs_mapping": False,
            }
            batch.workflow_state = "DRAFT"
            batch.validation_report = None
            batch.validation_error_count = 0
            batch.approved_by = None
            batch.revision += 1
            audit_state(s, batch, principal, "MAPPED")
            return {"data": batch_data(batch, True)}

    @router.get("/imports/batches")
    def batches(
        operator_id: str | None = None,
        state: str | None = None,
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        principal: Principal = Depends(authenticate),
    ):
        with Session(get_engine()) as s:
            query = select(ImportBatch).where(
                read_scope("import-batches", ImportBatch, principal, operator_id)
            )
            if state:
                query = query.where(ImportBatch.workflow_state == state)
            count = s.scalar(select(func.count()).select_from(query.subquery()))
            return {
                "data": [
                    batch_data(b)
                    for b in s.scalars(
                        query.order_by(ImportBatch.created_at.desc(), ImportBatch.id)
                        .offset(offset)
                        .limit(limit)
                    )
                ],
                "total": count,
                "offset": offset,
                "limit": limit,
            }

    @router.get("/imports/batches/{identifier}")
    def batch_detail(identifier: str, principal: Principal = Depends(authenticate)):
        with Session(get_engine()) as s:
            return {"data": batch_data(allowed_batch(s, identifier, principal), True)}

    @router.post("/imports/batches/{identifier}/{action}")
    def action(
        identifier: str,
        action: Literal["validate", "approve", "publish", "rollback", "archive"],
        body: Action,
        principal: Principal = Depends(authenticate),
    ):
        with Session(get_engine()) as s, s.begin():
            from .publication import physical_transaction

            physical_transaction(s, write_lock=True)
            batch = allowed_batch(s, identifier, principal, True)
            if body.revision != batch.revision:
                raise HTTPException(
                    409, "Change set revision changed; refresh before continuing"
                )
            try:
                if action == "validate":
                    if batch.payload.get("needs_mapping"):
                        raise ValueError("Map all input columns before validation")
                    validate_batch(s, batch, principal)
                elif action == "approve":
                    approve_batch(s, batch, principal)
                elif action == "publish":
                    publish_batch(s, batch, principal)
                elif action == "rollback":
                    rollback_batch(s, batch, principal, body.reason)
                else:
                    principal.require("edit")
                    if batch.workflow_state not in {"DRAFT", "VALIDATED"}:
                        raise HTTPException(
                            409, "Only unpublished drafts can be archived"
                        )
                    batch.workflow_state = "ARCHIVED"
                    batch.revision += 1
                    audit_state(s, batch, principal, "ARCHIVED", body.reason)
                return {"data": batch_data(batch, True)}
            except (ValueError, IntegrityError) as exc:
                raise HTTPException(422, str(exc).split("\n")[0][:400]) from exc

    @router.get("/data/audit")
    def audit(
        operator_id: str | None = None,
        entity_id: str | None = None,
        batch_id: str | None = None,
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        principal: Principal = Depends(authenticate),
    ):
        with Session(get_engine()) as s:
            query = select(Audit).where(
                read_scope("audit", Audit, principal, operator_id)
            )
            if entity_id:
                query = query.where(Audit.entity_id == entity_id)
            if batch_id:
                query = query.where(Audit.batch_id == batch_id)
            count = s.scalar(select(func.count()).select_from(query.subquery()))
            return {
                "data": jsonable_encoder(
                    list(
                        s.scalars(
                            query.order_by(Audit.recorded_at.desc(), Audit.id)
                            .offset(offset)
                            .limit(limit)
                        )
                    )
                ),
                "total": count,
                "offset": offset,
                "limit": limit,
            }

    @router.post("/data/fare-preview")
    def fare_preview(body: dict, principal: Principal = Depends(authenticate)):
        from datetime import date

        from .data_access import authorize_record
        from .domain import Service
        from .fares import FareEngine
        from .publication import apply_commands, physical_transaction

        with Session(get_engine()) as s, s.begin():
            service = s.get(Service, body.get("service_id"))
            if not service:
                raise HTTPException(404, "Unknown service")
            authorize_record(
                s, "schedules", Service, {"operator_id": service.operator_id}, principal
            )
            physical_transaction(s)
            transaction = s.begin_nested()
            try:
                if body.get("batch_id"):
                    batch = allowed_batch(s, body["batch_id"], principal)
                    if batch.workflow_state not in {"VALIDATED", "APPROVED"}:
                        raise HTTPException(409, "Validate the draft before preview")
                    apply_commands(
                        s,
                        batch.payload["commands"],
                        principal,
                        batch.operator_id,
                        expected=True,
                    )
                quote = FareEngine(s).quote(
                    service.id,
                    body["origin_id"],
                    body["destination_id"],
                    date.fromisoformat(body["travel_date"]),
                )
            except (KeyError, ValueError) as exc:
                raise HTTPException(422, "Invalid fare preview parameters") from exc
            finally:
                transaction.rollback()
                s.info.pop("fare_rule_index", None)
            return {"data": quote, "live_data_changed": False}

    @router.get("/data/calendar-preview/{service_id}")
    def calendar_preview(
        service_id: str,
        start: str,
        end: str,
        principal: Principal = Depends(authenticate),
    ):
        from datetime import date, timedelta

        from .catalog import Calendar
        from .data_access import authorize_record
        from .domain import ExceptionDay, Service
        from .operations import Trip

        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError as exc:
            raise HTTPException(422, "Use ISO dates") from exc
        if last < first or (last - first).days > 30:
            raise HTTPException(422, "Preview from 1 through 31 days")
        with Session(get_engine()) as s:
            service = s.get(Service, service_id)
            if not service:
                raise HTTPException(404, "Unknown service")
            authorize_record(
                s, "schedules", Service, {"operator_id": service.operator_id}, principal
            )
            rows = []
            for offset in range((last - first).days + 1):
                day = first + timedelta(days=offset)
                cal = s.scalar(
                    select(Calendar)
                    .where(
                        Calendar.service_id == service_id,
                        Calendar.active.is_(True),
                        Calendar.valid_from <= day,
                        Calendar.valid_to >= day,
                    )
                    .order_by(Calendar.valid_from.desc(), Calendar.id)
                )
                exception = s.scalar(
                    select(ExceptionDay).where(
                        ExceptionDay.service_id == service_id,
                        ExceptionDay.service_date == day,
                        ExceptionDay.active.is_(True),
                    )
                )
                trip = s.scalar(
                    select(Trip).where(
                        Trip.service_id == service_id,
                        Trip.service_date == day,
                        Trip.active.is_(True),
                    )
                )
                details = (exception.details or {}) if exception else {}
                operates = (
                    service.active
                    and service.valid_from <= day <= service.valid_to
                    and (
                        exception.operates
                        if exception
                        else str(day.weekday())
                        in (cal.weekdays if cal else service.weekdays)
                    )
                    and not (trip and trip.status == "cancelled")
                )
                rows.append(
                    {
                        "date": day.isoformat(),
                        "operates": bool(operates),
                        "departure_minutes": details.get(
                            "departure_minutes",
                            cal.departure_minutes if cal else service.departure_minutes,
                        ),
                        "planned_departure_at": jsonable_encoder(
                            trip.planned_departure_at
                        )
                        if trip
                        else None,
                        "exception": snapshot(exception),
                        "basis": "PUBLISHED_LOCAL_RECORDS",
                    }
                )
            return {"data": rows}

    @router.post("/data/copy-service/{service_id}")
    def copy_service(
        service_id: str, body: dict, principal: Principal = Depends(authenticate)
    ):
        from uuid import uuid4

        from .catalog import Calendar
        from .data_access import authorize_record
        from .domain import Fare, Service
        from .links import ServiceVehicle
        from .records import ServiceStopTime

        principal.require("edit")
        with Session(get_engine()) as s, s.begin():
            original = s.get(Service, service_id)
            if not original:
                raise HTTPException(404, "Unknown service")
            authorize_record(s, "schedules", Service, snapshot(original), principal)
            if not isinstance(body.get("number"), str) or not body["number"].strip():
                raise HTTPException(422, "Provide a new service number")
            copied = str(uuid4())
            values = {
                k: v
                for k, v in snapshot(original).items()
                if k in RESOURCES["schedules"][1].model_fields
            }
            values["number"] = body["number"]
            commands = [
                {
                    "resource": "schedules",
                    "id": copied,
                    "operation": "CREATE",
                    "values": values,
                }
            ]
            for resource, model in (
                ("calendars", Calendar),
                ("stop-times", ServiceStopTime),
                ("fares", Fare),
                ("vehicle-assignments", ServiceVehicle),
            ):
                for row in s.scalars(
                    select(model).where(
                        model.service_id == service_id, model.active.is_(True)
                    )
                ):
                    values = {
                        k: v
                        for k, v in snapshot(row).items()
                        if k in RESOURCES[resource][1].model_fields
                    }
                    values["service_id"] = copied
                    commands.append(
                        {"resource": resource, "operation": "CREATE", "values": values}
                    )
            batch = create_batch(s, commands, principal, original.operator_id)
            return {"data": batch_data(batch, True)}

    @router.post("/data/copy-variant/{variant_id}")
    def copy_variant(
        variant_id: str, body: dict, principal: Principal = Depends(authenticate)
    ):
        from uuid import uuid4

        from .catalog import Variant
        from .data_access import authorize_record, owner
        from .links import VariantStop

        principal.require("edit")
        with Session(get_engine()) as s, s.begin():
            original = s.get(Variant, variant_id)
            if not original:
                raise HTTPException(404, "Unknown variant")
            authorize_record(
                s, "route-variants", Variant, snapshot(original), principal
            )
            if not isinstance(body.get("name"), str) or not body["name"].strip():
                raise HTTPException(422, "Provide the new variant name")
            identifier = str(uuid4())
            commands = [
                {
                    "resource": "route-variants",
                    "id": identifier,
                    "operation": "CREATE",
                    "values": {
                        "route_id": original.route_id,
                        "name": body["name"],
                        "dataset_source": original.dataset_source,
                    },
                }
            ]
            commands.extend(
                {
                    "resource": "variant-stops",
                    "operation": "CREATE",
                    "values": {
                        "variant_id": identifier,
                        "stop_id": row.stop_id,
                        "dataset_source": row.dataset_source,
                    },
                }
                for row in s.scalars(
                    select(VariantStop).where(
                        VariantStop.variant_id == variant_id,
                        VariantStop.active.is_(True),
                    )
                )
            )
            batch = create_batch(
                s, commands, principal, owner(s, Variant, snapshot(original))
            )
            return {"data": batch_data(batch, True)}

    @router.get("/data/export/{resource}")
    def export_records(
        resource: str,
        principal: Principal = Depends(authenticate),
        operator_id: str | None = None,
    ):
        import csv
        import io

        if resource not in RESOURCES:
            raise HTTPException(404, "Unknown resource")
        model: Any = RESOURCES[resource][0]
        with Session(get_engine()) as s:
            records = list(
                s.scalars(
                    select(model)
                    .where(read_scope(resource, model, principal, operator_id))
                    .order_by(model.id)
                    .limit(10001)
                )
            )
            if len(records) > 10000:
                raise HTTPException(
                    422, "Narrow the operator scope; export limit is 10000 records"
                )
            stream = io.StringIO()
            writer = csv.writer(stream)
            columns = [c.name for c in model.__table__.columns]
            writer.writerow(["record_id" if c == "id" else c for c in columns])
            for row in records:
                values = []
                for c in columns:
                    value = getattr(row, c)
                    if isinstance(value, (dict, list)):
                        value = __import__("json").dumps(value, ensure_ascii=False)
                    if isinstance(value, str) and value[:1] in "=+-@":
                        value = "'" + value
                    values.append(value)
                writer.writerow(values)
            return Response(
                stream.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="local-{resource}.csv"'
                },
            )

    @router.post("/data/apsrtc-configuration")
    def apsrtc_configuration(principal: Principal = Depends(authenticate)):
        from uuid import uuid4

        from .domain import Operator

        if not principal.root:
            raise HTTPException(
                403, "Global administrator required for initial shared configuration"
            )
        brands = [
            "Pallevelugu",
            "Express",
            "Ultra Deluxe",
            "Super Luxury",
            "Indra",
            "Amaravathi",
            "Dolphin Cruise",
            "Vennela",
            "Vennela Economy",
            "Saptagiri services",
            "Metro Express",
            "Metro Luxury",
            "Electric services",
        ]
        with Session(get_engine()) as s, s.begin():
            if s.scalar(
                select(Operator.id).where(func.lower(Operator.code) == "apsrtc")
            ):
                raise HTTPException(
                    409,
                    "APSRTC already exists; maintain its categories through the existing editors",
                )
            identifier = str(uuid4())
            commands = [
                {
                    "resource": "operators",
                    "id": identifier,
                    "operation": "CREATE",
                    "values": {
                        "code": "APSRTC",
                        "name": "APSRTC",
                        "dataset_source": "USER_PROVIDED_CONFIGURATION",
                    },
                }
            ]
            commands.extend(
                {
                    "resource": "bus-types",
                    "operation": "CREATE",
                    "values": {
                        "operator_id": identifier,
                        "name": name,
                        "dataset_source": "USER_PROVIDED_CONFIGURATION",
                    },
                }
                for name in brands
            )
            batch = create_batch(
                s,
                commands,
                principal,
                filename="user-requested-apsrtc-configuration.json",
            )
            return {
                "data": batch_data(batch, True),
                "notice": "Unpublished configuration from the user's requested names. No official stations, vehicles, facilities, timetables, fares or operational records are invented.",
            }

    @router.get("/data/overview")
    def overview(
        operator_id: str | None = None, principal: Principal = Depends(authenticate)
    ):
        with Session(get_engine()) as s:
            counts = {}
            for resource, (untyped_model, _, _) in RESOURCES.items():
                model: Any = untyped_model
                counts[resource] = s.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(
                        model.active.is_(True),
                        read_scope(resource, model, principal, operator_id),
                    )
                )
            query = (
                select(ImportBatch.workflow_state, func.count())
                .where(
                    read_scope("import-batches", ImportBatch, principal, operator_id)
                )
                .group_by(ImportBatch.workflow_state)
            )
            return {
                "data": {
                    "counts": counts,
                    "workflow_counts": dict(s.execute(query).all()),
                    "actor": principal.username,
                    "role": principal.role,
                    "operator_ids": principal.operators,
                    "demo_bypass": __import__("os").getenv(
                        "RTC_ALLOW_DEMO_DIRECT_WRITES"
                    )
                    == "1",
                }
            }

    return router
