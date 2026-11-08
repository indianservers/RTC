"""Resolve only from valid current result references; never assume a tie-break."""

import hashlib
import itertools
from decimal import Decimal


class StaleResult(ValueError):
    """A previously listed result is no longer eligible in the database."""


def stable_results(rows):
    return [
        {
            **r,
            "result_id": hashlib.sha256(
                "|".join(
                    str(r.get(k, ""))
                    for k in (
                        "service_id",
                        "service_date",
                        "origin_id",
                        "destination_id",
                        "departure",
                        "arrival",
                    )
                ).encode()
            ).hexdigest()[:20],
        }
        for r in rows
    ]


def selected_rows(engine, state, now):
    """Refresh the exact service/date/stop segments through the existing enquiry engine."""
    from datetime import datetime, timedelta

    from ..engine import EnquiryRequest

    itinerary = state.get("selected_itinerary")
    chosen = state.get("selected_result")
    if not itinerary and not chosen:
        return []
    legs = itinerary["legs"] if itinerary else [chosen]
    refreshed = []
    for leg in legs:
        departure = datetime.fromisoformat(leg.get("boarding_at") or leg["departure"])
        service_date = leg.get("service_date") or state["travel_date"]
        origin = leg.get("origin") or leg["origin_id"]
        destination = leg.get("destination") or leg["destination_id"]
        query = EnquiryRequest(
            intent="NEXT_BUS",
            service_id=leg["service_id"],
            origin=origin,
            destination=destination,
            travel_date=service_date,
            at=max(now, departure.replace(hour=0, minute=0, second=0, microsecond=0)),
            limit=100,
        )
        result = engine.enquire(query)
        row = next(
            (
                r
                for r in result.results
                if r.get("service_id") == leg["service_id"]
                and str(r.get("service_date")) == str(service_date)
                and (
                    not leg.get("boarding_stop_id")
                    or r.get("boarding_stop_id") == leg["boarding_stop_id"]
                )
                and (
                    not leg.get("alighting_stop_id")
                    or r.get("alighting_stop_id") == leg["alighting_stop_id"]
                )
            ),
            None,
        )
        if row is None:
            raise StaleResult(
                "The selected departure is no longer available: it may have departed, been cancelled, or changed. Please search for updated options."
            )
        row = {
            **row,
            "service_date": str(row["service_date"]),
            "departure": row["departure"].isoformat()
            if hasattr(row["departure"], "isoformat")
            else row["departure"],
            "arrival": row["arrival"].isoformat()
            if hasattr(row["arrival"], "isoformat")
            else row["arrival"],
            "fare": str(row["fare"]) if row.get("fare") is not None else None,
        }
        refreshed.append(row)
    for index, (a, b) in enumerate(itertools.pairwise(refreshed)):
        minimum = (
            itinerary.get("transfers", [])[index]["minimum_minutes"]
            if itinerary and index < len(itinerary.get("transfers", []))
            else 15
        )
        if datetime.fromisoformat(a["arrival"]) + timedelta(
            minutes=minimum
        ) > datetime.fromisoformat(b["departure"]):
            raise StaleResult(
                "A recorded schedule change makes the selected connection impossible. Please search for updated journeys."
            )
    if itinerary:
        updated = {
            **itinerary,
            "legs": [
                {
                    **old,
                    "trip_id": row.get("trip_id"),
                    "fare": row["fare"],
                    "boarding_at": row["departure"],
                    "alighting_at": row["arrival"],
                }
                for old, row in zip(legs, refreshed)
            ],
        }
        known = [Decimal(row["fare"]) for row in refreshed if row["fare"] is not None]
        updated.update(
            total_fare=format(sum(known, Decimal(0)), ".2f")
            if len(known) == len(refreshed)
            else None,
            known_subtotal=format(sum(known, Decimal(0)), ".2f"),
            fare_status="KNOWN"
            if len(known) == len(refreshed)
            else "PARTIAL"
            if known
            else "UNKNOWN",
            departure_at=refreshed[0]["departure"],
            arrival_at=refreshed[-1]["arrival"],
        )
        state["selected_itinerary"] = updated
        state["selected_result"] = updated
    else:
        state["selected_result"] = {**chosen, **refreshed[0]}
        state["service_id"] = refreshed[0]["service_id"]
        state["trip_id"] = refreshed[0].get("trip_id")
    return refreshed


def selected_enquiry(engine, intent, state, now):
    """Context adapter, not a second fare engine or journey planner."""
    from datetime import datetime

    from ..domain import Station
    from ..engine import EnquiryRequest, SearchFilters

    supported = {
        "TICKET_FARE",
        "GET_FARE",
        "BUS_PLATFORM",
        "ROUTE_STOPS",
        "BUS_VIA_LOCATION",
        "INTERMEDIATE_STOP",
        "ARRIVAL_TIME",
        "JOURNEY_DURATION",
        "BUS_AMENITIES",
        "BUS_LIVE_STATUS",
        "BUS_CANCELLATION",
        "BUS_DELAY",
        "BUS_ARRIVED_STATUS",
        "BUS_DEPARTED_STATUS",
        "ESTIMATED_ARRIVAL",
    }
    if intent not in supported or not (
        state.get("selected_itinerary") or state.get("selected_result")
    ):
        return None
    operational = {
        "BUS_PLATFORM",
        "BUS_LIVE_STATUS",
        "BUS_CANCELLATION",
        "BUS_DELAY",
        "BUS_ARRIVED_STATUS",
        "BUS_DEPARTED_STATUS",
        "ESTIMATED_ARRIVAL",
    }
    if intent in operational:
        from datetime import date

        from sqlalchemy import select

        from ..operations import Trip

        chosen = state.get("selected_itinerary") or state["selected_result"]
        legs = chosen.get("legs") or [chosen]
        index = state.get("selected_leg") or 0
        if index >= len(legs):
            raise ValueError("Which leg of the selected journey do you mean?")
        leg = legs[index]
        service_day = leg.get("service_date") or state["travel_date"]
        trip = engine.session.scalar(
            select(Trip).where(
                Trip.service_id == leg["service_id"],
                Trip.service_date == date.fromisoformat(str(service_day)),
                Trip.active.is_(True),
            )
        )
        current_trip = trip.id if trip else None
        leg["trip_id"] = current_trip
        response = engine.enquire(
            EnquiryRequest(
                intent=intent,
                service_id=leg["service_id"],
                trip_id=current_trip,
                origin=leg.get("origin") or leg["origin_id"],
                station=leg.get("origin") or leg["origin_id"],
                destination=leg.get("destination") or leg["destination_id"],
                travel_date=leg.get("service_date") or state["travel_date"],
                at=now,
            )
        )
        result = response.model_dump(mode="json")
        result["executor"] = "SelectedJourney -> RTCEnquiryEngine.enquire"
        if len(legs) == 1:
            state["trip_id"] = current_trip
            state["selected_trip_id"] = current_trip
        if len(legs) > 1:
            result["warnings"].append(
                f"Using boarding leg {index + 1} of the selected journey."
            )
        return result
    rows = selected_rows(engine, state, now)
    query = {
        "intent": intent,
        "filters": SearchFilters.model_validate(state.get("filters", {})).model_dump(
            mode="json"
        ),
        "origin": state.get("origin"),
        "destination": state.get("destination"),
        "travel_date": state.get("travel_date"),
        "selected_result_id": state.get("selected_result_id"),
        "service_id": rows[0]["service_id"] if len(rows) == 1 else None,
        "trip_id": rows[0].get("trip_id") if len(rows) == 1 else None,
        "segments": [
            {
                "service_id": r["service_id"],
                "service_date": r["service_date"],
                "origin": r["origin_id"],
                "destination": r["destination_id"],
                "boarding_stop_id": r.get("boarding_stop_id"),
                "alighting_stop_id": r.get("alighting_stop_id"),
            }
            for r in rows
        ],
    }
    result = {
        "intent": intent,
        "status": "KNOWN",
        "query": query,
        "results": [],
        "warnings": [],
        "executor": "SelectedJourney -> RTCEnquiryEngine.enquire",
        "pagination": {},
    }
    source = (
        "DEMO"
        if all(r.get("dataset_source") in {"DEMO", "SYNTHETIC"} for r in rows)
        else "LOCAL"
    )
    if intent in {"TICKET_FARE", "GET_FARE"}:
        amounts = [Decimal(r["fare"]) for r in rows if r["fare"] is not None]
        known = len(amounts) == len(rows)
        result["status"] = "KNOWN" if known else "PARTIAL" if amounts else "UNKNOWN"
        result["results"] = [
            {
                "amount": format(sum(amounts, Decimal(0)), ".2f") if known else None,
                "known": known,
                "currency": "INR",
                "known_subtotal": format(sum(amounts, Decimal(0)), ".2f"),
                "segments": [
                    {**segment, "amount": row["fare"]}
                    for segment, row in zip(query["segments"], rows)
                ],
                "journey_id": state.get("selected_journey_id"),
                "dataset_source": source,
            }
        ]
    elif intent in {"ARRIVAL_TIME", "JOURNEY_DURATION"}:
        result["results"] = [
            {
                "departure": rows[0]["departure"],
                "arrival": rows[-1]["arrival"],
                "minutes": int(
                    (
                        datetime.fromisoformat(rows[-1]["arrival"])
                        - datetime.fromisoformat(rows[0]["departure"])
                    ).total_seconds()
                    / 60
                ),
                "dataset_source": source,
            }
        ]
    elif intent == "BUS_AMENITIES":
        from sqlalchemy import select

        from ..catalog import Vehicle, VehicleType
        from ..links import ServiceVehicle

        for row in rows:
            vehicle = engine.session.scalar(
                select(Vehicle)
                .join(ServiceVehicle)
                .where(
                    ServiceVehicle.service_id == row["service_id"],
                    ServiceVehicle.active.is_(True),
                    Vehicle.active.is_(True),
                )
            )
            kind = engine.session.get(VehicleType, vehicle.type_id) if vehicle else None
            result["results"].append(
                {
                    "service_id": row["service_id"],
                    "ac": kind.ac if kind else None,
                    "sleeper": kind.sleeper if kind else None,
                    "dataset_source": source,
                }
            )
    elif intent in {"ROUTE_STOPS", "BUS_VIA_LOCATION", "INTERMEDIATE_STOP"}:
        for row in rows:
            stops = engine.enquiry.get_route_stops(
                row["service_id"],
                datetime.fromisoformat(row["departure"]).date()
                if not row.get("service_date")
                else datetime.fromisoformat(row["service_date"]).date(),
            )
            first = next(
                (r.sequence for r in stops if r.id == row.get("boarding_stop_id")), None
            )
            last = next(
                (r.sequence for r in stops if r.id == row.get("alighting_stop_id")),
                None,
            )
            for stop in stops:
                if (
                    first is not None
                    and last is not None
                    and first <= stop.sequence <= last
                ):
                    station = engine.session.get(Station, stop.station_id)
                    result["results"].append(
                        {
                            "service_id": row["service_id"],
                            "station_id": stop.station_id,
                            "station_name": station.name,
                            "boarding": stop.boarding,
                            "alighting": stop.alighting,
                            "dataset_source": source,
                        }
                    )
        if intent in {"BUS_VIA_LOCATION", "INTERMEDIATE_STOP"} and state.get("via"):
            target = engine.resolver.resolve(state["via"])
            target_ids = {s["id"] for s in target.get("candidates", [])}
            result["answer_text"] = (
                "Yes, the selected journey has that recorded stop."
                if any(r["station_id"] in target_ids for r in result["results"])
                else "That location is not a recorded stop on the selected travel segment."
            )
    else:
        index = state.get("selected_leg") or 0
        if index >= len(rows):
            raise ValueError("Which leg of the selected journey do you mean?")
        row = rows[index]
        response = engine.enquire(
            EnquiryRequest(
                intent=intent,
                service_id=row["service_id"],
                trip_id=row.get("trip_id"),
                origin=row["origin_id"],
                station=row["origin_id"],
                destination=row["destination_id"],
                travel_date=row["service_date"],
                at=now,
            )
        )
        result.update(
            results=response.model_dump(mode="json")["results"], status=response.status
        )
        if len(rows) > 1:
            result["warnings"] = [
                f"Using boarding leg {index + 1} of the selected journey."
            ]
    return result


class ReferentialResolver:
    def resolve(self, text, values):
        rows = values.get("candidates", [])
        if not rows:
            raise ValueError(
                "Please request a current result list before selecting a bus."
            )
        if "cheaper" in text or "cheapest one" in text:
            known = [r for r in rows if r.get("fare") is not None]
            if not known:
                raise ValueError("No known fares are available for comparison.")
            best = min(Decimal(str(r["fare"])) for r in known)
            matches = [r for r in known if Decimal(str(r["fare"])) == best]
        elif "fastest one" in text:
            from datetime import datetime

            known = [r for r in rows if r.get("arrival") and r.get("departure")]
            if not known:
                raise ValueError("Arrival times are unavailable for comparison.")
            duration = lambda r: (
                datetime.fromisoformat(r["arrival"])
                - datetime.fromisoformat(r["departure"])
            )
            best = min(duration(r) for r in known)
            matches = [r for r in known if duration(r) == best]
        elif "previous one" in text:
            history = values.get("selected_result_history", [])
            if history:
                matches = [
                    r
                    for r in rows
                    if (r.get("result_id") or r.get("journey_id")) == history[-1]
                ]
            else:
                history = values.get("selected_service_history", [])
                if not history:
                    raise ValueError("There is no previous confirmed selection.")
                matches = [r for r in rows if r.get("service_id") == history[-1]]
        else:
            selected = values.get("service_id")
            matches = [r for r in rows if r.get("service_id") == selected]
        if len(matches) != 1:
            raise ValueError(
                "Several or no current options match. Which listed service do you mean?"
            )
        return next(
            i
            for i, r in enumerate(rows)
            if (r.get("result_id") or r.get("service_id"))
            == (matches[0].get("result_id") or matches[0].get("service_id"))
        )


def conversational_reference(text, state, session):
    """Rewrite only unambiguous references to the existing numeric selection path."""
    import re
    from datetime import datetime

    from ..domain import Category, Service

    rows = state.get("candidates", [])
    bare = text.strip(".!? ")
    if bare in {"that one", "the same one", "this one"}:
        if not state.get("selected_result_id"):
            raise ValueError("Which listed option do you mean? Choose its number.")
        return "that bus"
    if bare in {"the next one", "the one before it", "the other one"}:
        current = next(
            (
                i
                for i, r in enumerate(rows)
                if r.get("result_id") == state.get("selected_result_id")
            ),
            None,
        )
        if current is None:
            raise ValueError("Which option should I use as the starting point?")
        if bare == "the other one":
            others = [i for i in range(len(rows)) if i != current]
            if len(others) != 1:
                raise ValueError(
                    "There is more than one other option. Which number do you mean?"
                )
            index = others[0]
        else:
            index = current + (1 if bare == "the next one" else -1)
        if not 0 <= index < len(rows):
            raise ValueError(
                "There is no listed option in that direction. Would you like a fresh search?"
            )
        return str(index + 1)
    category = re.fullmatch(r"the (.+)", bare)
    if (
        category
        and rows
        and not re.search(r"option|service|first|second|third|last", bare)
    ):
        clock = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?: one)?", category[1])
        if clock:
            hour = int(clock[1]) % 12 + (12 if clock[3] == "pm" else 0)
            matches = [
                i
                for i, r in enumerate(rows)
                if datetime.fromisoformat(r.get("departure_at") or r["departure"])
                .time()
                .replace(second=0, microsecond=0)
                .hour
                == hour
                and datetime.fromisoformat(
                    r.get("departure_at") or r["departure"]
                ).minute
                == int(clock[2] or 0)
            ]
        else:
            matches = []
            for i, row in enumerate(rows):
                ids = [leg["service_id"] for leg in row.get("legs", [])] or [
                    row.get("service_id")
                ]
                categories = [
                    session.get(
                        Category, session.get(Service, sid).category_id
                    ).name.casefold()
                    for sid in ids
                    if sid and session.get(Service, sid)
                ]
                if categories and all(name == category[1] for name in categories):
                    matches.append(i)
            if not matches:
                return text
        if len(matches) != 1:
            raise ValueError(
                "Which listed departure do you mean? Several or no options match that reference."
            )
        return str(matches[0] + 1)
    return text


def compare_current(engine, text, state, now):
    """Revalidate compatible displayed segments before deriving comparison facts."""
    import re
    from copy import deepcopy
    from datetime import datetime

    candidates = state.get("candidates", [])
    if len(candidates) < 2:
        raise ValueError("Please search for at least two current options to compare.")
    selected_index = next(
        (
            i
            for i, r in enumerate(candidates)
            if r.get("result_id") == state.get("selected_result_id")
        ),
        None,
    )
    if "compare with the first" in text:
        if selected_index is None:
            raise ValueError("Which option should I compare with the first one?")
        indexes = list(dict.fromkeys([selected_index, 0]))
    elif (
        "first" in text
        and "second" in text
        or "the two" in text
        or text.strip(".!? ") == "both"
    ):
        if len(candidates) != 2 and "first" not in text:
            raise ValueError("Which two options do you mean? Give their numbers.")
        indexes = [0, 1]
    else:
        indexes = list(range(len(candidates)))
    if "how much more is" in text:
        from ..domain import Category, Service

        target = []
        for i, row in enumerate(candidates):
            ids = [leg["service_id"] for leg in row.get("legs", [])] or [
                row.get("service_id")
            ]
            if any(
                session_category and session_category.name.casefold() in text
                for sid in ids
                if sid
                for service in [engine.session.get(Service, sid)]
                if service
                for session_category in [
                    engine.session.get(Category, service.category_id)
                ]
            ):
                target.append(i)
        if selected_index is None or len(target) != 1:
            raise ValueError(
                "Compared with which selected option? Select a bus, then name the category to compare."
            )
        indexes = list(dict.fromkeys([selected_index, target[0]]))
    if len(indexes) < 2:
        raise ValueError(
            "That is the same option. Which other number should I compare?"
        )
    facts = []
    compatible = set()
    for i in indexes:
        candidate = candidates[i]
        temp = {
            "selected_result": deepcopy(candidate),
            "travel_date": state.get("travel_date"),
        }
        if candidate.get("journey_id"):
            temp["selected_itinerary"] = deepcopy(candidate)
        rows = selected_rows(engine, temp, now)
        departure = datetime.fromisoformat(rows[0]["departure"])
        arrival = datetime.fromisoformat(rows[-1]["arrival"])
        compatible.add(
            (rows[0]["origin_id"], rows[-1]["destination_id"], departure.date())
        )
        fares = [Decimal(r["fare"]) for r in rows if r.get("fare") is not None]
        amenity = selected_enquiry(engine, "BUS_AMENITIES", temp, now)
        ac_values = [r.get("ac") for r in amenity["results"]]
        facts.append(
            {
                "option": i + 1,
                "result_id": candidate["result_id"],
                "service_ids": [r["service_id"] for r in rows],
                "service_numbers": [r.get("service_number") for r in rows],
                "origin_id": rows[0]["origin_id"],
                "destination_id": rows[-1]["destination_id"],
                "boarding_date": departure.date().isoformat(),
                "departure": departure.isoformat(),
                "arrival": arrival.isoformat(),
                "arrival_kind": rows[-1].get("arrival_kind", "scheduled"),
                "departure_kind": rows[0].get("departure_kind", "scheduled"),
                "duration_minutes": int((arrival - departure).total_seconds() / 60),
                "fare": str(sum(fares, Decimal(0)))
                if len(fares) == len(rows)
                else None,
                "ac": False
                if False in ac_values
                else True
                if ac_values and all(v is True for v in ac_values)
                else None,
                "sources": sorted({r.get("dataset_source", "LOCAL") for r in rows}),
            }
        )
    if len(compatible) != 1:
        raise ValueError(
            "These options have different travel segments or boarding dates. Search one route and date before comparing."
        )
    metric = (
        "fare"
        if re.search(r"cheap|much more", text)
        else "duration_minutes"
        if "faster" in text or "fastest" in text
        else "ac"
        if "has ac" in text
        else "arrival"
        if re.search(r"arriv|before", text)
        else "all"
    )
    winners = []
    deadline = re.search(r"before (\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if deadline:
        hour = int(deadline[1]) % 12 + (12 if deadline[3] == "pm" else 0)
        cutoff = datetime.fromisoformat(facts[0]["departure"]).replace(
            hour=hour, minute=int(deadline[2] or 0), second=0, microsecond=0
        )
        eligible = [f for f in facts if datetime.fromisoformat(f["arrival"]) < cutoff]
        winners = [f["option"] for f in eligible]
        reason = (
            "Options meeting the recorded arrival deadline: "
            + (", ".join(map(str, winners)) or "none")
            + "."
        )
    elif metric in {"fare", "duration_minutes", "arrival"}:
        known = [f for f in facts if f[metric] is not None]
        value = lambda f: Decimal(f[metric]) if metric == "fare" else f[metric]
        if known:
            best = min(value(f) for f in known)
            winners = [f["option"] for f in known if value(f) == best]
        reason = (
            "Among options with known fares, "
            if metric == "fare"
            else "Using recorded " + metric.replace("_", " ") + ", "
        ) + (
            "option(s) " + ", ".join(map(str, winners)) + " rank first."
            if winners
            else "the comparison is unavailable."
        )
        if len(known) != len(facts):
            reason += (
                " Unknown fares are excluded; no overall cheapest claim can be made."
            )
    elif metric == "ac":
        winners = [f["option"] for f in facts if f["ac"] is True]
        reason = (
            "Recorded AC options: "
            + (", ".join(map(str, winners)) or "none confirmed")
            + ". Unknown vehicle attributes stay unconfirmed."
        )
    else:
        reason = "Here are the current recorded fares, scheduled times and vehicle attributes. No overall best option is assumed."
    lines = [reason]
    for f in facts:
        lines.append(
            f"Option {f['option']}: fare "
            + ("INR " + f["fare"] if f["fare"] is not None else "unknown")
            + f"; {f['duration_minutes']} minutes; {f['arrival_kind']} arrival "
            + datetime.fromisoformat(f["arrival"]).strftime("%d %b %I:%M %p")
            + "; AC "
            + ("yes" if f["ac"] is True else "no" if f["ac"] is False else "unknown")
            + "."
        )
    if (
        "much more" in text
        and len(facts) == 2
        and all(f["fare"] is not None for f in facts)
    ):
        lines.append(
            "The recorded fare difference is INR "
            + str(abs(Decimal(facts[0]["fare"]) - Decimal(facts[1]["fare"])))
            + "."
        )
    return {
        "intent": "CONTEXT_COMPARISON",
        "status": "KNOWN",
        "query": {"metric": metric, "result_ids": [f["result_id"] for f in facts]},
        "results": facts,
        "warnings": [],
        "executor": "ConversationQueryPlanner.compare_current",
        "answer_text": "\n".join(lines),
        "winners": winners,
    }
