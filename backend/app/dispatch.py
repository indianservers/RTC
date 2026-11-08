"""Validated dispatcher events over existing audit and operational projections."""

import copy
import hashlib
import json
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select

from .availability import utc
from .catalog import Calendar
from .domain import ExceptionDay, Route, Service, Station
from .operations import DataSource, PlatformAssignment, StationBay, Trip
from .records import Alert, Audit, DelayEvent, Disruption, ServiceStopTime, TripStopTime

ROLES = {
    "ADMIN",
    "OPERATIONS_VIEWER",
    "DISPATCHER",
    "STATION_SUPERVISOR",
    "OPERATOR_ADMIN",
}
SUPERVISORS = {"ADMIN", "STATION_SUPERVISOR", "OPERATOR_ADMIN"}
EVENTS = {
    "BOARDING",
    "READY",
    "ARRIVED_AT_STOP",
    "DEPARTED_FROM_STOP",
    "IN_TRANSIT",
    "COMPLETED",
    "DELAYED",
    "ETA",
    "PLATFORM",
    "CANCELLED",
    "SUSPENDED",
    "REINSTATE_REQUEST",
    "REINSTATE",
    "NOTICE_REQUEST",
    "PUBLISH_NOTICE",
    "ANNOUNCEMENT_REQUEST",
    "PUBLISH_ANNOUNCEMENT",
    "CORRECTION",
}


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: str
    station_id: str
    source_id: str
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=120)
    occurred_at: AwareDatetime
    expires_at: AwareDatetime
    reason: str = Field(min_length=5, max_length=1000)
    details: dict = Field(default_factory=dict)


def scope(principal, operator, station, write=False, supervisor=False):
    if principal.role not in ROLES or write and principal.role == "OPERATIONS_VIEWER":
        raise HTTPException(403, "Operations role required")
    if supervisor and principal.role not in SUPERVISORS:
        raise HTTPException(403, "Station supervisor approval required")
    if not principal.root and not any(
        op == operator
        and (stand is None and principal.role == "OPERATOR_ADMIN" or stand == station)
        for op, stand in principal.station_grants
    ):
        raise HTTPException(403, "Operator/station is outside this capability")


def stops_for(session, service, day):
    from .enquiry import Enquiry

    return Enquiry(session).get_route_stops(service.id, day)


def schedule(session, service, day, station_id):
    station = session.get(Station, station_id)
    if not station or not station.active:
        raise HTTPException(422, "Unknown or inactive station")
    stops = stops_for(session, service, day)
    stop = next((r for r in stops if r.station_id == station_id), None)
    if not stop:
        raise HTTPException(422, "Station is not an active stop of this dated service")
    override = session.scalar(
        select(ExceptionDay).where(
            ExceptionDay.service_id == service.id,
            ExceptionDay.service_date == day,
            ExceptionDay.active.is_(True),
        )
    )
    calendar = session.scalar(
        select(Calendar)
        .where(
            Calendar.service_id == service.id,
            Calendar.active.is_(True),
            Calendar.valid_from <= day,
            Calendar.valid_to >= day,
        )
        .order_by(Calendar.valid_from.desc())
    )
    if (
        not service.active
        or not service.valid_from <= day <= service.valid_to
        or (
            not override.operates
            if override
            else str(day.weekday())
            not in (calendar.weekdays if calendar else service.weekdays)
        )
    ):
        raise HTTPException(422, "Service does not operate on this date")
    offset = session.scalar(
        select(ServiceStopTime).where(
            ServiceStopTime.service_id == service.id,
            ServiceStopTime.stop_id == stop.id,
            ServiceStopTime.active.is_(True),
        )
    )
    first = stops[0]
    first_station = session.get(Station, first.station_id)
    minutes = (override.details or {}).get("departure_minutes") if override else None
    base = datetime.combine(
        day, time.min, ZoneInfo(first_station.timezone)
    ) + timedelta(
        minutes=minutes
        if minutes is not None
        else calendar.departure_minutes
        if calendar
        else service.departure_minutes
    )
    trip = session.scalar(
        select(Trip).where(
            Trip.service_id == service.id,
            Trip.service_date == day,
            Trip.active.is_(True),
        )
    )
    if trip and trip.planned_departure_at:
        base = utc(trip.planned_departure_at)
    arrival = (
        offset.arrival_offset
        if offset
        else stop.arrival_offset_minutes
        if stop.arrival_offset_minutes is not None
        else stop.offset_minutes
    )
    departure = (
        offset.departure_offset
        if offset
        else stop.departure_offset_minutes
        if stop.departure_offset_minutes is not None
        else stop.offset_minutes
    )
    return (
        stop,
        stops,
        base + timedelta(minutes=arrival),
        base + timedelta(minutes=departure),
    )


def fingerprint(body):
    return hashlib.sha256(
        json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()


class TripOperationalStateMachine:
    """Lifecycle, movement at each stop, and delay are orthogonal dimensions."""

    @staticmethod
    def apply(state, kind, station, occurred, details, stop_order):
        result = copy.deepcopy(state)
        lifecycle = result.setdefault("lifecycle", "ACTIVE")
        result.setdefault("phase", "SCHEDULED")
        current = result.setdefault("stops", {}).setdefault(
            station, {"phase": "SCHEDULED"}
        )
        last = result.get("last_movement_at")
        if kind in {
            "BOARDING",
            "READY",
            "ARRIVED_AT_STOP",
            "DEPARTED_FROM_STOP",
            "IN_TRANSIT",
            "COMPLETED",
        }:
            if lifecycle != "ACTIVE" or result["phase"] == "COMPLETED":
                raise HTTPException(
                    409,
                    "Inactive/completed trip requires authorized reinstatement/correction",
                )
            if last and utc(datetime.fromisoformat(last)) > occurred:
                raise HTTPException(
                    409, "Out-of-order movement; submit an authorized correction"
                )
            previous_index = result.get("last_stop_index", -1)
            if stop_order < previous_index:
                raise HTTPException(409, "Stop event goes backwards along the route")
            if kind == "ARRIVED_AT_STOP" and current["phase"] in {
                "ARRIVED_AT_STOP",
                "BOARDING",
                "READY",
                "DEPARTED_FROM_STOP",
            }:
                raise HTTPException(409, "Arrival contradicts recorded stop phase")
            if (
                kind in {"BOARDING", "READY"}
                and current["phase"] == "DEPARTED_FROM_STOP"
            ):
                raise HTTPException(409, "Cannot board a departed stop")
            if kind == "READY" and current["phase"] not in {"BOARDING", "READY"}:
                raise HTTPException(409, "Start boarding before marking ready")
            if (
                kind == "DEPARTED_FROM_STOP"
                and current["phase"] == "DEPARTED_FROM_STOP"
            ):
                raise HTTPException(409, "Already departed this stop")
            if kind == "IN_TRANSIT" and result["phase"] != "DEPARTED_FROM_STOP":
                raise HTTPException(
                    409, "Record actual departure before in-transit status"
                )
            if kind == "COMPLETED" and not details.get("at_destination"):
                raise HTTPException(409, "Completion requires destination arrival")
            current["phase"] = kind
            if kind == "ARRIVED_AT_STOP":
                current["actual_arrival"] = occurred.isoformat()
            if kind == "DEPARTED_FROM_STOP":
                if (
                    current.get("actual_arrival")
                    and datetime.fromisoformat(current["actual_arrival"]) > occurred
                ):
                    raise HTTPException(409, "Departure precedes recorded arrival")
                current["actual_departure"] = occurred.isoformat()
            result.update(
                phase=kind,
                last_stop_index=stop_order,
                last_movement_at=occurred.isoformat(),
            )
        elif kind in {"CANCELLED", "SUSPENDED"}:
            if result["phase"] in {"DEPARTED_FROM_STOP", "IN_TRANSIT", "COMPLETED"}:
                raise HTTPException(
                    409,
                    "An already departed trip cannot be cancelled; use an approved disruption",
                )
            result["lifecycle"] = kind
        elif kind in {"DELAYED", "ETA"}:
            if lifecycle != "ACTIVE" or current["phase"] == "DEPARTED_FROM_STOP":
                raise HTTPException(
                    409, "Cannot revise departure of an inactive/departed stop"
                )
            current["delay_reason"] = details["reason"]
        return result


def apply_event(session, trip, body, principal):
    service = session.get(Service, trip.service_id)
    scope(principal, service.operator_id, body.station_id, write=True)
    old_event = session.scalar(
        select(Audit).where(Audit.idempotency_key == body.idempotency_key)
    )
    if old_event:
        if (
            old_event.entity_id != trip.id
            or old_event.actor != principal.username
            or (old_event.new_values or {}).get("request_hash") != fingerprint(body)
        ):
            raise HTTPException(
                409, "Idempotency key was used for a different operation"
            )
        return old_event
    if trip.operational_version != body.expected_version:
        raise HTTPException(409, "Trip version changed; refresh authoritative state")
    kind = body.event_type
    if kind not in EVENTS:
        raise HTTPException(422, "Unsupported operational event type")
    now = datetime.now(UTC)
    occurred, expiry = utc(body.occurred_at), utc(body.expires_at)
    if (
        occurred > now + timedelta(seconds=30)
        or expiry <= occurred
        or expiry > now + timedelta(days=8)
    ):
        raise HTTPException(
            422, "Event time must be observed, with an explicit bounded expiry"
        )
    source = session.get(DataSource, body.source_id)
    if (
        not source
        or not source.active
        or source.operator_id not in {None, service.operator_id}
    ):
        raise HTTPException(422, "Missing active operator-compatible source provenance")
    demo = (
        "DEMO" in trip.dataset_source.upper()
        or "SYNTHETIC" in trip.dataset_source.upper()
    )
    if source.is_demo and not demo:
        raise HTTPException(422, "DEMO observations require a labelled DEMO trip")
    if demo and source.is_official and not source.is_demo:
        raise HTTPException(422, "DEMO trips cannot become official through an event")
    dataset = (
        "DEMO"
        if demo or source.is_demo
        else "VERIFIED_LOCAL_OPERATOR"
        if source.is_official
        else "LOCAL_DISPATCHER"
    )
    stop, stops, _scheduled_arrival, scheduled_departure = schedule(
        session, service, trip.service_date, body.station_id
    )
    before = copy.deepcopy(trip.operational_state or {})
    if not before and trip.status in {"running", "completed", "cancelled"}:
        before = {
            "lifecycle": "CANCELLED" if trip.status == "cancelled" else "ACTIVE",
            "phase": "COMPLETED"
            if trip.status == "completed"
            else "IN_TRANSIT"
            if trip.status == "running"
            else "SCHEDULED",
        }
    if (
        body.event_type != "CORRECTION"
        and before.get("last_event_time")
        and occurred < datetime.fromisoformat(before["last_event_time"])
    ):
        raise HTTPException(
            409, "Out-of-order event; refresh and submit an authorized correction"
        )
    if (
        not scheduled_departure - timedelta(days=1)
        <= occurred
        <= scheduled_departure + timedelta(days=7)
    ):
        raise HTTPException(
            422, "Occurred time is outside this dated trip's operational window"
        )
    details = dict(body.details)
    allowed = {
        "bay_id",
        "estimated_arrival",
        "estimated_departure",
        "delay_minutes",
        "target_event_id",
        "corrected_event_type",
        "affected_station_ids",
        "affected_service_ids",
        "affected_route_ids",
        "affected_trip_ids",
        "disruption_type",
        "severity",
        "description",
        "starts_at",
        "ends_at",
    }
    if set(details) - allowed:
        raise HTTPException(422, "Unsupported event detail field")
    details["reason"] = body.reason
    index = next(i for i, r in enumerate(stops) if r.id == stop.id)
    details["at_destination"] = (
        index == len(stops) - 1
        and before.get("stops", {}).get(body.station_id, {}).get("actual_arrival")
        is not None
    )
    if kind == "CORRECTION":
        scope(
            principal, service.operator_id, body.station_id, write=True, supervisor=True
        )
        target = session.get(Audit, details.get("target_event_id"))
        if (
            not target
            or target.entity_id != trip.id
            or target.station_id != body.station_id
            or target.version != trip.operational_version
        ):
            raise HTTPException(
                409, "Correction must reference the latest trip event at this station"
            )
        kind = details.get("corrected_event_type")
        if kind not in {
            "ARRIVED_AT_STOP",
            "DEPARTED_FROM_STOP",
            "BOARDING",
            "READY",
            "ETA",
            "DELAYED",
            "PLATFORM",
        }:
            raise HTTPException(
                422, "Unsupported correction; reinstate cancellations through approval"
            )
        before_for_apply = copy.deepcopy(target.previous_values or {})
        old_projection = target.new_values or {}
        for model in (TripStopTime, DelayEvent, PlatformAssignment):
            for identifier in old_projection.get("projection_ids", {}).get(
                model.__tablename__, []
            ):
                record = session.get(model, identifier)
                if record:
                    record.active = False
    else:
        before_for_apply = before
    if kind in {"DELAYED", "ETA"}:
        for key in ("estimated_arrival", "estimated_departure"):
            if key in details:
                try:
                    value = datetime.fromisoformat(details[key])
                    if value.tzinfo is None:
                        raise ValueError()
                    details[key] = utc(value).isoformat()
                except (ValueError, TypeError) as exc:
                    raise HTTPException(
                        422, "ETA must be a timezone-aware datetime"
                    ) from exc
                if utc(value) < occurred or utc(
                    value
                ) > scheduled_departure + timedelta(days=2):
                    raise HTTPException(
                        422, "ETA is outside the valid trip observation window"
                    )
        minutes = details.get("delay_minutes")
        if minutes is not None and (
            not isinstance(minutes, int)
            or isinstance(minutes, bool)
            or not 0 <= minutes <= 2880
        ):
            raise HTTPException(422, "Delay must be between 0 and 2880 minutes")
        if "estimated_departure" not in details and minutes is not None:
            details["estimated_departure"] = (
                scheduled_departure + timedelta(minutes=minutes)
            ).isoformat()
        if not any(k in details for k in ("estimated_arrival", "estimated_departure")):
            raise HTTPException(
                422, "Enter a revised arrival/departure estimate or delay minutes"
            )
        if details.get("estimated_departure"):
            computed = max(
                0,
                int(
                    (
                        datetime.fromisoformat(details["estimated_departure"])
                        - scheduled_departure
                    ).total_seconds()
                    // 60
                ),
            )
            if minutes is not None and abs(computed - minutes) > 1:
                raise HTTPException(
                    422, "Delay minutes conflict with revised departure"
                )
            details["delay_minutes"] = computed
    state = TripOperationalStateMachine.apply(
        before_for_apply, kind, body.station_id, occurred, details, index
    )
    common = {
        "trip_id": trip.id,
        "source_id": body.source_id,
        "effective_at": occurred,
        "expires_at": expiry,
        "verified": True,
        "dataset_source": dataset,
    }
    projections = {}

    def add(record):
        session.add(record)
        session.flush()
        projections.setdefault(record.__tablename__, []).append(record.id)

    if kind in {"ARRIVED_AT_STOP", "DEPARTED_FROM_STOP", "ETA", "DELAYED"}:
        current = state["stops"][body.station_id]
        previous = session.scalar(
            select(TripStopTime)
            .where(
                TripStopTime.trip_id == trip.id,
                TripStopTime.stop_id == stop.id,
                TripStopTime.active.is_(True),
                TripStopTime.verified.is_(True),
            )
            .order_by(TripStopTime.effective_at.desc(), TripStopTime.id)
        )
        values = {
            k: getattr(previous, k) if previous else None
            for k in (
                "actual_arrival",
                "actual_departure",
                "estimated_arrival",
                "estimated_departure",
            )
        }
        if previous and utc(previous.expires_at) <= occurred:
            for key in ("estimated_arrival", "estimated_departure"):
                values[key] = None
                current.pop(key, None)
            current.pop("delay_minutes", None)
        for key in values:
            if current.get(key):
                values[key] = datetime.fromisoformat(current[key])
            if key in details:
                values[key] = datetime.fromisoformat(details[key])
        if (
            values["actual_arrival"]
            and values["actual_departure"]
            and utc(values["actual_departure"]) < utc(values["actual_arrival"])
        ):
            raise HTTPException(409, "Actual departure precedes actual arrival")
        if (
            values["estimated_arrival"]
            and values["estimated_departure"]
            and utc(values["estimated_departure"]) < utc(values["estimated_arrival"])
        ):
            raise HTTPException(422, "Estimated departure precedes estimated arrival")
        for key, value in values.items():
            if value:
                current[key] = utc(value).isoformat()
        current["expires_at"] = expiry.isoformat()
        add(TripStopTime(stop_id=stop.id, **values, **common))
        if kind in {"ETA", "DELAYED"} and "delay_minutes" in details:
            current["delay_minutes"] = details["delay_minutes"]
            add(
                DelayEvent(
                    station_id=body.station_id,
                    delay_minutes=details["delay_minutes"],
                    **common,
                )
            )
    if kind == "PLATFORM" or kind == "BOARDING" and details.get("bay_id"):
        bay = session.get(StationBay, details.get("bay_id"))
        if not bay or not bay.active or bay.station_id != body.station_id:
            raise HTTPException(422, "Platform is not an active bay of this station")
        conflicts = session.scalars(
            select(PlatformAssignment).where(
                PlatformAssignment.bay_id == bay.id,
                PlatformAssignment.trip_id != trip.id,
                PlatformAssignment.active.is_(True),
                PlatformAssignment.effective_at < expiry,
                PlatformAssignment.expires_at > occurred,
            )
        )
        if any(r.verified for r in conflicts):
            raise HTTPException(409, "Platform has an overlapping confirmed assignment")
        for old in session.scalars(
            select(PlatformAssignment)
            .join(StationBay)
            .where(
                PlatformAssignment.trip_id == trip.id,
                StationBay.station_id == body.station_id,
                PlatformAssignment.active.is_(True),
            )
        ):
            if utc(old.effective_at) > occurred:
                raise HTTPException(
                    409, "Out-of-order platform change requires correction"
                )
            old.active = False
        assignment_kind = (
            "ACTUAL_BOARDING" if kind == "BOARDING" else "DISPATCHER_CONFIRMED"
        )
        add(
            PlatformAssignment(bay_id=bay.id, assignment_kind=assignment_kind, **common)
        )
        state["stops"][body.station_id]["platform"] = {
            "bay": bay.code,
            "bay_id": bay.id,
            "kind": assignment_kind,
            "expires_at": expiry.isoformat(),
        }
    if kind in {"CANCELLED", "SUSPENDED"}:
        trip.status = "cancelled"  # Existing planner cancellation projection; lifecycle distinguishes suspension.
        state["cancellation"] = {
            "reason": body.reason,
            "affected_station_ids": [s.station_id for s in stops],
            "occurred_at": occurred.isoformat(),
        }
    if kind == "REINSTATE_REQUEST":
        if (
            before.get("lifecycle") not in {"CANCELLED", "SUSPENDED"}
            and trip.status != "cancelled"
        ):
            raise HTTPException(409, "Only cancelled/suspended trips can be reinstated")
        state["reinstatement"] = {
            "requested_by": principal.username,
            "version": trip.operational_version + 1,
        }
    if kind == "REINSTATE":
        scope(principal, service.operator_id, body.station_id, True, True)
        request = before.get("reinstatement")
        if not request or request["requested_by"] == principal.username:
            raise HTTPException(
                403, "A different supervisor must approve a reinstatement request"
            )
        # Revalidate all timed platform conflicts before restoring availability.
        for assignment in session.scalars(
            select(PlatformAssignment).where(
                PlatformAssignment.trip_id == trip.id,
                PlatformAssignment.active.is_(True),
                PlatformAssignment.expires_at > now,
            )
        ):
            if session.scalar(
                select(PlatformAssignment.id).where(
                    PlatformAssignment.bay_id == assignment.bay_id,
                    PlatformAssignment.trip_id != trip.id,
                    PlatformAssignment.active.is_(True),
                    PlatformAssignment.verified.is_(True),
                    PlatformAssignment.effective_at < assignment.expires_at,
                    PlatformAssignment.expires_at > assignment.effective_at,
                )
            ):
                raise HTTPException(
                    409, "Resolve platform conflicts before reinstatement"
                )
        state.update(lifecycle="ACTIVE", phase="SCHEDULED")
        state.pop("reinstatement", None)
        trip.status = "scheduled"
    if kind in {"DEPARTED_FROM_STOP", "IN_TRANSIT"}:
        trip.status = "running"
    if kind == "COMPLETED":
        trip.status = "completed"
    if kind.endswith("_REQUEST") and kind != "REINSTATE_REQUEST":
        state.setdefault("pending", {})[body.idempotency_key] = {
            "actor": principal.username,
            "kind": kind,
            "details": details,
            "source_id": body.source_id,
            "station_id": body.station_id,
            "expires_at": expiry.isoformat(),
        }
        if kind == "ANNOUNCEMENT_REQUEST":
            state["pending"][body.idempotency_key]["preview"] = announcement(
                session, trip, body.station_id, now
            )
    if kind in {"PUBLISH_NOTICE", "PUBLISH_ANNOUNCEMENT"}:
        scope(principal, service.operator_id, body.station_id, True, True)
        pending = state.get("pending", {}).get(details.get("target_event_id"))
        expected_kind = (
            "NOTICE_REQUEST" if kind == "PUBLISH_NOTICE" else "ANNOUNCEMENT_REQUEST"
        )
        if (
            not pending
            or pending["kind"] != expected_kind
            or pending["actor"] == principal.username
            or pending["station_id"] != body.station_id
            or datetime.fromisoformat(pending["expires_at"]) <= now
        ):
            raise HTTPException(
                403, "Different supervisor must approve a current scoped request"
            )
        pending_source = session.get(DataSource, pending["source_id"])
        if (
            not pending_source
            or not pending_source.active
            or pending_source.operator_id not in {None, service.operator_id}
        ):
            raise HTTPException(
                409, "Requested provenance changed; submit a newly verified request"
            )
        if kind == "PUBLISH_NOTICE":
            content = pending["details"]
            try:
                starts = (
                    datetime.fromisoformat(content["starts_at"])
                    if content.get("starts_at")
                    else occurred
                )
                ends = (
                    datetime.fromisoformat(content["ends_at"])
                    if content.get("ends_at")
                    else expiry
                )
                if (
                    starts.tzinfo is None
                    or ends.tzinfo is None
                    or ends <= starts
                    or ends > now + timedelta(days=8)
                ):
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    422, "Disruption requires ordered timezone-aware start/end times"
                ) from exc
            affected = set(content.get("affected_service_ids", [])) | {service.id}
            for route_id in content.get("affected_route_ids", []):
                route = session.get(Route, route_id)
                if not route or route.operator_id != service.operator_id:
                    raise HTTPException(422, "Invalid affected route")
                affected.update(
                    session.scalars(
                        select(Service.id).where(
                            Service.route_id == route_id, Service.active.is_(True)
                        )
                    )
                )
            for trip_id in content.get("affected_trip_ids", []):
                affected_trip = session.get(Trip, trip_id)
                if not affected_trip:
                    raise HTTPException(422, "Invalid affected trip")
                affected.add(affected_trip.service_id)
            affected_stations = content.get("affected_station_ids", [body.station_id])
            for sid in affected_stations:
                scope(principal, service.operator_id, sid, True, True)
                if not session.get(Station, sid):
                    raise HTTPException(422, "Unknown affected station")
            if not content.get("description") or len(content["description"]) > 2000:
                raise HTTPException(422, "Disruption requires a bounded description")
            if content.get("severity") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise HTTPException(422, "Choose disruption severity")
            if content.get("disruption_type") not in {
                "ROAD_CLOSURE",
                "ROUTE_DIVERSION",
                "STATION_CLOSURE",
                "STOP_SUSPENSION",
                "FESTIVAL_CROWD",
                "WEATHER_SUSPENSION",
                "SERVICE_INTERRUPTION",
                "OTHER",
            }:
                raise HTTPException(422, "Choose a supported disruption type")
            for sid in affected:
                affected_service = session.get(Service, sid)
                if (
                    not affected_service
                    or affected_service.operator_id != service.operator_id
                ):
                    raise HTTPException(422, "Invalid affected operator service")
                session.add(
                    Disruption(
                        service_id=sid,
                        description=content["description"],
                        disruption_type=content["disruption_type"],
                        severity=content["severity"],
                        details={**content, "affected_station_ids": affected_stations},
                        approved_by=principal.username,
                        source_id=pending["source_id"],
                        effective_at=starts,
                        expires_at=ends,
                        verified=True,
                        dataset_source=dataset,
                    )
                )
        else:
            text = announcement(session, trip, body.station_id, now)
            if text != pending.get("preview"):
                raise HTTPException(
                    409, "Announcement facts changed; request review of a new preview"
                )
            session.add(
                Alert(
                    trip_id=trip.id,
                    station_id=body.station_id,
                    message=text,
                    **{k: v for k, v in common.items() if k != "trip_id"},
                )
            )
            state["last_announcement"] = text
        del state["pending"][details["target_event_id"]]
    if "REQUEST" not in kind and not kind.startswith("PUBLISH_"):
        state["last_operation"] = kind
    state["last_update"] = now.isoformat()
    state["last_event_time"] = occurred.isoformat()
    state["dataset_source"] = dataset
    trip.operational_state = state
    trip.operational_version += 1
    event = Audit(
        actor=principal.username,
        entity_type="operations",
        entity_id=trip.id,
        operator_id=service.operator_id,
        station_id=body.station_id,
        source_id=body.source_id,
        occurred_at=occurred,
        recorded_at=now,
        operation=body.event_type,
        version=trip.operational_version,
        previous_values=before,
        new_values={
            "state": state,
            "request_hash": fingerprint(body),
            "details": details,
            "projection_ids": projections,
        },
        changed_fields=[kind],
        reason=body.reason,
        idempotency_key=body.idempotency_key,
        dataset_source=dataset,
    )
    session.add(event)
    session.flush()
    return event


def announcement(session, trip, station_id, at):
    """Text uses locally configured templates and only current verified projections."""
    from pathlib import Path

    templates = json.loads(
        (
            Path(__file__).resolve().parents[2] / "config/operations_announcements.json"
        ).read_text(encoding="utf-8")
    )
    service = session.get(Service, trip.service_id)
    state = trip.operational_state or {}
    stop = state.get("stops", {}).get(station_id, {})
    lifecycle = state.get("lifecycle", "ACTIVE")
    if lifecycle in {"CANCELLED", "SUSPENDED"}:
        return templates["cancelled"].format(service_number=service.number)
    if state.get("last_operation") == "REINSTATE":
        return templates["reinstated"].format(service_number=service.number)
    platform = stop.get("platform")
    if (
        state.get("last_operation") == "PLATFORM"
        and platform
        and at < datetime.fromisoformat(platform["expires_at"])
    ):
        return templates["platform"].format(
            service_number=service.number, platform=platform["bay"]
        )
    phase = stop.get("phase", "SCHEDULED")
    if phase == "DEPARTED_FROM_STOP":
        return templates["departed"].format(service_number=service.number)
    if phase == "ARRIVED_AT_STOP":
        return templates["arrived"].format(service_number=service.number)
    if phase == "BOARDING":
        return templates["boarding"].format(service_number=service.number)
    if (
        stop.get("estimated_departure")
        and stop.get("expires_at")
        and at < datetime.fromisoformat(stop["expires_at"])
    ):
        return templates["delayed"].format(
            service_number=service.number, estimated_time=stop["estimated_departure"]
        )
    platform = stop.get("platform")
    if platform and at < datetime.fromisoformat(platform["expires_at"]):
        return templates["platform"].format(
            service_number=service.number, platform=platform["bay"]
        )
    return templates["unknown"].format(service_number=service.number)
