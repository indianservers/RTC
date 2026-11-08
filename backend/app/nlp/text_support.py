"""English text dialogue policies; all transport facts come from query results."""

import json
import re
from datetime import datetime
from pathlib import Path

from ..local_intents import (
    LOCAL_INTENTS,
    OPERATOR_LOCAL,
    STATION_LOCAL,
    TRIP_LOCAL,
    enrich_definition,
)

ROOT = Path(__file__).resolve().parents[3]


def registry(session=None):
    if session is not None:
        from .taxonomy import IntentRegistry

        rows = IntentRegistry(session).list()
        if rows:
            return [r.model_dump() for r in rows]
    return [
        enrich_definition(r)
        for r in json.loads(
            (ROOT / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
        )["intents"]
    ]


def classify_extra(text, existing, session=None):
    # Canonical codes and exact authored registry examples cover every taxonomy entry.
    rows = registry(session)
    for row in rows:
        if text.rstrip(".?!") in [
            row["code"].lower().replace("_", " "),
            *[x.lower().rstrip(".?!") for x in row["examples"]],
        ]:
            return [row.get("backend_code") or row["code"]]
    local_patterns = {
        "FIRST_BUS": r"which.*leaves earliest",
        "CHEAPEST_BUS": r"cheaper category",
        "BUS_VIA_LOCATION": r"(?:does|will).*stop at|pass through",
        "BUS_AT_TIME": r"\b(?:bus|buses).*\b(?:at|around)\s+\d",
        "SERVICE_FREQUENCY": r"how often|service frequency|how frequently",
        "SPECIAL_DAY_SCHEDULE": r"festival.*schedule|special day schedule|holiday timetable",
        "ACCESSIBLE_BUS_AVAILABILITY": r"wheelchair|accessible buses",
        "BUS_CAPACITY": r"bus capacity|how many.*(?:seats|berths).*total",
        "ROUTE_DISTANCE": r"route distance|how many kilo|how far",
        "DESTINATION_REACHABILITY": r"is.*reachable|^can i reach",
        "BOOKING_OPTIONS": r"where.*(?:book|buy).*ticket|booking options",
        "ESTIMATED_ARRIVAL": r"estimated arrival|arrival estimate|current eta",
        "BUS_DEPARTED_STATUS": r"has.*departed|already left",
        "BUS_ARRIVED_STATUS": r"has.*arrived|already reached",
        "PLATFORM_CHANGE": r"platform.*changed|changed.*platform|bay.*changed",
        "OPERATOR_CONTACT": r"operator contact|operator website",
        "STATION_NAVIGATION": r"station navigation|where.*bay|which floor",
        "COMPLAINT_GUIDANCE": r"complaint|complain",
    }
    local = [i for i, p in local_patterns.items() if re.search(p, text)]
    if local:
        return local
    additions = {
        "CONNECTING_BUSES": r"connecting buses|need to reach|how can i (?:reach|get to)|how (?:do|can) i travel to",
        "TICKET_FARE": r"how much|cost|ticket price",
        "NEXT_BUS": r"when is (?:the |a )?bus|bus timings?|what time.*bus",
        "ARRIVAL_TIME": r"reach(?:es)? .*first|when.*reach",
        "BUS_CANCELLATION": r"is.*cancelled|has.*cancelled",
        "BUS_PLATFORM": r"which bay",
        "STATION_FACILITIES": r"toilets?|drinking water|waiting room",
    }
    mapping = {r["code"]: r.get("backend_code") or r["code"] for r in rows}
    result = list(dict.fromkeys(mapping.get(i, i) for i in existing))
    for intent, pattern in additions.items():
        if re.search(pattern, text) and intent not in result:
            result.append(intent)
    return result


STATION_INTENTS = {
    "STATION_FACILITIES",
    "STATION_HELPDESK",
    "LOST_PROPERTY_CONTACT",
} | STATION_LOCAL
SERVICE_INTENTS = {
    "ROUTE_STOPS",
    "BOARDING_POINT",
    "ALIGHTING_POINT",
    "INTERMEDIATE_STOP",
    "BUS_LIVE_STATUS",
    "BUS_CANCELLATION",
}
TRIP_INTENTS = {
    "SEAT_AVAILABILITY",
    "BUS_PLATFORM",
    "BUS_DELAY",
    "SERVICE_DISRUPTION",
} | TRIP_LOCAL
SUPPORTED = {r["backend_code"] for r in registry() if r.get("backend_code")}


def missing(intents, slots):
    for intent in intents:
        if intent not in SUPPORTED:
            continue
        if intent in STATION_INTENTS:
            if not slots.get("origin"):
                return "AWAITING_ORIGIN"
        elif intent == "SERVICE_NUMBER_LOOKUP":
            if not slots.get("service_number"):
                return "AWAITING_SERVICE"
        elif intent == "CONCESSION_ELIGIBILITY" or intent in OPERATOR_LOCAL:
            if not slots.get("filters", {}).get("operator"):
                return "AWAITING_OPERATOR"
        elif intent in SERVICE_INTENTS | TRIP_INTENTS:
            if not slots.get("service_id") and not slots.get("service_number"):
                return "AWAITING_SERVICE"
            if intent in {
                "BUS_PLATFORM",
                "PLATFORM_CHANGE",
                "ESTIMATED_ARRIVAL",
                "BUS_ARRIVED_STATUS",
                "BUS_DEPARTED_STATUS",
            } and not slots.get("origin"):
                return "AWAITING_ORIGIN"
        else:
            if not slots.get("destination"):
                return "AWAITING_DESTINATION"
            if not slots.get("origin"):
                return "AWAITING_ORIGIN"
            if intent == "BUS_AT_TIME" and not slots.get("requested_clock"):
                return "AWAITING_TIME"
            if intent == "ROUTE_DISTANCE" and not slots.get("service_id"):
                return "AWAITING_SERVICE"
            if intent == "BUS_VIA_LOCATION" and not slots.get("via"):
                return "AWAITING_VIA"
    return None


def clock_text(value):
    return (
        datetime.fromisoformat(value)
        .strftime("%d %b %Y at %I:%M %p")
        .replace(" 0", " ")
    )


def render_result(result):
    intent = result.get("query", {}).get("intent", result["intent"])
    rows = result["results"]
    if result["status"] == "UNSUPPORTED":
        return (
            "This database enquiry does not support "
            + intent.lower().replace("_", " ")
            + "."
        )
    if result["status"] == "INVALID_QUERY":
        return (
            "I could not complete that enquiry: " + "; ".join(result["warnings"]) + "."
        )
    if not rows:
        if intent in LOCAL_INTENTS:
            return "No supporting local records are available for this enquiry." + (
                " " + " ".join(result.get("warnings", []))
            )
        return "No matching information is available for that enquiry."
    if intent in LOCAL_INTENTS:
        return render_local(intent, rows, result.get("warnings", []))
    if intent == "SEAT_AVAILABILITY":
        r = rows[0]
        return (
            f"The recorded seat count is {r['known_vacant']}."
            if r.get("status") in ("available", "not_available")
            and r.get("known_vacant") is not None
            else "Seat availability information is not available."
            + (" The last snapshot is stale." if r.get("status") == "stale" else "")
        )
    if intent == "BUS_PLATFORM":
        return (
            f"The platform is {rows[0]['bay']}."
            if rows[0].get("bay")
            else "The platform has not been confirmed."
        )
    if intent in ("BUS_LIVE_STATUS", "BUS_CANCELLATION", "BUS_DELAY"):
        r = rows[0]
        if intent == "BUS_DELAY":
            return (
                f"The recorded delay is {r['delay_minutes']} minutes."
                if r.get("delay_status") == "KNOWN"
                and r.get("delay_minutes") is not None
                else "Delay information is not confirmed."
            )
        if str(r.get("status", "unknown")).lower() in (
            "unknown",
            "stale",
            "scheduled_only",
        ):
            return "Current operational status is not confirmed." + (
                " The last report is stale." if r.get("status") == "stale" else ""
            )
        return (
            "Recorded status: "
            + str(r.get("status", "unknown")).replace("_", " ")
            + "."
        )
    if intent in (
        "ROUTE_STOPS",
        "INTERMEDIATE_STOP",
        "BOARDING_POINT",
        "ALIGHTING_POINT",
    ):
        return (
            "Recorded stops: "
            + ", ".join(
                str(r.get("station_name", r.get("station_id", "unknown"))) for r in rows
            )
            + "."
        )
    if intent in STATION_INTENTS:
        return (
            "Recorded information: "
            + "; ".join(
                str(r.get("name", r.get("contact_type", "Contact")))
                + (": " + str(r.get("phone")) if r.get("phone") else "")
                for r in rows
            )
            + "."
        )
    if intent == "CONCESSION_ELIGIBILITY":
        return (
            "; ".join(
                f"{r['name']}: {r['percent']}%; eligibility has not been confirmed"
                for r in rows
            )
            + "."
        )
    answers = []
    for n, r in enumerate(rows[:5], 1):
        if "legs" in r:
            answers.append(
                f"{n}. Connect using "
                + " then ".join(
                    str(x.get("service_number", x.get("service_id"))) for x in r["legs"]
                )
                + "; arrival "
                + clock_text(r["arrival"])
                + "."
            )
            continue
        service = str(r.get("service_number", r.get("number", "Selected service")))
        if "departure" in r:
            if intent == "TICKET_FARE" or intent == "FARE_COMPARISON":
                line = f"{n}. Service {service}: " + (
                    f"fare INR {r['fare']}."
                    if r.get("fare") is not None
                    else "Fare information is not available."
                )
            elif intent == "ARRIVAL_TIME":
                line = (
                    f"{n}. Service {service}: {r.get('arrival_kind', 'scheduled')} arrival "
                    + clock_text(r["arrival"])
                    + "."
                )
            elif intent == "JOURNEY_DURATION":
                minutes = int(
                    (
                        datetime.fromisoformat(r["arrival"])
                        - datetime.fromisoformat(r["departure"])
                    ).total_seconds()
                    / 60
                )
                line = f"{n}. Service {service}: journey time {minutes} minutes."
            elif intent == "BUS_AMENITIES":
                line = (
                    f"{n}. Service {service}: "
                    + (
                        ", ".join(
                            str(a.get("name", a.get("code", "recorded amenity")))
                            for a in r.get("amenities", [])
                        )
                        or "No amenities have been recorded"
                    )
                    + "."
                )
            else:
                line = (
                    f"{n}. {r.get('category_name', 'Bus')} service {service}: {r.get('departure_kind', 'scheduled')} departure "
                    + clock_text(r["departure"])
                    + "."
                )
                if r.get("fare") is not None:
                    line += f" Fare INR {r['fare']}."
            answers.append(line)
        else:
            answers.append(f"{n}. Service {service}.")
    return "\n".join(answers)


def render(results):
    answer = "\n".join(render_result(r) for r in results)

    def demo(value):
        if isinstance(value, dict):
            return value.get("dataset_source") in ("DEMO", "SYNTHETIC") or any(
                demo(v) for v in value.values()
            )
        return isinstance(value, list) and any(demo(v) for v in value)

    if demo(results):
        answer = "Demo schedule/data: " + answer
    return answer


def render_local(intent, rows, warnings):
    if intent == "BUS_CAPACITY":
        r = rows[0]
        return (
            f"Recorded capacity: {r['capacity']}."
            if "capacity" in r
            else f"Recorded layout: {r['seating_capacity']} seats and {r['berth_capacity']} berths."
        ) + " This is not seat availability."
    if intent == "ROUTE_DISTANCE":
        return f"The recorded route segment distance is {rows[0]['distance_km']} km."
    if intent == "SERVICE_FREQUENCY":
        r = rows[0]
        return (
            f"There are {r['count']} recorded departures on this date."
            + (
                " Gaps between distinct departures (minutes): "
                + ", ".join(map(str, r["gap_minutes"]))
                + "."
                if r["gap_minutes"]
                else " No headway can be calculated."
            )
            + " This is not a guaranteed frequency."
        )
    if intent == "BOOKING_OPTIONS":
        return (
            "Recorded booking options: "
            + "; ".join(r["name"] + ": " + r["instructions"] for r in rows)
            + "."
        )
    if intent == "OPERATOR_CONTACT":
        return "Recorded operator website: " + rows[0]["website"] + "."
    if intent == "COMPLAINT_GUIDANCE":
        return (
            "Recorded complaint contacts: "
            + "; ".join(r["label"] + ": " + r["contact_value"] for r in rows)
            + ". Contact availability has not been live-verified."
        )
    if intent == "STATION_NAVIGATION":
        return (
            "Recorded locations: "
            + "; ".join(
                (r.get("station_name", "") + ": " + r["address"])
                if r.get("address")
                else "Bay " + r["bay"] + ": " + r["zone"]
                for r in rows
            )
            + ". No indoor route is inferred."
        )
    if intent == "PLATFORM_CHANGE":
        r = rows[0]
        return (
            f"The recorded platform changed from {r['previous_bay']} to {r['current_bay']}."
            if r["changed"]
            else f"The two latest recorded assignments both name platform {r['current_bay']}."
        )
    if intent == "ESTIMATED_ARRIVAL":
        return (
            "The fresh verified arrival estimate is "
            + clock_text(rows[0]["estimated_arrival"])
            + "."
        )
    if intent in ("BUS_DEPARTED_STATUS", "BUS_ARRIVED_STATUS"):
        field = (
            "actual_departure" if intent == "BUS_DEPARTED_STATUS" else "actual_arrival"
        )
        return (
            "The bus was recorded as "
            + ("departed" if field == "actual_departure" else "arrived")
            + " at "
            + clock_text(rows[0][field])
            + "."
        )
    # Existing timetable formatter handles the actual journey facts.
    legacy = "CONNECTING_BUSES" if intent == "DESTINATION_REACHABILITY" else "NEXT_BUS"
    return render_result(
        {"intent": legacy, "query": {"intent": legacy}, "results": rows, "status": "KNOWN"}
    ) + (" " + " ".join(warnings) if warnings else "")
