"""Standalone oracle. No production imports; all times are timezone-aware ISO 8601."""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

SOURCE = "SYNTHETIC"
def dt(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result

def active(trip, day):
    exceptions = trip.get("exceptions", {})
    if day.isoformat() in exceptions:
        return exceptions[day.isoformat()]
    return (trip.get("valid_from", "0001-01-01") <= day.isoformat() <=
            trip.get("valid_to", "9999-12-31") and day.weekday() in trip.get("weekdays", range(7)))

def journeys(state, origin, destination, now, max_transfers=2, transfer_minutes=10):
    """Enumerate directed, time-respecting segments, including intermediate stops.

    Trip stop timestamps are absolute occurrences, not recurring time-of-day values.
    Calendars apply to the first stop's operating date, including overnight trips.
    """
    now = dt(now)
    edges = []
    for trip in state.get("trips", []):
        if trip.get("cancelled") or not active(trip, dt(trip["stops"][0]["departure"]).date()):
            continue
        delay = timedelta(minutes=trip.get("delay_minutes", 0))
        for i, start in enumerate(trip["stops"]):
            for end in trip["stops"][i+1:]:
                edges.append(dict(service_id=trip["id"], origin=start["station"],
                    destination=end["station"], departure=(dt(start["departure"])+delay).isoformat(),
                    arrival=(dt(end["arrival"])+delay).isoformat(), source_label=trip["source_label"]))
    found = []
    def walk(station, ready, legs, visited):
        if len(legs) >= max_transfers + 1:
            return
        for edge in edges:
            if edge["origin"] != station or edge["destination"] in visited:
                continue
            if any(x["service_id"] == edge["service_id"] for x in legs):
                continue
            if dt(edge["departure"]) < ready:
                continue
            chain = legs + [edge]
            if edge["destination"] == destination:
                found.append(chain)
            else:
                walk(edge["destination"], dt(edge["arrival"])+timedelta(minutes=transfer_minutes),
                     chain, visited | {edge["destination"]})
    walk(origin, now, [], {origin})
    return sorted(found, key=lambda legs: (dt(legs[-1]["arrival"]), len(legs), str(legs)))

def fare(rule, query):
    if rule is None:
        return {"amount": None, "warnings": ["FARE_UNKNOWN"]}
    day = query["date"]
    if day < rule["valid_from"] or day > rule["valid_to"]:
        return {"amount": None, "warnings": ["FARE_EXPIRED"]}
    mode = rule["mode"]
    if mode == "fixed":
        amount = Decimal(rule["amount"])
    elif mode == "stop":
        value = rule["pairs"].get(query["origin"]+":"+query["destination"])
        if value is None:
            return {"amount": None, "warnings": ["FARE_UNKNOWN"]}
        amount = Decimal(value)
    elif mode in ("stage", "distance"):
        amount = Decimal(rule["rate"])*Decimal(str(query["stages" if mode == "stage" else "distance_km"]))
    else:
        raise ValueError("Unknown fare mode")
    amount = Decimal(query.get("trip_override", amount))
    amount += Decimal(rule.get("surcharge", "0"))
    concession = Decimal(rule.get("concessions", {}).get(query.get("concession"), "0"))
    amount *= Decimal(1)-concession
    if amount < 0:
        raise ValueError("Negative fare")
    return {"amount": str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "warnings": []}

def evaluate(state, query, now):
    intent = query["intent"]
    warnings = []
    if intent == "journey":
        value = [[x["service_id"] for x in legs] for legs in journeys(state, query["origin"],
            query["destination"], now, query.get("max_transfers", 2), query.get("transfer_minutes", 10))]
    elif intent == "fare":
        result = fare(state.get("fare_rule"), query)
        value, warnings = result["amount"], result["warnings"]
    elif intent == "selection":
        value = state["candidates"]
        warnings = ["AMBIGUOUS_SELECTION"] if len(value) > 1 else []
    elif intent == "cheapest":
        known = [x for x in state["prices"] if x["amount"] is not None]
        value = min(known, key=lambda x: Decimal(x["amount"]))["id"] if known else None
        warnings = [] if known else ["FARE_UNKNOWN"]
    else:
        trip = next((t for t in state.get("trips", []) if t["id"] == query["service_id"]), None)
        if trip is None:
            value, warnings = None, ["SERVICE_UNKNOWN"]
        elif intent == "departure":
            value = [s["departure"] for s in trip["stops"] if dt(s["departure"]) >= dt(now)] if not trip.get("cancelled") else []
        elif intent == "arrival":
            value = trip["stops"][-1]["arrival"]
        elif intent == "amenities":
            value = trip["amenities"]
        elif intent == "seats":
            snap = trip.get("seat_snapshot")
            if snap is None:
                value, warnings = None, ["SEATS_UNKNOWN"]
            elif (dt(now)-dt(snap["observed_at"])).total_seconds() > 900:
                value, warnings = None, ["SEATS_STALE"]
            else:
                value = snap["available"]
        elif intent == "status":
            value = {"cancelled": trip.get("cancelled", False), "delay_minutes": trip.get("delay_minutes", 0)}
        elif intent == "platform":
            value = trip.get("platform")
            if value is None:
                warnings = ["PLATFORM_UNKNOWN"]
        elif intent == "gps":
            value = None
            warnings = ["GPS_STALE" if trip.get("gps_stale") else "GPS_UNKNOWN"]
        else:
            raise ValueError("Unsupported intent: "+intent)
    return {"value": value, "warnings": warnings, "source_label": SOURCE}
