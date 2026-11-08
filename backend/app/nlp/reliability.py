"""Bounded repair/diagnosis policies over the existing conversation and enquiry engines."""

import re
from copy import deepcopy
from datetime import datetime, time, timedelta
from enum import StrEnum
from time import perf_counter
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import aliased

from ..domain import Service, Station, Stop
from ..engine import EnquiryRequest
from ..operations import Trip


class ErrorCategory(StrEnum):
    INTENT_MISCLASSIFICATION = "INTENT_MISCLASSIFICATION"
    ENTITY_RESOLUTION_ERROR = "ENTITY_RESOLUTION_ERROR"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    AMBIGUOUS_REFERENCE = "AMBIGUOUS_REFERENCE"
    CONTRADICTORY_FILTERS = "CONTRADICTORY_FILTERS"
    NO_MATCHING_SERVICE = "NO_MATCHING_SERVICE"
    DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"
    STALE_OPERATIONAL_DATA = "STALE_OPERATIONAL_DATA"
    DATABASE_ERROR = "DATABASE_ERROR"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    UNSUPPORTED_ENQUIRY = "UNSUPPORTED_ENQUIRY"


class Reliability(BaseModel):
    confidence_state: Literal[
        "CONFIDENT",
        "CLARIFICATION_REQUIRED",
        "LOW_CONFIDENCE",
        "OUT_OF_SCOPE",
        "UNSUPPORTED",
    ] = "CONFIDENT"
    error_category: ErrorCategory | None = None
    failure_group: str | None = None
    classification_is_provisional: bool = True
    score_kind: str = "DETERMINISTIC_RULES"
    probability: float | None = None
    decision_margin: float | None = None
    top_two_gap: float | None = None
    model_status: str = "RULES"
    repair: str | None = None
    repair_detection_ms: float = 0
    diagnostic_ms: float = 0
    diagnosis: list[dict] = Field(default_factory=list)


class ConversationRepairEngine:
    def prepare(self, text):
        start = perf_counter()
        kind = None
        if re.search(
            r"(?:i asked for|i wanted|i meant) (?:the )?fare,? not (?:the )?(?:timing|time)",
            text,
        ):
            text = "what is the fare?"
            kind = "INTENT_CORRECTION"
        elif re.search(r"(?:no,? )?i meant (?:the )?last bus", text):
            text = "last bus of the day"
            kind = "INTENT_CORRECTION"
        elif re.search(
            r"that.s (?:not the bus i selected|the wrong bus)|wrong bus selected", text
        ):
            text = "not that bus"
            kind = "SELECTION_REPAIR"
        elif re.search(r"^i said (.+),? not (.+)", text):
            match = re.search(r"^i said (.+?),? not (.+)", text)
            text = "actually, " + match[1]
            kind = "ENTITY_CORRECTION"
        elif re.search(r"^(?:no|actually|i meant)\b", text):
            kind = "CONTEXT_CORRECTION"
        return text, kind, (perf_counter() - start) * 1000

    def conflict(self, text):
        if re.search(r"\bfirst\b.*\bor\b.*\bnext\b|\bnext\b.*\bor\b.*\bfirst\b", text):
            return {
                "answer": "Do you want the first bus of the day or the next available bus?",
                "act": "CLARIFICATION",
                "state": "CLARIFICATION_REQUIRED",
                "clarify": True,
                "results": [],
                "intents": [],
                "choices": [
                    {
                        "id": "first",
                        "label": "First bus of the day",
                        "text": "First bus of the day",
                    },
                    {"id": "next", "label": "Next available bus", "text": "Next bus"},
                ],
            }
        return None


def diagnose(engine, slots, now):
    """Counterfactual probes explain empty searches; never mutate passenger restrictions."""
    started = perf_counter()
    diagnoses = []
    if not slots.get("origin") or not slots.get("destination"):
        return [], 0
    if slots.get("journey_mode") and (
        slots.get("transfer_station") or slots.get("journey_max_transfers", 2) > 0
    ):
        return [
            {
                "code": "CONNECTION_FEASIBILITY_UNCONFIRMED",
                "message": "No feasible connection matched the recorded stop times and your current restrictions. A single cause has not been established.",
                "evidence_count": 0,
                "constraint_changed": False,
            }
        ], (perf_counter() - started) * 1000
    station = engine.session.get(Station, slots["origin"])
    day = datetime.fromisoformat(slots["travel_date"]).date()
    lo = datetime.combine(day, time.min, ZoneInfo(station.timezone))
    hi = lo + timedelta(days=1)
    at = max(lo, now) if day == now.astimezone(lo.tzinfo).date() else lo
    filters = deepcopy(slots.get("filters", {}))
    for keys, code, message in [
        (
            ("ac", "sleeper", "category", "exclude_categories"),
            "CATEGORY_RESTRICTION",
            "Recorded services match when the bus category restrictions are removed.",
        ),
        (
            ("after", "before", "arrival_before", "arrival_after"),
            "TIME_WINDOW",
            "Recorded services match outside the requested time window.",
        ),
        (
            ("max_fare", "min_fare"),
            "FARE_LIMIT",
            "Recorded services match when the fare limit is removed; unknown fares are not assumed affordable.",
        ),
    ]:
        if not any(filters.get(k) is not None for k in keys):
            continue
        relaxed = {k: v for k, v in filters.items() if k not in keys}
        relaxed.setdefault("before", hi.isoformat())
        request = EnquiryRequest(
            intent="NEXT_BUS",
            origin=slots["origin"],
            destination=slots["destination"],
            travel_date=day,
            at=at,
            filters=relaxed,
            limit=5,
        )
        result = engine.enquire(request)
        if result.results:
            diagnoses.append(
                {
                    "code": code,
                    "message": message,
                    "evidence_count": len(result.results),
                    "query": request.model_dump(mode="json"),
                    "constraint_changed": False,
                }
            )
    if not diagnoses:
        a, b = aliased(Stop), aliased(Stop)
        services = list(
            engine.session.scalars(
                select(Service)
                .join(a, a.route_id == Service.route_id)
                .join(b, b.route_id == Service.route_id)
                .where(
                    a.station_id == slots["origin"],
                    b.station_id == slots["destination"],
                    a.sequence < b.sequence,
                    a.active.is_(True),
                    b.active.is_(True),
                    a.boarding.is_(True),
                    b.alighting.is_(True),
                    Service.active.is_(True),
                )
                .distinct()
                .limit(501)
            )
        )
        operator = filters.get("operator")
        if operator:
            from ..domain import Operator

            op = engine.session.scalar(
                select(Operator).where(
                    (Operator.id == operator) | (Operator.code == operator)
                )
            )
            services = [s for s in services if op and s.operator_id == op.id]
        trips = (
            list(
                engine.session.scalars(
                    select(Trip).where(
                        Trip.service_id.in_([s.id for s in services]),
                        Trip.service_date == day,
                        Trip.active.is_(True),
                    )
                )
            )
            if services
            else []
        )
        if not services:
            code, message = (
                "NO_DIRECT_ROUTE",
                "No published active direct service is recorded for this segment. Connecting options may still exist.",
            )
        elif all(not s.valid_from <= day <= s.valid_to for s in services):
            code, message = (
                "OUTSIDE_COVERAGE",
                "The requested date is outside the recorded validity ranges for these direct services.",
            )
        elif trips and all(t.status == "cancelled" for t in trips):
            code, message = (
                "RECORDED_CANCELLATIONS",
                "All recorded dated trips for this segment and date are marked cancelled; no eligible departures matched.",
            )
        else:
            code, message = (
                "COVERAGE_UNCONFIRMED",
                "No eligible scheduled departures matched. Calendar coverage, publication or availability cannot be established from this diagnosis.",
            )
        diagnoses.append(
            {
                "code": code,
                "message": message,
                "evidence_count": len(services),
                "constraint_changed": False,
            }
        )
    return diagnoses, (perf_counter() - started) * 1000


def assess(state, clarify, intents, results, prediction, answer):
    info = Reliability(
        model_status=prediction.get("status", "RULES"),
        decision_margin=prediction.get("decision_margin"),
        top_two_gap=prediction.get("top_two_gap"),
        score_kind="SVM_MARGIN_NOT_PROBABILITY"
        if prediction.get("decision_margin") is not None
        else "DETERMINISTIC_RULES",
    )
    if state == "OUT_OF_SCOPE":
        info.confidence_state = "OUT_OF_SCOPE"
        return info
    if any(r.get("status") == "UNSUPPORTED" for r in results):
        info.confidence_state = "UNSUPPORTED"
        info.error_category = ErrorCategory.UNSUPPORTED_ENQUIRY
    elif clarify:
        info.confidence_state = (
            "LOW_CONFIDENCE"
            if state == "IDLE" or prediction.get("status") == "CLARIFICATION_REQUIRED"
            else "CLARIFICATION_REQUIRED"
        )
        info.error_category = (
            ErrorCategory.CONTRADICTORY_FILTERS
            if re.search(r"contradict|choose AC or|conflicting", answer, re.IGNORECASE)
            else ErrorCategory.ENTITY_RESOLUTION_ERROR
            if "STATION" in state or "CATEGORY" in state
            else ErrorCategory.MISSING_CONTEXT
            if state.startswith("AWAITING")
            else ErrorCategory.AMBIGUOUS_REFERENCE
        )
        info.failure_group = "CONTEXT_ERROR"
        if info.confidence_state == "LOW_CONFIDENCE" and prediction.get("status") in {
            "NOT_READY",
            "MISSING_MODEL",
            "CHECKSUM_MISMATCH",
        }:
            info.error_category = ErrorCategory.MODEL_UNAVAILABLE
            info.failure_group = "OPERATIONAL_ERROR"
    elif state == "NO_RESULTS":
        info.error_category = ErrorCategory.NO_MATCHING_SERVICE
        info.failure_group = "DATA_ERROR"
    elif any(
        r.get("status") == "STALE"
        or any(
            row.get("status") in {"stale", "STALE"}
            or row.get("gps_status") == "STALE"
            or row.get("delay_status") == "STALE"
            for row in r.get("results", [])
        )
        for r in results
    ):
        info.error_category = ErrorCategory.STALE_OPERATIONAL_DATA
        info.failure_group = "DATA_ERROR"
    elif results and any(
        r.get("status") == "UNKNOWN"
        or any(
            row.get("status") == "unknown"
            or "amount" in row
            and row["amount"] is None
            or "bay" in row
            and row["bay"] is None
            for row in r.get("results", [])
        )
        for r in results
    ):
        info.error_category = ErrorCategory.DATA_NOT_AVAILABLE
        info.failure_group = "DATA_ERROR"
    return info


def stale_platform_evidence(engine, results, now):
    from ..operations import PlatformAssignment, StationBay

    evidence = []
    for result in results:
        query = result.get("query", {})
        if (
            result.get("intent") != "BUS_PLATFORM"
            or not query.get("trip_id")
            or not any(r.get("status") == "unknown" for r in result.get("results", []))
        ):
            continue
        row = engine.session.scalar(
            select(PlatformAssignment)
            .join(StationBay, StationBay.id == PlatformAssignment.bay_id)
            .where(
                PlatformAssignment.trip_id == query["trip_id"],
                StationBay.station_id == (query.get("station") or query.get("origin")),
                PlatformAssignment.active.is_(True),
                PlatformAssignment.verified.is_(True),
                PlatformAssignment.effective_at <= now,
                PlatformAssignment.expires_at <= now,
            )
            .order_by(PlatformAssignment.effective_at.desc())
            .limit(1)
        )
        if row:
            evidence.append(
                {
                    "code": "STALE_PLATFORM_RECORD",
                    "message": "The previous recorded platform assignment has expired. The current platform remains unconfirmed.",
                    "source_id": row.source_id,
                    "expires_at": row.expires_at.isoformat(),
                    "constraint_changed": False,
                }
            )
    return evidence
