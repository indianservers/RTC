"""Frozen deterministic operational playback; never real live positions."""
from copy import deepcopy
from .reference_engine import dt

KINDS = {"delayed", "arrived", "departed", "cancelled", "platform_changed", "gps_stale", "seats_updated", "diversion"}
def replay(state, events, until):
    result = deepcopy(state)
    log = []
    ids = set()
    for event in sorted(events, key=lambda e: (dt(e["at"]), e["id"])):
        if event["id"] in ids:
            raise ValueError("Duplicate event ID")
        ids.add(event["id"])
        if dt(event["at"]) > dt(until):
            continue
        if event["source_label"] != "SYNTHETIC" or event["kind"] not in KINDS:
            raise ValueError("Invalid simulation event")
        trip = next(t for t in result["trips"] if t["id"] == event["service_id"])
        kind, payload = event["kind"], event.get("payload", {})
        if kind == "delayed": trip["delay_minutes"] = payload["minutes"]
        elif kind == "cancelled": trip["cancelled"] = True
        elif kind == "platform_changed": trip["platform"] = payload["platform"]
        elif kind == "gps_stale": trip["gps_stale"] = True
        elif kind == "seats_updated": trip["seat_snapshot"] = {"available": payload["available"], "observed_at": event["at"], "source_label": "SYNTHETIC"}
        elif kind == "diversion": trip["diversion"] = payload["description"]
        else: trip["operational_status"] = kind
        trip["last_event_at"] = event["at"]
        log.append(deepcopy(event))
    return {"state": result, "event_log": log, "frozen_now": until, "source_label": "SYNTHETIC", "live_positions": False}
