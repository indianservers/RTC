# ruff: noqa: B008
"""Single-server local REST board and authoritative WebSocket invalidations."""

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .availability import utc
from .dispatch import EventInput, announcement, apply_event, schedule, scope
from .domain import Category, Operator, Service, Station, Stop
from .enquiry import Enquiry
from .operations import DataSource, PlatformAssignment, StationBay, Trip
from .publication import physical_transaction
from .records import Alert, Audit, Disruption, TripStopTime


class TripInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: str
    service_date: date
    station_id: str
    source_id: str


class BoardRow(BaseModel):
    trip_id: str | None
    service_id: str
    service_date: date
    operator_id: str
    service_number: str
    origin: str
    destination: str
    category: str
    category_id: str
    scheduled_arrival: datetime
    scheduled_departure: datetime
    estimated_arrival: datetime | None = None
    estimated_departure: datetime | None = None
    actual_arrival: datetime | None = None
    actual_departure: datetime | None = None
    status: str
    phase: str
    delay_status: str
    delay_minutes: int | None = None
    delay_reason: str | None = None
    platform: dict
    version: int
    last_update: str | None
    dataset_source: str
    gps_status: str = "UNKNOWN"
    arrivals: bool
    departures: bool


class BoardResponse(BaseModel):
    data: list[BoardRow]
    counts: dict[str, int]
    total: int
    limit: int
    offset: int
    as_of: datetime


class DataResponse(BaseModel):
    data: dict[str, Any]


def board_rows(session, station_id, day, operator_id=None, category_id=None):
    station = session.get(Station, station_id)
    if not station or not station.active:
        raise HTTPException(404, "Unknown active station")
    services = (
        select(Service)
        .join(Operator, Operator.id == Service.operator_id)
        .join(Category, Category.id == Service.category_id)
        .where(
            Service.active.is_(True),
            Operator.active.is_(True),
            Category.active.is_(True),
            Service.route_id.in_(
                select(Stop.route_id).where(
                    Stop.station_id == station_id, Stop.active.is_(True)
                )
            ),
        )
    )
    if operator_id:
        services = services.where(Service.operator_id == operator_id)
    if category_id:
        services = services.where(Service.category_id == category_id)
    rows = []
    now = datetime.now(UTC)
    selected = list(session.scalars(services.limit(5001)))
    if len(selected) > 5000:
        raise HTTPException(
            422, "Board resource limit exceeded; select an operator/category"
        )
    for service in selected:
        try:
            stop, stops, arrival, departure = schedule(
                session, service, day, station_id
            )
        except HTTPException as exc:
            if exc.status_code == 422:
                continue
            raise
        trip = session.scalar(
            select(Trip).where(
                Trip.service_id == service.id,
                Trip.service_date == day,
                Trip.active.is_(True),
            )
        )
        state = (trip.operational_state or {}) if trip else {}
        current = state.get("stops", {}).get(station_id, {})
        observation = (
            session.scalar(
                select(TripStopTime)
                .where(
                    TripStopTime.trip_id == trip.id,
                    TripStopTime.stop_id == stop.id,
                    TripStopTime.verified.is_(True),
                    TripStopTime.active.is_(True),
                    TripStopTime.effective_at <= now,
                )
                .order_by(
                    TripStopTime.effective_at.desc(),
                    TripStopTime.recorded_at.desc(),
                    TripStopTime.id.desc(),
                )
            )
            if trip
            else None
        )
        fresh = observation is not None and utc(observation.expires_at) > now
        platform = (
            Enquiry(session).get_platform_assignment(trip.id, station_id, now)
            if trip
            else {"status": "unknown", "bay": None}
        )
        platform["kind"] = platform.get("kind") or (
            "DISPATCHER_CONFIRMED" if platform["status"] == "known" else "UNKNOWN"
        )
        if platform["status"] != "known" and trip:
            planned = session.scalar(
                select(PlatformAssignment)
                .join(StationBay)
                .where(
                    PlatformAssignment.trip_id == trip.id,
                    StationBay.station_id == station_id,
                    PlatformAssignment.active.is_(True),
                    PlatformAssignment.verified.is_(False),
                    PlatformAssignment.effective_at <= now,
                    PlatformAssignment.expires_at > now,
                )
                .order_by(PlatformAssignment.effective_at.desc())
            )
            if planned:
                platform = {
                    "status": "planned",
                    "kind": "PLANNED",
                    "bay": session.get(StationBay, planned.bay_id).code,
                }
        lifecycle = state.get(
            "lifecycle",
            "CANCELLED" if trip and trip.status == "cancelled" else "ACTIVE",
        )
        phase = current.get("phase", "SCHEDULED")
        delay_minutes = current.get("delay_minutes") if fresh else None
        delay_status = (
            "KNOWN"
            if fresh
            and (
                delay_minutes is not None
                or current.get("estimated_arrival")
                or current.get("estimated_departure")
            )
            else "STALE"
            if current.get("estimated_departure") or current.get("estimated_arrival")
            else "UNKNOWN"
        )
        origin = session.get(Station, stops[0].station_id)
        destination = session.get(Station, stops[-1].station_id)
        row = BoardRow(
            trip_id=trip.id if trip else None,
            service_id=service.id,
            service_date=day,
            operator_id=service.operator_id,
            service_number=service.number,
            origin=origin.name,
            destination=destination.name,
            category=session.get(Category, service.category_id).name,
            category_id=service.category_id,
            scheduled_arrival=arrival,
            scheduled_departure=departure,
            status=lifecycle
            if lifecycle != "ACTIVE"
            else phase
            if phase != "SCHEDULED"
            else "DELAYED"
            if delay_minutes
            else "SCHEDULED",
            phase=phase,
            delay_status=delay_status,
            delay_minutes=delay_minutes,
            delay_reason=current.get("delay_reason"),
            platform=platform,
            version=trip.operational_version if trip else 0,
            last_update=state.get("last_update"),
            dataset_source=trip.dataset_source if trip else service.dataset_source,
            arrivals=stop.id != stops[0].id,
            departures=stop.id != stops[-1].id,
        )
        if observation:
            row.actual_arrival = observation.actual_arrival
            row.actual_departure = observation.actual_departure
            if fresh:
                row.estimated_arrival = observation.estimated_arrival
                row.estimated_departure = observation.estimated_departure
        rows.append(row)
    return rows


def operations_router(get_engine, authenticate):
    router = APIRouter(prefix="/api/v1/operations", tags=["Local operations"])

    @router.get("/board", response_model=BoardResponse)
    def board(
        station_id: str,
        service_date: date,
        operator_id: str | None = None,
        category_id: str | None = None,
        q: str = Query("", max_length=100),
        tab: str = "all",
        after: datetime | None = None,
        before: datetime | None = None,
        sort: str = "scheduled_departure",
        descending: bool = False,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        with Session(get_engine()) as session:
            rows = board_rows(
                session, station_id, service_date, operator_id, category_id
            )
            counts = {
                "scheduled_arrivals": sum(r.arrivals for r in rows),
                "scheduled_departures": sum(r.departures for r in rows),
                "delayed_trips": sum(bool(r.delay_minutes) for r in rows),
                "cancelled_trips": sum(
                    r.status in {"CANCELLED", "SUSPENDED"} for r in rows
                ),
                "arrived_trips": sum(r.actual_arrival is not None for r in rows),
                "departed_trips": sum(r.actual_departure is not None for r in rows),
                "awaiting_platform_confirmation": sum(
                    r.platform["kind"]
                    not in {"DISPATCHER_CONFIRMED", "ACTUAL_BOARDING"}
                    for r in rows
                ),
            }
            for value in (after, before):
                if value and value.tzinfo is None:
                    raise HTTPException(422, "Time window must include timezone")
            if sort not in {
                "scheduled_departure",
                "scheduled_arrival",
                "service_number",
                "status",
                "category",
            }:
                raise HTTPException(422, "Unsupported board sort")
            if tab not in {
                "all",
                "arrivals",
                "departures",
                "delayed",
                "cancelled",
                "platforms",
            }:
                raise HTTPException(422, "Unsupported board tab")
            rows = [
                r
                for r in rows
                if (
                    not q
                    or q.casefold()
                    in f"{r.service_number} {r.origin} {r.destination} {r.category}".casefold()
                )
                and (not after or r.scheduled_departure >= after)
                and (not before or r.scheduled_departure <= before)
                and (tab not in {"arrivals", "departures"} or getattr(r, tab))
                and (tab != "delayed" or r.delay_minutes)
                and (tab != "cancelled" or r.status in {"CANCELLED", "SUSPENDED"})
            ]
            rows.sort(
                key=lambda r: (getattr(r, sort), r.service_id), reverse=descending
            )
            return BoardResponse(
                data=rows[offset : offset + limit],
                counts=counts,
                total=len(rows),
                limit=limit,
                offset=offset,
                as_of=datetime.now(UTC),
            )

    @router.get("/trips", response_model=BoardResponse)
    def trips(station_id: str, service_date: date, operator_id: str | None = None):
        return board(
            station_id=station_id,
            service_date=service_date,
            operator_id=operator_id,
            q="",
            after=None,
            before=None,
            limit=50,
            offset=0,
        )

    @router.post("/trips", response_model=DataResponse)
    def open_trip(body: TripInput, principal=Depends(authenticate)):
        with Session(get_engine()) as session, session.begin():
            physical_transaction(session, write_lock=True)
            service = session.get(Service, body.service_id)
            if not service:
                raise HTTPException(404, "Unknown service")
            scope(principal, service.operator_id, body.station_id, True)
            schedule(session, service, body.service_date, body.station_id)
            source = session.get(DataSource, body.source_id)
            if (
                not source
                or not source.active
                or source.operator_id not in {None, service.operator_id}
            ):
                raise HTTPException(422, "Active local source required")
            trip = session.scalar(
                select(Trip).where(
                    Trip.service_id == service.id,
                    Trip.service_date == body.service_date,
                )
            )
            if not trip:
                trip = Trip(
                    service_id=service.id,
                    service_date=body.service_date,
                    dataset_source=service.dataset_source,
                    source_id=source.id,
                )
                session.add(trip)
                session.flush()
                session.add(
                    Audit(
                        actor=principal.username,
                        entity_type="operations",
                        entity_id=trip.id,
                        operation="OPEN_TRIP",
                        operator_id=service.operator_id,
                        station_id=body.station_id,
                        source_id=source.id,
                        occurred_at=datetime.now(UTC),
                        recorded_at=datetime.now(UTC),
                        reason="Materialized existing dated schedule; no actual movement inferred",
                        new_values={
                            "service_id": service.id,
                            "service_date": body.service_date.isoformat(),
                        },
                        dataset_source=service.dataset_source,
                    )
                )
            if not trip.active:
                raise HTTPException(409, "Dated trip is inactive")
            return {"data": jsonable_encoder(trip)}

    @router.get("/trips/{trip_id}", response_model=DataResponse)
    def trip_detail(trip_id: str, station_id: str, principal=Depends(authenticate)):
        with Session(get_engine()) as session:
            trip = session.get(Trip, trip_id)
            if not trip:
                raise HTTPException(404, "Unknown trip")
            service = session.get(Service, trip.service_id)
            if not service:
                raise HTTPException(404, "Unknown service")
            scope(principal, service.operator_id, station_id)
            schedule(
                session,
                session.get(Service, trip.service_id),
                trip.service_date,
                station_id,
            )
            return {
                "data": {
                    **jsonable_encoder(trip),
                    "announcement_preview": announcement(
                        session, trip, station_id, datetime.now(UTC)
                    ),
                }
            }

    @router.post("/trips/{trip_id}/events", response_model=DataResponse)
    def event(trip_id: str, body: EventInput, principal=Depends(authenticate)):
        with Session(get_engine()) as session, session.begin():
            physical_transaction(session, write_lock=True)
            trip = session.scalar(
                select(Trip).where(Trip.id == trip_id).with_for_update()
            )
            if not trip or not trip.active:
                raise HTTPException(404, "Unknown active trip")
            result = apply_event(session, trip, body, principal)
            return {"data": jsonable_encoder(result)}

    @router.get("/events")
    def history(
        station_id: str,
        operator_id: str,
        trip_id: str | None = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        principal=Depends(authenticate),
    ):
        scope(principal, operator_id, station_id)
        with Session(get_engine()) as session:
            query = select(Audit).where(
                Audit.entity_type == "operations",
                Audit.operator_id == operator_id,
                Audit.station_id == station_id,
            )
            if trip_id:
                query = query.where(Audit.entity_id == trip_id)
            count = session.scalar(select(func.count()).select_from(query.subquery()))
            rows = list(
                session.scalars(
                    query.order_by(Audit.recorded_at.desc(), Audit.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            return {
                "data": jsonable_encoder(rows),
                "total": count,
                "limit": limit,
                "offset": offset,
            }

    @router.get("/platforms")
    def platforms(
        station_id: str, principal=Depends(authenticate), operator_id: str = ""
    ):
        scope(principal, operator_id, station_id)
        with Session(get_engine()) as session:
            now = datetime.now(UTC)
            bays = list(
                session.scalars(
                    select(StationBay)
                    .where(
                        StationBay.station_id == station_id, StationBay.active.is_(True)
                    )
                    .order_by(StationBay.code)
                    .limit(500)
                )
            )
            result = []
            for bay in bays:
                assignments = list(
                    session.scalars(
                        select(PlatformAssignment)
                        .join(Trip)
                        .join(Service)
                        .where(
                            PlatformAssignment.bay_id == bay.id,
                            PlatformAssignment.active.is_(True),
                            PlatformAssignment.expires_at > now,
                            Service.operator_id == operator_id,
                        )
                        .order_by(PlatformAssignment.effective_at)
                        .limit(200)
                    )
                )
                result.append(
                    {
                        "bay": jsonable_encoder(bay),
                        "occupancy": "UNKNOWN",
                        "assignments": jsonable_encoder(assignments),
                        "conflict": any(
                            a.trip_id != b.trip_id
                            and a.effective_at < b.expires_at
                            and b.effective_at < a.expires_at
                            for a in assignments
                            for b in session.scalars(
                                select(PlatformAssignment).where(
                                    PlatformAssignment.bay_id == bay.id,
                                    PlatformAssignment.active.is_(True),
                                    PlatformAssignment.verified.is_(True),
                                    PlatformAssignment.expires_at > now,
                                )
                            )
                        ),
                    }
                )
            return {"data": result}

    @router.get("/disruptions")
    def disruptions(
        station_id: str,
        operator_id: str,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        with Session(get_engine()) as session:
            now = datetime.now(UTC)
            query = (
                select(Disruption)
                .join(Service)
                .where(
                    Service.operator_id == operator_id,
                    Disruption.active.is_(True),
                    Disruption.verified.is_(True),
                    Disruption.effective_at <= now,
                    Disruption.expires_at > now,
                )
            )
            rows = [
                r
                for r in session.scalars(
                    query.order_by(Disruption.effective_at.desc()).limit(2000)
                )
                if not (r.details or {}).get("affected_station_ids")
                or station_id in (r.details or {})["affected_station_ids"]
            ]
            return {
                "data": jsonable_encoder(rows[offset : offset + limit]),
                "total": len(rows),
                "limit": limit,
                "offset": offset,
            }

    @router.get("/announcements")
    def announcements(station_id: str, limit: int = Query(50, ge=1, le=200)):
        with Session(get_engine()) as session:
            now = datetime.now(UTC)
            return {
                "data": jsonable_encoder(
                    list(
                        session.scalars(
                            select(Alert)
                            .where(
                                Alert.station_id == station_id,
                                Alert.active.is_(True),
                                Alert.verified.is_(True),
                                Alert.effective_at <= now,
                                Alert.expires_at > now,
                            )
                            .order_by(Alert.effective_at.desc())
                            .limit(limit)
                        )
                    )
                )
            }

    @router.get("/quality")
    def quality(station_id: str, operator_id: str, principal=Depends(authenticate)):
        scope(principal, operator_id, station_id)
        with Session(get_engine()) as session:
            now = datetime.now(UTC)
            query = (
                select(TripStopTime)
                .join(Trip, Trip.id == TripStopTime.trip_id)
                .join(Service, Service.id == Trip.service_id)
                .join(Stop, Stop.id == TripStopTime.stop_id)
                .where(
                    Service.operator_id == operator_id,
                    Stop.station_id == station_id,
                    TripStopTime.active.is_(True),
                )
            )
            issues = []
            for row in session.scalars(query.limit(2000)):
                if (
                    row.actual_arrival
                    and row.actual_departure
                    and utc(row.actual_departure) < utc(row.actual_arrival)
                ):
                    issues.append(
                        {
                            "code": "ACTUAL_TIME_ORDER",
                            "severity": "CRITICAL",
                            "trip_id": row.trip_id,
                            "record_id": row.id,
                            "correction": "Supervisor must append a correction; do not rewrite history.",
                        }
                    )
                if (row.estimated_arrival or row.estimated_departure) and utc(
                    row.expires_at
                ) <= now:
                    issues.append(
                        {
                            "code": "STALE_ETA",
                            "severity": "MEDIUM",
                            "trip_id": row.trip_id,
                            "record_id": row.id,
                            "correction": "Obtain a new verified estimate.",
                        }
                    )
            return {"data": issues[:200], "total": len(issues), "bounded_records": 2000}

    @router.websocket("/stream")
    async def stream(socket: WebSocket, station_id: str):
        # Public invalidation only: no tokens, actor identities or unpublished details.
        origin = socket.headers.get("origin")
        if origin and origin.split("://")[-1] != socket.headers.get("host"):
            await socket.close(code=1008)
            return
        with Session(get_engine()) as session:
            if not session.get(Station, station_id):
                await socket.close(code=1008)
                return
        await socket.accept()
        last = -1
        try:
            while True:
                with Session(get_engine()) as session:
                    from .runtime import event_revision

                    revision = event_revision(session)
                if revision != last:
                    await socket.send_json(
                        {
                            "type": "INVALIDATE",
                            "version": revision,
                            "station_id": station_id,
                            "authoritative_refetch": True,
                        }
                    )
                    last = revision
                else:
                    await socket.send_json({"type": "HEARTBEAT", "version": revision})
                await asyncio.sleep(1)
        except (WebSocketDisconnect, RuntimeError, OSError, SQLAlchemyError):
            pass

    return router
