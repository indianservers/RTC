"""English text dialogue policies; all transport facts come from query results."""

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def registry(session=None):
    if session is not None:
        from .taxonomy import IntentRegistry

        rows = IntentRegistry(session).list()
        if rows:
            return [r.model_dump() for r in rows]
    return json.loads(
        (ROOT / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
    )["intents"]


def classify_extra(text, existing, session=None):
    # Canonical codes and exact authored registry examples cover every taxonomy entry.
    rows = registry(session)
    for row in rows:
        if text.rstrip(".?!") in [
            row["code"].lower().replace("_", " "),
            *[x.lower().rstrip(".?!") for x in row["examples"]],
        ]:
            return [row.get("backend_code") or row["code"]]
    additions = {
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


STATION_INTENTS = {"STATION_FACILITIES", "STATION_HELPDESK", "LOST_PROPERTY_CONTACT"}
SERVICE_INTENTS = {
    "ROUTE_STOPS",
    "BOARDING_POINT",
    "ALIGHTING_POINT",
    "INTERMEDIATE_STOP",
    "BUS_LIVE_STATUS",
    "BUS_CANCELLATION",
}
TRIP_INTENTS = {"SEAT_AVAILABILITY", "BUS_PLATFORM", "BUS_DELAY", "SERVICE_DISRUPTION"}
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
        elif intent == "CONCESSION_ELIGIBILITY":
            if not slots.get("filters", {}).get("operator"):
                return "AWAITING_OPERATOR"
        elif intent in SERVICE_INTENTS | TRIP_INTENTS:
            if not slots.get("service_id") and not slots.get("service_number"):
                return "AWAITING_SERVICE"
            if intent == "BUS_PLATFORM" and not slots.get("origin"):
                return "AWAITING_ORIGIN"
        else:
            if not slots.get("destination"):
                return "AWAITING_DESTINATION"
            if not slots.get("origin"):
                return "AWAITING_ORIGIN"
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
        return "No matching information is available for that enquiry."
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
