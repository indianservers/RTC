"""Explicit DEMO-only live acceptance. Uses authorized APIs, never direct DB writes."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx


def run():
    root = {"Authorization": "Bearer " + os.environ["RTC_ADMIN_TOKEN"]}
    tag = uuid4().hex[:8]
    report = {"dataset": "DEMO", "application": "http://127.0.0.1:8000", "checks": {}}
    users = []
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1", trust_env=False, timeout=180
    ) as client:

        def call(method, path, body=None, headers=root):
            response = client.request(method, path, json=body, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get("data", result)

        try:
            boot = call("GET", "/app/bootstrap")
            op = next(o for o in boot["operators"] if o["code"] == "DEMO")
            origin = call("GET", "/stations/resolve?value=Vijayawada")["candidates"][0]
            destination = call("GET", "/stations/resolve?value=Nellore")["candidates"][
                0
            ]
            category = next(
                c for c in boot["categories"] if c["operator_id"] == op["id"]
            )

            def provision(role, global_scope=False):
                user = call(
                    "POST",
                    "/admin/data/users",
                    {
                        "username": f"demo-5b-{role.lower()}-{tag}",
                        "role": role,
                        "operator_ids": [] if global_scope else [op["id"]],
                        "station_ids": [origin["id"]]
                        if role in {"DISPATCHER", "STATION_SUPERVISOR"}
                        else [],
                        "global_scope": global_scope,
                    },
                )
                users.append(user["id"])
                return {"Authorization": "Bearer " + user["token"]}

            approver = provision("APPROVER", True)
            dispatcher = provision("DISPATCHER")
            supervisor = provision("STATION_SUPERVISOR")
            ids = {
                k: str(uuid4())
                for k in (
                    "source",
                    "bay1",
                    "bay2",
                    "route",
                    "stop1",
                    "stop2",
                    "service",
                )
            }
            departure = datetime.now(ZoneInfo(origin["timezone"])) + timedelta(hours=1)
            day = departure.date()
            number = "DEMO-5B-" + str(int(tag, 16) % 1000000)
            commands = [
                {
                    "resource": "data-sources",
                    "id": ids["source"],
                    "values": {
                        "code": "DEMO-5B-" + tag,
                        "name": "DEMO dispatcher acceptance source",
                        "operator_id": op["id"],
                        "is_demo": True,
                        "is_official": False,
                        "dataset_source": "DEMO",
                    },
                },
                *(
                    {
                        "resource": "bays",
                        "id": ids[k],
                        "values": {
                            "station_id": origin["id"],
                            "code": f"DEMO-5B-{n}-{tag}",
                            "bay_name": "FICTIONAL test bay",
                            "dataset_source": "DEMO",
                        },
                    }
                    for n, k in ((1, "bay1"), (2, "bay2"))
                ),
                {
                    "resource": "routes",
                    "id": ids["route"],
                    "values": {
                        "code": "DEMO-5B-" + tag,
                        "operator_id": op["id"],
                        "origin_station_id": origin["id"],
                        "destination_station_id": destination["id"],
                        "dataset_source": "DEMO",
                    },
                },
                {
                    "resource": "stops",
                    "id": ids["stop1"],
                    "values": {
                        "route_id": ids["route"],
                        "station_id": origin["id"],
                        "sequence": 0,
                        "offset_minutes": 0,
                        "distance_km": "0",
                        "boarding": True,
                        "alighting": True,
                        "dataset_source": "DEMO",
                    },
                },
                {
                    "resource": "stops",
                    "id": ids["stop2"],
                    "values": {
                        "route_id": ids["route"],
                        "station_id": destination["id"],
                        "sequence": 1,
                        "offset_minutes": 180,
                        "distance_km": "250",
                        "boarding": True,
                        "alighting": True,
                        "dataset_source": "DEMO",
                    },
                },
                {
                    "resource": "schedules",
                    "id": ids["service"],
                    "values": {
                        "number": number,
                        "operator_id": op["id"],
                        "category_id": category["id"],
                        "route_id": ids["route"],
                        "departure_minutes": departure.hour * 60 + departure.minute,
                        "valid_from": day.isoformat(),
                        "valid_to": day.isoformat(),
                        "weekdays": "0123456",
                        "dataset_source": "DEMO",
                    },
                },
            ]
            batch = call(
                "POST",
                "/admin/data/changes",
                {
                    "commands": commands,
                    "operator_id": op["id"],
                    "reason": "Explicit fictional Phase 5B acceptance fixture; never official RTC data",
                },
            )
            for verb, headers in (
                ("validate", root),
                ("approve", approver),
                ("publish", root),
            ):
                batch = call(
                    "POST",
                    f"/admin/imports/batches/{batch['id']}/{verb}",
                    {"revision": batch["revision"]},
                    headers,
                )
                assert not (batch.get("validation_report") or {}).get("errors"), batch
            report.update(
                service_number=number,
                service_id=ids["service"],
                station=origin["name"],
                station_id=origin["id"],
                source_id=ids["source"],
                master_batch_id=batch["id"],
            )
            trip = call(
                "POST",
                "/operations/trips",
                {
                    "service_id": ids["service"],
                    "service_date": day.isoformat(),
                    "station_id": origin["id"],
                    "source_id": ids["source"],
                },
                dispatcher,
            )
            report["trip_id"] = trip["id"]
            version = trip["operational_version"]

            def event(kind, details=None, headers=dispatcher):
                nonlocal version
                r = call(
                    "POST",
                    f"/operations/trips/{trip['id']}/events",
                    {
                        "event_type": kind,
                        "station_id": origin["id"],
                        "source_id": ids["source"],
                        "expected_version": version,
                        "idempotency_key": str(uuid4()),
                        "occurred_at": datetime.now(UTC).isoformat(),
                        "expires_at": (
                            datetime.now(UTC) + timedelta(hours=4)
                        ).isoformat(),
                        "reason": "DEMO acceptance observation; not official transport information",
                        "details": details or {},
                    },
                    headers,
                )
                version = r["version"]
                return r

            event("DELAYED", {"delay_minutes": 15})
            event("PLATFORM", {"bay_id": ids["bay1"]})
            event("PLATFORM", {"bay_id": ids["bay2"]})
            query = {
                "intent": "BUS_DELAY",
                "trip_id": trip["id"],
                "service_id": ids["service"],
                "station": origin["id"],
                "origin": origin["id"],
                "travel_date": day.isoformat(),
                "at": datetime.now(UTC).isoformat(),
            }
            delayed = call("POST", "/enquiry", query)["results"][0]
            report["checks"]["delay_and_revised_departure"] = delayed[
                "delay_minutes"
            ] == 15 and bool(delayed["estimated_departure"])
            report["checks"]["latest_platform"] = (
                delayed["platform"]["bay"] == f"DEMO-5B-2-{tag}"
            )
            platform_reply = call(
                "POST",
                "/conversation/message",
                {
                    "text": f"Which platform for service {number}?",
                    "language": "en",
                    "station_context": origin["id"],
                },
            )
            report["checks"]["nlp_latest_platform"] = (
                f"DEMO-5B-2-{tag}" in platform_reply["answer"]
            )
            before = call(
                "POST",
                "/enquiry",
                {
                    **query,
                    "intent": "BUS_DEPARTED_STATUS",
                    "at": datetime.now(UTC).isoformat(),
                },
            )
            report["checks"]["no_false_actual_departure"] = not before["results"]
            nlp = call(
                "POST",
                "/conversation/message",
                {
                    "text": f"Is service {number} delayed?",
                    "language": "en",
                    "station_context": origin["id"],
                },
            )
            report["delay_nlp"] = {"intents": nlp["intents"], "answer": nlp["answer"]}
            report["checks"]["nlp_delay"] = (
                "BUS_DELAY" in nlp["intents"] and "15" in nlp["answer"]
            )
            event("BOARDING", {"bay_id": ids["bay2"]})
            event("DEPARTED_FROM_STOP")
            after = call(
                "POST",
                "/enquiry",
                {
                    **query,
                    "intent": "BUS_DEPARTED_STATUS",
                    "at": datetime.now(UTC).isoformat(),
                },
            )
            report["checks"]["actual_departure_visible"] = bool(
                after["results"][0]["actual_departure"]
            )
            nlp = call(
                "POST",
                "/conversation/message",
                {
                    "text": f"Has service {number} departed?",
                    "language": "en",
                    "station_context": origin["id"],
                },
            )
            report["departure_nlp"] = {
                "intents": nlp["intents"],
                "answer": nlp["answer"],
            }
            report["checks"]["nlp_departure"] = "recorded as departed" in nlp["answer"]
            requested = event("ANNOUNCEMENT_REQUEST")
            event(
                "PUBLISH_ANNOUNCEMENT",
                {"target_event_id": requested["idempotency_key"]},
                supervisor,
            )
            history = call(
                "GET",
                f"/operations/events?station_id={origin['id']}&operator_id={op['id']}&trip_id={trip['id']}",
            )
            report["events"] = [
                {
                    "id": e["id"],
                    "operation": e["operation"],
                    "version": e["version"],
                    "actor": e["actor"],
                    "source_id": e["source_id"],
                    "occurred_at": e["occurred_at"],
                    "recorded_at": e["recorded_at"],
                    "dataset_source": e["dataset_source"],
                }
                for e in history
            ]
            report["checks"]["every_event_has_actor_timestamp_source"] = all(
                e["actor"]
                and e["source_id"]
                and e["occurred_at"]
                and e["recorded_at"]
                and e["dataset_source"] == "DEMO"
                for e in history
            )
            assert all(report["checks"].values()), report
        finally:
            for user in users:
                call("DELETE", f"/admin/data/users/{user}")
            report["temporary_capabilities_revoked"] = True
            path = Path(__file__).resolve().parents[1] / os.getenv(
                "RTC_LIVE_REPORT_PATH", "docs/phase5b-live-acceptance.json"
            )
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
