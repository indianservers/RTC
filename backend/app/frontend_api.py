# ruff: noqa: B008
"""Thin local app adapters. Enquiry, fare and conversation logic stay in their engines."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from .catalog import Amenity, Calendar, Depot, ImportBatch, Vehicle, VehicleType
from .domain import Category, Operator, Service, Station
from .enquiry import Enquiry, JourneyQuery
from .fares import FareEngine
from .imports import RESOURCES
from .links import ServiceVehicle
from .nlp.inference import EnglishInferenceService
from .nlp.pipeline import NLPRequest
from .operations import PlatformAssignment
from .records import DelayEvent, Disruption, FareRule, Location, TripStopTime
from .status import OperationalStatusEngine


def app_router(get_engine, require_admin):
    router = APIRouter(prefix="/api/v1")

    @router.get("/app/bootstrap")
    def bootstrap():
        with Session(get_engine()) as s:
            counts = {
                name: s.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.active.is_(True))
                )
                for name, model in (
                    ("operators", Operator),
                    ("stations", Station),
                    ("services", Service),
                )
            }
            sources = list(
                s.scalars(
                    select(Service.dataset_source)
                    .where(Service.active.is_(True))
                    .distinct()
                )
            )
            return {
                "data": {
                    "counts": counts,
                    "default_station": jsonable_encoder(
                        s.scalar(
                            select(Station)
                            .where(Station.active.is_(True))
                            .order_by(Station.code)
                            .limit(1)
                        )
                    ),
                    "sources": sources,
                    "operators": jsonable_encoder(
                        list(
                            s.scalars(
                                select(Operator)
                                .where(Operator.active.is_(True))
                                .order_by(Operator.name)
                            )
                        )
                    ),
                    "categories": jsonable_encoder(
                        list(
                            s.scalars(
                                select(Category)
                                .where(Category.active.is_(True))
                                .order_by(Category.name)
                            )
                        )
                    ),
                }
            }

    @router.get("/app/services/{service_id}")
    def details(service_id: str, travel_date: date):
        with Session(get_engine()) as s:
            e = Enquiry(s)
            try:
                service = e.get_service_details(service_id)
                stops = e.get_route_stops(service_id, travel_date)
                stations = {
                    x.station_id: e.repository.resolve_station(x.station_id)
                    for x in stops
                }
                category = s.get(Category, service.category_id)
                operator = s.get(Operator, service.operator_id)
                vehicle = s.scalar(
                    select(Vehicle)
                    .join(ServiceVehicle, ServiceVehicle.vehicle_id == Vehicle.id)
                    .where(
                        ServiceVehicle.service_id == service_id,
                        ServiceVehicle.active.is_(True),
                    )
                )
                kind = s.get(VehicleType, vehicle.type_id) if vehicle else None
                rows = []
                at = None
                if len(stops) >= 2:
                    at = datetime.combine(
                        travel_date,
                        time.min,
                        ZoneInfo(stations[stops[0].station_id].timezone),
                    )
                    rows = [
                        r
                        for r in e._rows(
                            JourneyQuery(
                                origin=stops[0].station_id,
                                destination=stops[-1].station_id,
                                at=at,
                            )
                        )
                        if r["service_id"] == service_id
                        and r["service_date"] == travel_date
                    ]
                row = rows[0] if rows else None
                trip_id = e.get_service_status(service_id, travel_date).get("trip_id")
                observed_at = datetime.now(UTC)
                status = (
                    OperationalStatusEngine(s).status(trip_id, observed_at)
                    if trip_id and at is not None
                    else {"status": "SCHEDULED_ONLY", "gps_status": "UNKNOWN"}
                )
                expiry = None
                if trip_id:
                    from .availability import utc

                    observations = union_all(
                        *(
                            select(model.expires_at.label("expires_at")).where(
                                model.trip_id == trip_id,
                                model.active.is_(True),
                                model.verified.is_(True),
                                model.effective_at <= observed_at,
                                model.expires_at > observed_at,
                            )
                            for model in (
                                TripStopTime,
                                DelayEvent,
                                Location,
                                PlatformAssignment,
                            )
                        )
                    ).subquery()
                    value = s.scalar(select(func.min(observations.c.expires_at)))
                    expiry = utc(value).isoformat() if value else None
                from .records import ServiceStopTime

                offsets = {
                    t.stop_id: t
                    for t in s.scalars(
                        select(ServiceStopTime).where(
                            ServiceStopTime.service_id == service_id,
                            ServiceStopTime.active.is_(True),
                        )
                    )
                }
                first_offset = (
                    offsets[stops[0].id].departure_offset
                    if stops and stops[0].id in offsets
                    else (
                        stops[0].departure_offset_minutes
                        if stops[0].departure_offset_minutes is not None
                        else stops[0].offset_minutes
                    )
                    if stops
                    else 0
                )
                timeline = [
                    {
                        **jsonable_encoder(stop),
                        "station_name": stations[stop.station_id].name,
                        "scheduled_at": (
                            row["scheduled_departure"]
                            + timedelta(
                                minutes=(
                                    offsets[stop.id].departure_offset
                                    if stop.id in offsets
                                    else stop.departure_offset_minutes
                                    if stop.departure_offset_minutes is not None
                                    else stop.offset_minutes
                                )
                                - first_offset
                            )
                        ).isoformat()
                        if row
                        else None,
                    }
                    for stop in stops
                ]
                return {
                    "data": {
                        "operational_as_of": observed_at.isoformat(),
                        "operational_expires_at": expiry,
                        "service": jsonable_encoder(service),
                        "operator": jsonable_encoder(operator),
                        "category": jsonable_encoder(category),
                        "vehicle_type": jsonable_encoder(kind),
                        "stops": timeline,
                        "journey": jsonable_encoder(row),
                        "status": jsonable_encoder(status),
                        "platform": e.get_platform_assignment(
                            trip_id, stops[0].station_id, observed_at
                        )
                        if trip_id and at is not None
                        else {"status": "unknown", "bay": None},
                        "concessions": e.get_concessions(
                            service.operator_id, travel_date
                        ),
                        "fare": FareEngine(s).quote(
                            service_id,
                            stops[0].station_id,
                            stops[-1].station_id,
                            travel_date,
                        )
                        if len(stops) > 1
                        else None,
                        "amenities": jsonable_encoder(
                            list(
                                s.scalars(
                                    select(Amenity).where(
                                        Amenity.vehicle_id == vehicle.id,
                                        Amenity.active.is_(True),
                                    )
                                )
                            )
                        )
                        if vehicle
                        else [],
                    }
                }
            except ValueError as exc:
                raise HTTPException(404, str(exc)) from exc

    @router.get("/admin/ui/metadata", dependencies=[Depends(require_admin)])
    def metadata(principal=Depends(require_admin)):
        with Session(get_engine()):
            batch = (
                None  # Existing import batches have no timestamp; recency is unknown.
            )
            return {
                "data": {
                    "resources": {
                        key: {
                            "schema": schema.model_json_schema(),
                            "editable": True,
                            "references": {
                                column.name: target
                                for column in model.__table__.columns
                                for fk in column.foreign_keys
                                for target, (target_model, _, _) in RESOURCES.items()
                                if target_model.__tablename__ == fk.column.table.name
                            },
                        }
                        for key, (model, schema, _) in RESOURCES.items()
                    },
                    "readonly": ["import-batches", "location-updates"],
                    "latest_import": jsonable_encoder(batch),
                    "role": principal.role,
                    "actor": principal.username,
                    "operator_ids": principal.operators,
                    "demo_bypass": __import__("os").getenv(
                        "RTC_ALLOW_DEMO_DIRECT_WRITES"
                    )
                    == "1",
                    "publication_required": __import__("os").getenv(
                        "RTC_ALLOW_DEMO_DIRECT_WRITES"
                    )
                    != "1",
                    "permissions": {
                        "read": True,
                        "write_resources": list(RESOURCES)
                        if principal.root
                        else [
                            r
                            for r in RESOURCES
                            if r
                            not in __import__(
                                "app.data_access", fromlist=["SHARED"]
                            ).SHARED
                        ]
                        if principal.role == "EDITOR"
                        else [],
                    },
                }
            }

    @router.get("/admin/ui/catalog/{resource}", dependencies=[Depends(require_admin)])
    def readonly(
        resource: str,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        q: str = Query("", max_length=100),
        sort_by: str = "id",
        descending: bool = False,
        active: bool | None = None,
        operator_id: str | None = None,
        principal=Depends(require_admin),
    ):
        model: Any = {
            "depots": Depot,
            "trips": __import__("app.operations", fromlist=["Trip"]).Trip,
            "delay-events": DelayEvent,
            "stop-observations": TripStopTime,
            "service-disruptions": Disruption,
            "location-updates": Location,
            "fare-rules": FareRule,
            "calendars": Calendar,
            "platform-assignments": PlatformAssignment,
            "import-batches": ImportBatch,
        }.get(resource)
        if model is None:
            raise HTTPException(404, "Unknown read-only resource")
        from .admin_listing import list_records

        with Session(get_engine()) as s:
            try:
                return list_records(
                    s,
                    model,
                    limit,
                    offset,
                    q,
                    sort_by,
                    descending,
                    active,
                    __import__("app.data_access", fromlist=["read_scope"]).read_scope(
                        resource, model, principal, operator_id
                    ),
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

    @router.get("/admin/ui/data-quality", dependencies=[Depends(require_admin)])
    def data_quality(
        audit_date: date | None = None,
        kind: str | None = None,
        severity: Literal["ERROR", "WARNING", "INFO"] | None = None,
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        operator_id: str | None = None,
        principal=Depends(require_admin),
    ):
        from .data_quality import quality_report

        now = datetime.now(UTC)
        with Session(get_engine()) as s:
            return {
                "data": quality_report(
                    s,
                    now,
                    audit_date or now.astimezone(ZoneInfo("Asia/Kolkata")).date(),
                    kind,
                    severity,
                    limit,
                    offset,
                    principal,
                    operator_id,
                )
            }

    @router.post("/admin/ui/diagnostics", dependencies=[Depends(require_admin)])
    def diagnostics(request: NLPRequest):
        from datetime import UTC

        with Session(get_engine()) as s:
            return EnglishInferenceService(s).interpret_query(
                request.model_copy(update={"debug": True, "session_id": None}),
                datetime.now(UTC),
            )

    return router
