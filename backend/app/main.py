# ruff: noqa: B008
from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import Category, Operator, Service, Station, database
from .nlp.inference import EnglishInferenceService

app = FastAPI(title="RTC offline enquiry — Phase 1 foundation")
engine = database()


@app.get("/api/v1/{resource}")
def reference(
    resource: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
):
    model = {
        "operators": Operator,
        "stations": Station,
        "bus-types": Category,
        "services": Service,
        "routes": __import__("app.domain", fromlist=["Route"]).Route,
    }.get(resource)
    if model is None:
        raise HTTPException(404, "Unknown resource")
    with Session(engine) as session:
        rows = session.scalars(
            select(model)
            .where(model.active.is_(True))
            .order_by(model.__table__.c.id)
            .offset(offset)
            .limit(limit)
        )
        return {
            "data": [
                {c.name: getattr(row, c.name) for c in model.__table__.columns}
                for row in rows
            ],
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/v1/enquiry/next-bus")
def next_bus(
    origin: str,
    destination: str,
    at: datetime,
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
    amenity: str | None = None,
):
    with Session(engine) as session:
        try:
            return {
                "data": Enquiry(session).get_next_buses(
                    JourneyQuery(
                        origin=origin,
                        destination=destination,
                        at=cast(datetime, at),
                        category=category,
                        amenity=amenity,
                        limit=limit,
                    )
                )
            }
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


import os
from typing import Annotated, cast

from fastapi import Body, Depends, Header
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError

from .enquiry import Enquiry, JourneyQuery
from .imports import RESOURCES, import_csv, validate_relations


@app.get("/api/v1/enquiry/{kind}")
def enquiry(
    kind: str,
    origin: str = "",
    destination: str = "",
    at: datetime | None = None,
    day: date | None = None,
    service_id: str = "",
    trip_id: str = "",
    station: str = "",
    operator: str | None = None,
    category: str | None = None,
    amenity: str | None = None,
    via: str = "",
    requested: int = Query(1, ge=1, le=100),
    minimum_transfer: int = Query(15, ge=1, le=180),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with Session(engine) as session:
        e = Enquiry(session)
        try:
            if (
                kind in ("first-bus", "last-bus", "status", "concessions")
                and day is None
            ):
                raise ValueError("Explicit operating day required")
            if kind in ("platform", "availability") and (
                at is None or at.tzinfo is None
            ):
                raise ValueError("Explicit aware timestamp required")
            if kind == "service":
                result = e.get_service_details(service_id)
            elif kind == "route":
                result = e.get_route_stops(service_id)
            elif kind == "platform":
                result = e.get_platform_assignment(trip_id, station, cast(datetime, at))
            elif kind == "availability":
                result = e.get_seat_availability(trip_id, cast(datetime, at), requested)
            elif kind == "status":
                result = e.get_service_status(service_id, cast(date, day))
            elif kind == "facilities":
                result = e.get_station_facilities(station)
            elif kind == "concessions":
                result = e.get_concessions(operator or "", cast(date, day))
            elif kind == "operator-services":
                result = e.get_operator_services(operator or "", limit, offset)
            else:
                if at is None and day is not None:
                    from datetime import time
                    from zoneinfo import ZoneInfo

                    resolved = e.repository.resolve_station(origin)
                    at = datetime.combine(day, time.min, ZoneInfo(resolved.timezone))
                q = JourneyQuery(
                    origin=origin,
                    destination=destination,
                    at=cast(datetime, at),
                    category=category,
                    amenity=amenity,
                    operator=operator,
                    limit=limit,
                    offset=offset,
                )
                methods = {
                    "fare": e.get_bus_fare,
                    "bus-types": e.get_available_bus_types,
                    "duration": e.get_journey_duration,
                    "arrival": e.get_arrival_time,
                    "cheapest": e.get_cheapest_services,
                    "fastest": e.get_fastest_services,
                    "direct": e.get_direct_services,
                }
                if kind == "first-bus":
                    result = e.get_first_bus(q, cast(date, day))
                elif kind == "last-bus":
                    result = e.get_last_bus(q, cast(date, day))
                elif kind == "connections":
                    result = e.get_connecting_services(q, minimum_transfer)
                elif kind == "via":
                    result = e.get_services_via_stop(q, via)
                elif kind in methods:
                    result = methods[kind](q)
                else:
                    raise HTTPException(404, "Unknown enquiry")
            return {"data": jsonable_encoder(result), "limit": limit, "offset": offset}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


from .data_access import Principal, authenticate, read_scope


def admin(authorization: Annotated[str | None, Header()] = None):
    return authenticate(engine, authorization)


def staged_write(
    session,
    resource,
    values,
    principal,
    identifier=None,
    operation="CREATE",
    operator_id=None,
    source_id=None,
):
    from .data_api import batch_data
    from .publication import create_batch

    batch = create_batch(
        session,
        [
            {
                "resource": resource,
                "operation": operation,
                "id": identifier,
                "values": values,
            }
        ],
        principal,
        operator_id,
        source_id,
    )
    return {
        "data": batch_data(batch, True),
        "publication_state": "DRAFT",
        "message": "Draft stored. Validate, obtain independent approval, and publish before passenger use.",
    }


@app.post("/api/v1/admin/imports/{resource}", dependencies=[Depends(admin)])
def upload(
    resource: str,
    text: Annotated[str, Body(media_type="text/csv")],
    dry_run: bool = True,
    principal: Principal = Depends(admin),
    operator_id: str | None = Header(None, alias="X-Operator-ID"),
    source_id: str | None = Header(None, alias="X-Data-Source"),
):
    with Session(engine) as session, session.begin():
        try:
            if os.getenv("RTC_ALLOW_DEMO_DIRECT_WRITES") != "1" or not principal.root:
                from .import_files import map_rows, parse_file

                headers, rows, checksum = parse_file("upload.csv", text.encode("utf-8"))
                from .data_api import batch_data
                from .publication import create_batch, validate_batch

                batch = create_batch(
                    session,
                    map_rows(resource, headers, rows),
                    principal,
                    operator_id,
                    source_id,
                    "upload.csv",
                    checksum,
                )
                validate_batch(session, batch, principal)
                return {
                    "data": {
                        "committed": False,
                        "inserted": 0,
                        "duplicates": 0,
                        "errors": batch.validation_report["errors"],
                        "dry_run": dry_run,
                        "batch_id": batch.id,
                        "publication_state": batch.workflow_state,
                        "batch": batch_data(batch, True),
                    }
                }
            return {"data": import_csv(session, resource, text, dry_run)}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/admin/{resource}", status_code=201, dependencies=[Depends(admin)])
def create_master(
    resource: str,
    values: dict,
    principal: Principal = Depends(admin),
    operator_id: str | None = Header(None, alias="X-Operator-ID"),
    source_id: str | None = Header(None, alias="X-Data-Source"),
):
    if resource not in RESOURCES:
        raise HTTPException(404, "Unknown resource")
    model, schema, _ = RESOURCES[resource]
    with Session(engine) as session, session.begin():
        try:
            if os.getenv("RTC_ALLOW_DEMO_DIRECT_WRITES") != "1" or not principal.root:
                return staged_write(
                    session,
                    resource,
                    values,
                    principal,
                    operator_id=operator_id,
                    source_id=source_id,
                )
            data = schema.model_validate(values).model_dump()
            validate_relations(session, model, data)
            row = model(**data)
            session.add(row)
            session.flush()
            return {"data": jsonable_encoder(row)}
        except (ValueError, IntegrityError) as exc:
            raise HTTPException(422, "Invalid or conflicting master data") from exc


@app.delete("/api/v1/admin/{resource}/{identifier}", dependencies=[Depends(admin)])
def deactivate_master(
    resource: str,
    identifier: str,
    principal: Principal = Depends(admin),
    operator_id: str | None = Header(None, alias="X-Operator-ID"),
    source_id: str | None = Header(None, alias="X-Data-Source"),
):
    if resource not in RESOURCES:
        raise HTTPException(404, "Unknown resource")
    with Session(engine) as session, session.begin():
        row = session.get(RESOURCES[resource][0], identifier)
        if not row:
            raise HTTPException(404, "Unknown record")
        if os.getenv("RTC_ALLOW_DEMO_DIRECT_WRITES") != "1" or not principal.root:
            return staged_write(
                session,
                resource,
                {},
                principal,
                identifier,
                "DEACTIVATE",
                operator_id,
                source_id,
            )
        row.active = False
        return {"data": {"id": identifier, "active": False}}


@app.put("/api/v1/admin/{resource}/{identifier}", dependencies=[Depends(admin)])
def update_master(
    resource: str,
    identifier: str,
    values: dict,
    principal: Principal = Depends(admin),
    operator_id: str | None = Header(None, alias="X-Operator-ID"),
    source_id: str | None = Header(None, alias="X-Data-Source"),
):
    if resource not in RESOURCES:
        raise HTTPException(404, "Unknown resource")
    model, schema, _ = RESOURCES[resource]
    with Session(engine) as session, session.begin():
        row = session.get(model, identifier)
        if row is None:
            raise HTTPException(404, "Unknown record")
        try:
            if os.getenv("RTC_ALLOW_DEMO_DIRECT_WRITES") != "1" or not principal.root:
                return staged_write(
                    session,
                    resource,
                    values,
                    principal,
                    identifier,
                    "UPDATE",
                    operator_id,
                    source_id,
                )
            data = schema.model_validate(values).model_dump()
            validate_relations(session, model, data)
            for key, value in data.items():
                setattr(row, key, value)
            session.flush()
            return {"data": jsonable_encoder(row)}
        except (ValueError, IntegrityError) as exc:
            raise HTTPException(422, "Invalid or conflicting master data") from exc


@app.get("/api/v1/stations/search")
def search_stations(
    q: str = Query(min_length=1, max_length=100), limit: int = Query(20, ge=1, le=100)
):
    from sqlalchemy import func

    from .domain import Alias

    with Session(engine) as session:
        aliases = select(Alias.station_id).where(
            func.lower(Alias.name).contains(q.casefold(), autoescape=True),
            Alias.active.is_(True),
        )
        rows = session.scalars(
            select(Station)
            .where(
                Station.active.is_(True),
                (func.lower(Station.name).contains(q.casefold(), autoescape=True))
                | (func.lower(Station.code).contains(q.casefold(), autoescape=True))
                | Station.id.in_(aliases),
            )
            .order_by(Station.name)
            .limit(limit)
        )
        return {"data": jsonable_encoder(list(rows))}


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": str(exc.status_code), "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request",
                "details": jsonable_encoder(
                    exc.errors(), custom_encoder={ValueError: str}
                ),
            }
        },
    )


from .engine import EnquiryRequest, EnquiryResponse, RTCEnquiryEngine
from .resolver import StationResolver


@app.post("/api/v1/enquiry", response_model=EnquiryResponse)
def unified_enquiry(request: EnquiryRequest):
    with Session(engine) as session:
        return RTCEnquiryEngine(session).enquire(request)


@app.get("/api/v1/stations/resolve")
def resolve_station(value: str = Query(min_length=1, max_length=250)):
    with Session(engine) as session:
        return {"data": StationResolver(session).resolve(value)}


from datetime import UTC
from pathlib import Path

from .nlp.muril import MuRILIntentClassifier
from .nlp.pipeline import NLPRequest, NLPResponse


@app.post("/api/v1/nlp/interpret", response_model=NLPResponse)
def interpret_text(
    request: NLPRequest, authorization: Annotated[str | None, Header()] = None
):
    if request.debug:
        admin(authorization)
    with Session(engine) as session:
        return EnglishInferenceService(session).interpret_query(
            request, datetime.now(UTC)
        )


@app.post("/api/v1/conversation/message", response_model=NLPResponse)
def conversation_message(
    request: NLPRequest, authorization: Annotated[str | None, Header()] = None
):
    if request.debug:
        admin(authorization)
    from fastapi.responses import JSONResponse
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with Session(engine) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            return EnglishInferenceService(session).process_conversation(
                request, datetime.now(UTC)
            )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "The local database is temporarily unavailable. Retry this enquiry; your saved context has not been discarded.",
                    "failure_group": "OPERATIONAL_ERROR",
                    "retryable": True,
                }
            },
        )


@app.post("/api/v1/conversation/reset")
def conversation_reset(request: NLPRequest):
    with Session(engine) as session, session.begin():
        return {
            "data": EnglishInferenceService(session).reset_session(
                request.session_id or "", request.owner_token
            )
        }


from .nlp.pipeline import ConversationRestoreRequest, ConversationStateResponse


@app.post("/api/v1/conversation/state", response_model=ConversationStateResponse)
def conversation_state(request: ConversationRestoreRequest):
    from .catalog import Context, Message
    from .nlp.session_access import check_owner, public_context

    with Session(engine) as session:
        context = session.scalar(
            select(Context).where(Context.session_id == request.session_id)
        )
        if not context:
            raise HTTPException(404, "Conversation is unavailable; start a new enquiry")
        check_owner(context.values, request.owner_token)
        if datetime.fromisoformat(
            context.values.get("expires_at", "1970-01-01T00:00:00+00:00")
        ) <= datetime.now(UTC):
            raise HTTPException(
                410, "Conversation expired; start a private new enquiry"
            )
        state = public_context(context.values)
        messages = list(
            session.scalars(
                select(Message)
                .where(
                    Message.session_id == request.session_id,
                    Message.role.in_(["user", "assistant"]),
                )
                .order_by(Message.sequence_number.desc(), Message.id.desc())
                .limit(40)
            )
        )
        return {
            "last_message_id": context.values.get("_last_message_id"),
            "data_source": __import__(
                "app.nlp.text_support", fromlist=["sources"]
            ).sources([], state),
            "session_id": request.session_id,
            "current_context": state,
            "selected_journey": state.get("selected_itinerary")
            or state.get("selected_result"),
            "result_set": state.get("candidates", []),
            "state_version": state.get("revision", 0),
            "history": [
                {
                    "id": m.id,
                    "role": m.role,
                    "text": m.text,
                    "sequence_number": m.sequence_number,
                }
                for m in reversed(messages)
            ],
        }


@app.get("/api/v1/nlp/status")
def nlp_status():
    return {
        "data": {
            "baseline": "READY",
            "muril": MuRILIntentClassifier(
                Path(__file__).resolve().parents[2]
            ).status(),
        }
    }


@app.get("/api/v1/models/status")
def models_status():
    import json

    registry = Path(__file__).resolve().parents[2] / "config/model_registry.yaml"
    models = (
        json.loads(registry.read_text(encoding="utf-8")).get("models", [])
        if registry.exists()
        else []
    )
    return {"data": {"nlp": nlp_status()["data"], "models": models}}


from sqlalchemy.exc import SQLAlchemyError


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Local enquiry data is temporarily unavailable.",
            }
        },
    )


@app.get("/api/v1/admin/{resource}", dependencies=[Depends(admin)])
def read_master(
    resource: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str = Query("", max_length=100),
    sort_by: str = "id",
    descending: bool = False,
    active: bool | None = None,
    operator_id: str | None = None,
    principal: Principal = Depends(admin),
):
    if resource not in RESOURCES:
        raise HTTPException(404, "Unknown resource")
    from .admin_listing import list_records

    model: Any = RESOURCES[resource][0]
    with Session(engine) as session:
        try:
            return list_records(
                session,
                model,
                limit,
                offset,
                q,
                sort_by,
                descending,
                active,
                read_scope(resource, model, principal, operator_id),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


from .nlp.taxonomy import IntentRegistry


@app.get("/api/v1/nlp/intents")
def list_intents(limit: int = Query(60, ge=1, le=60), offset: int = Query(0, ge=0)):
    with Session(engine) as session:
        return {
            "data": IntentRegistry(session).list(limit, offset),
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/v1/nlp/intents/{code}")
def intent_detail(code: str):
    with Session(engine) as session:
        definition = IntentRegistry(session).get(code)
        if definition is None:
            raise HTTPException(404, "Unknown enquiry intent")
        return {"data": definition}


@app.get("/api/v1/nlp/entities")
def list_entity_types():
    with Session(engine) as session:
        return {"data": IntentRegistry(session).entities()}


@app.get("/api/v1/nlp/health")
def nlp_health():
    from sqlalchemy import text

    from .nlp.english_model import EnglishIntentModel

    with Session(engine) as session:
        session.execute(text("SELECT 1"))
        model = EnglishIntentModel(Path(__file__).resolve().parents[2]).descriptor()
        return {
            "data": {
                "status": "DEGRADED" if model is None else "READY",
                "database": "READY",
                "deterministic_fallback": "READY",
                "statistical_model": "NOT_APPROVED" if model is None else "ACTIVE",
                "active_model_name": model.get("name") if model else None,
                "active_model_version": model.get("version") if model else None,
                "offline_certification": "OS_ISOLATION_UNVERIFIED",
            }
        }


from .nlp.session_access import SessionAccessError, check_owner, public_context


@app.exception_handler(SessionAccessError)
async def session_access_error(request, exc):
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "SESSION_ACCESS_DENIED",
                "message": "Session access denied.",
            }
        },
    )


@app.get("/api/v1/conversation/{session_id}/context")
def get_conversation_context(
    session_id: str, authorization: Annotated[str | None, Header()] = None
):
    from .catalog import Context

    with Session(engine) as session:
        row = session.scalar(select(Context).where(Context.session_id == session_id))
        if not row or not row.values.get("_owner_hash"):
            raise HTTPException(404, "Context unavailable")
        token = (authorization or "").removeprefix("Bearer ")
        check_owner(row.values, token)
        expiry = row.values.get("expires_at")
        if expiry and datetime.fromisoformat(expiry) <= datetime.now(UTC):
            raise HTTPException(410, "Session expired")
        return {"data": public_context(row.values)}


# Journey planning shares the existing database, timetable repository and filters.
from .journey import JourneyConstraints, JourneyPlanner, JourneyResults, RecoveryRequest


@app.post("/api/v1/journeys/search", response_model=JourneyResults)
def journey_search(request: JourneyConstraints):
    with Session(engine) as session:
        try:
            return JourneyPlanner(session).search(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/journeys/compare", response_model=JourneyResults)
def journey_compare(request: JourneyConstraints):
    # Recompute from local records rather than trusting submitted itinerary facts.
    return journey_search(request)


@app.post("/api/v1/journeys/replan", response_model=JourneyResults)
def journey_replan(request: JourneyConstraints):
    with Session(engine) as session:
        try:
            return JourneyPlanner(session).replan_journey(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/journeys/missed-bus", response_model=JourneyResults)
def journey_missed_bus(request: RecoveryRequest):
    with Session(engine) as session:
        try:
            return JourneyPlanner(session).find_alternatives_after_missed_bus(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


from .data_api import management_router
from .frontend_api import app_router

app.include_router(management_router(lambda: engine, admin))
from .operations_api import operations_router

app.include_router(operations_router(lambda: engine, admin))
app.include_router(app_router(lambda: engine, admin))

from .nlp.review_api import review_router

app.include_router(review_router(lambda: engine, admin))

from .runtime import health_router, install_maintenance

app.include_router(health_router(lambda: engine, admin))
install_maintenance(app, lambda: engine)
if os.getenv("RTC_TRUSTED_HOSTS"):
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=os.environ["RTC_TRUSTED_HOSTS"].split(",")
    )

# Serve compiled local assets in production; API errors must remain API errors.
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


class LocalAppFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace("\\", "/")
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Unknown API endpoint")
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in path.rsplit("/", 1)[-1]:
                return await super().get_response("index.html", scope)
            raise


_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount(
        "/", LocalAppFiles(directory=str(_frontend_dist), html=True), name="local-app"
    )


from .frontend_security import install_ui_security

install_ui_security(app)

from .diagnostics import install_diagnostics

install_diagnostics(app)
