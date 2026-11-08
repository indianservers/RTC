"""Read-only SQL audits over local records; no metrics are synthesized."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import aliased

from .catalog import Calendar, ImportBatch
from .domain import Alias, Category, Fare, Route, Service, Station, Stop
from .operations import PlatformAssignment, Trip
from .records import (
    DelayEvent,
    FareRule,
    Location,
    QualityIssue,
    ServiceStopTime,
    TripStopTime,
)


def quality_report(
    session,
    at: datetime,
    day: date,
    kind=None,
    severity=None,
    limit=25,
    offset=0,
    principal=None,
    operator_id=None,
):
    checks = []

    def add(code, level, model, condition, resource, correction, label):
        query = select(model.id).where(model.active.is_(True), condition)
        if principal is not None:
            from .data_access import read_scope

            query = query.where(read_scope(resource, model, principal, operator_id))
        checks.append((code, level, query, resource, correction, label))

    add(
        "MISSING_STATION_ALIAS",
        "WARNING",
        Station,
        ~exists(
            select(Alias.id).where(
                Alias.station_id == Station.id, Alias.active.is_(True)
            )
        ),
        "stations",
        "Review station aliases in the local master data.",
        "Station has no active aliases",
    )
    other_station = aliased(Station)
    add(
        "POSSIBLE_DUPLICATE_STATION",
        "WARNING",
        Station,
        exists(
            select(other_station.id).where(
                other_station.active.is_(True),
                other_station.id != Station.id,
                func.lower(func.trim(other_station.name))
                == func.lower(func.trim(Station.name)),
                or_(
                    other_station.city_id == Station.city_id,
                    and_(other_station.city_id.is_(None), Station.city_id.is_(None)),
                ),
            )
        ),
        "stations",
        "Review matching names and city before merging; distinct stations can share names.",
        "Possible duplicate station name within city",
    )
    earlier = aliased(Stop)
    later = aliased(Stop)
    add(
        "INVALID_ROUTE_SEQUENCE",
        "ERROR",
        Route,
        exists(
            select(earlier.id)
            .join(later, later.route_id == earlier.route_id)
            .where(
                earlier.route_id == Route.id,
                earlier.active.is_(True),
                later.active.is_(True),
                earlier.sequence < later.sequence,
                or_(
                    earlier.offset_minutes > later.offset_minutes,
                    earlier.distance_km > later.distance_km,
                ),
            )
        ),
        "routes",
        "Correct decreasing scheduled offsets or distances while preserving stop order.",
        "Route offsets or distances decrease along stop sequence",
    )
    category = aliased(Category)
    add(
        "INCONSISTENT_SERVICE_CATEGORY",
        "ERROR",
        Service,
        ~exists(
            select(category.id).where(
                category.id == Service.category_id,
                category.active.is_(True),
                category.operator_id == Service.operator_id,
            )
        ),
        "schedules",
        "Use an active bus category belonging to this service operator.",
        "Service references inactive or mismatched operator category",
    )
    stop_count = (
        select(func.count(Stop.id))
        .where(Stop.route_id == Route.id, Stop.active.is_(True))
        .scalar_subquery()
    )
    add(
        "MISSING_ROUTE_STOPS",
        "ERROR",
        Route,
        stop_count < 2,
        "routes",
        "Add at least two ordered route stops with permissions.",
        "Route has fewer than two active stops",
    )
    valid_calendar = exists(
        select(Calendar.id).where(
            Calendar.service_id == Service.id,
            Calendar.active.is_(True),
            Calendar.valid_from <= day,
            Calendar.valid_to >= day,
        )
    )
    base_valid = and_(
        Service.valid_from <= day, Service.valid_to >= day, Service.weekdays != ""
    )
    add(
        "NO_CURRENT_CALENDAR",
        "WARNING",
        Service,
        ~valid_calendar & ~base_valid,
        "schedules",
        "Check validity dates and recurring calendar. A seasonal or future service may be intentional.",
        "No calendar window covers audit date",
    )
    scheduled_exists = exists(
        select(ServiceStopTime.id).where(
            ServiceStopTime.service_id == Service.id, ServiceStopTime.active.is_(True)
        )
    )
    route_offsets = exists(
        select(Stop.id).where(
            Stop.route_id == Service.route_id,
            Stop.active.is_(True),
            Stop.offset_minutes >= 0,
        )
    )
    service_schedule = exists(
        select(Service.id).where(
            Service.id == Trip.service_id,
            Service.active.is_(True),
            or_(scheduled_exists, route_offsets),
        )
    )
    add(
        "MISSING_TRIP_SCHEDULE",
        "ERROR",
        Trip,
        ~service_schedule,
        "trips",
        "Supply service stop times or validated recurring route-stop offsets.",
        "Trip has no locally derivable scheduled stop times",
    )
    valid_fare = exists(
        select(Fare.id).where(
            Fare.service_id == Service.id,
            Fare.active.is_(True),
            Fare.valid_from <= day,
            Fare.valid_to >= day,
        )
    )
    add(
        "MISSING_VALID_FARE",
        "WARNING",
        Service,
        ~valid_fare,
        "schedules",
        "Review missing dated segment tariffs; do not substitute zero.",
        "Service has no valid segment fare on audit date",
    )
    add(
        "EXPIRED_SEGMENT_TARIFF",
        "WARNING",
        Fare,
        Fare.valid_to < day,
        "fares",
        "Review validity and replace expired tariff if the service still operates.",
        "Segment tariff has expired",
    )
    duplicate = aliased(Service)
    add(
        "DUPLICATE_SERVICE_NUMBER",
        "ERROR",
        Service,
        exists(
            select(duplicate.id).where(
                duplicate.active.is_(True),
                duplicate.operator_id == Service.operator_id,
                duplicate.number == Service.number,
                duplicate.id != Service.id,
            )
        ),
        "schedules",
        "Resolve duplicate numbers within the same operator; cross-operator reuse is allowed.",
        "Service number duplicated within operator",
    )
    platform = exists(
        select(PlatformAssignment.id).where(
            PlatformAssignment.trip_id == Trip.id,
            PlatformAssignment.active.is_(True),
            PlatformAssignment.verified.is_(True),
            PlatformAssignment.effective_at <= at,
            PlatformAssignment.expires_at > at,
        )
    )
    add(
        "PLATFORM_UNCONFIRMED",
        "INFO",
        Trip,
        and_(
            Trip.service_date == day,
            Trip.status.not_in(["cancelled", "completed"]),
            ~platform,
        ),
        "trips",
        "Verify and record a fresh platform assignment. Absence is not proof no platform exists.",
        "No current verified platform assignment",
    )
    operational_models: list[Any] = [
        TripStopTime,
        DelayEvent,
        Location,
        PlatformAssignment,
    ]
    for model in operational_models:
        newer = aliased(model)
        match = [
            newer.trip_id == model.trip_id,
            newer.active.is_(True),
            newer.verified.is_(True),
            newer.effective_at <= at,
            newer.effective_at > model.effective_at,
        ]
        if hasattr(model, "stop_id"):
            match.append(newer.stop_id == model.stop_id)
        if hasattr(model, "station_id"):
            match.append(newer.station_id == model.station_id)
        add(
            "STALE_" + model.__tablename__.upper(),
            "WARNING",
            model,
            and_(
                exists(
                    select(Trip.id).where(
                        Trip.id == model.trip_id,
                        Trip.active.is_(True),
                        Trip.service_date == day,
                        Trip.status.not_in(["cancelled", "completed"]),
                    )
                ),
                model.verified.is_(True),
                model.effective_at <= at,
                model.expires_at <= at,
                ~exists(select(newer.id).where(*match)),
            ),
            {
                TripStopTime: "stop-observations",
                DelayEvent: "delay-events",
                Location: "location-updates",
                PlatformAssignment: "platform-assignments",
            }[model],
            "Obtain a new verified operational update; retain scheduled/unknown status until then.",
            "Latest applicable operational record is stale",
        )
    add(
        "RECORDED_IMPORT_ISSUE",
        "ERROR",
        QualityIssue,
        and_(QualityIssue.resolved.is_(False), QualityIssue.batch_id.is_not(None)),
        "import-batches",
        "Inspect the recorded issue and original CSV import report.",
        "Unresolved recorded import issue",
    )
    add(
        "EXPIRED_FARE_RULE",
        "WARNING",
        FareRule,
        FareRule.valid_to < day,
        "fare-rules",
        "Review rule validity and publish a replacement without overlapping dates.",
        "Dated fare rule has expired",
    )
    add(
        "UNDATED_FARE_RULE",
        "WARNING",
        FareRule,
        or_(FareRule.valid_from.is_(None), FareRule.valid_to.is_(None)),
        "fare-rules",
        "Review legacy rule and supply effective dates before further publication.",
        "Legacy fare rule lacks effective dates",
    )
    add(
        "FAILED_STAGED_IMPORT",
        "ERROR",
        ImportBatch,
        ImportBatch.validation_error_count > 0,
        "imports",
        "Open this change set and correct the reported rows before validating again.",
        "Stored change set has unresolved validation errors",
    )
    other_calendar = aliased(Calendar)
    add(
        "CONFLICTING_CALENDAR",
        "ERROR",
        Calendar,
        exists(
            select(other_calendar.id).where(
                other_calendar.service_id == Calendar.service_id,
                other_calendar.id != Calendar.id,
                other_calendar.active.is_(True),
                other_calendar.valid_from <= Calendar.valid_to,
                other_calendar.valid_to >= Calendar.valid_from,
            )
        ),
        "calendars",
        "Resolve overlapping active calendar windows and publish a validated replacement.",
        "Active service calendar windows overlap",
    )
    counts = []
    issues: list[dict] = []
    total = 0
    remaining_offset = offset
    for code, level, query, resource, correction, label in checks:
        count = session.scalar(select(func.count()).select_from(query.subquery())) or 0
        counts.append(
            {
                "code": code,
                "severity": level,
                "enterprise_severity": {
                    "ERROR": "HIGH",
                    "WARNING": "MEDIUM",
                    "INFO": "LOW",
                }[level],
                "count": count,
                "label": label,
            }
        )
        if (kind and kind != code) or (severity and severity != level):
            continue
        total += count
        if remaining_offset >= count:
            remaining_offset -= count
            continue
        available = limit - len(issues)
        if available > 0:
            ids = session.scalars(
                query.order_by(query.selected_columns.id)
                .offset(remaining_offset)
                .limit(available)
            )
            for identifier in ids:
                recorded = (
                    session.get(QualityIssue, identifier)
                    if code == "RECORDED_IMPORT_ISSUE"
                    else None
                )
                issues.append(
                    {
                        "id": f"{code}:{identifier}",
                        "code": code,
                        "severity": level,
                        "record_id": identifier,
                        "resource": resource,
                        "description": recorded.description if recorded else label,
                        "batch_id": recorded.batch_id if recorded else None,
                        "suggested_correction": correction,
                    }
                )
        remaining_offset = 0
    return {
        "as_of": at.isoformat(),
        "audit_date": day.isoformat(),
        "issues": issues,
        "checks": counts,
        "total": total,
        "limit": limit,
        "offset": offset,
        "unavailable_checks": [
            {
                "code": "INVALID_IMPORT_ROW_HISTORY",
                "reason": "Legacy direct-import rejected rows were not retained. Phase 5A staged import reports are stored and audited; historical missing records cannot be reconstructed.",
            }
        ],
        "notes": [
            "Recurring route-stop offsets count as scheduled stop times; a missing TripStopTime observation does not mean no timetable exists.",
            "A current base service validity window is accepted without a separate Calendar row.",
            "Platform and operational audits describe verification coverage, not guaranteed real-time service conditions.",
        ],
    }
