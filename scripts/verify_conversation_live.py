"""Publish fictional conversation fixtures through the existing approval workflow.
Run explicitly against the local production app; all created transport data is DEMO.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx


def run():
    root = {"Authorization": "Bearer " + os.environ["RTC_ADMIN_TOKEN"]}
    tag = uuid4().hex[:8]
    report = {"dataset": "DEMO", "base_url": os.getenv("RTC_BASE_URL", "http://127.0.0.1:8000"), "turns": []}
    with httpx.Client(
        base_url=report["base_url"] + "/api/v1", trust_env=False, timeout=120
    ) as client:

        def call(method, path, body=None, headers=root):
            response = client.request(method, path, json=body, headers=headers)
            if response.is_error:
                raise RuntimeError(
                    f"{method} {path}: {response.status_code} {response.text}"
                )
            value = response.json()
            return value.get("data", value)

        boot = call("GET", "/app/bootstrap")
        op = next(o for o in boot["operators"] if o["code"] == "DEMO")
        stations = {
            name: call("GET", "/stations/resolve?value=" + name)["candidates"][0]
            for name in ("Vijayawada", "Ongole", "Nellore")
        }
        category = next(c for c in boot["categories"] if c["operator_id"] == op["id"])
        reuse = os.getenv("RTC_REUSE_CONVERSATION_FIXTURE") == "1"
        approver = (
            None
            if reuse
            else call(
                "POST",
                "/admin/data/users",
                {
                    "username": "demo-conversation-approver-" + tag,
                    "role": "APPROVER",
                    "global_scope": True,
                    "operator_ids": [],
                    "station_ids": [],
                },
            )
        )
        try:
            if reuse:
                saved = json.loads(
                    Path("docs/conversation-upgrade-live.json").read_text(
                        encoding="utf-8"
                    )
                )
                services = saved["service_ids"]
                report.update(
                    master_batch_id=saved["master_batch_id"],
                    service_ids=services,
                    fixture_reused=True,
                )
            else:
                now = datetime.now(ZoneInfo("Asia/Kolkata"))
                departure = now + timedelta(minutes=45)
                start = now.date().isoformat()
                end = (now + timedelta(days=30)).date().isoformat()
                route = str(uuid4())
                kind = str(uuid4())
                layout = str(uuid4())
                commands = []

                def add(resource, identifier, **values):
                    commands.append(
                        {
                            "resource": resource,
                            "id": identifier,
                            "values": {**values, "dataset_source": "DEMO"},
                        }
                    )

                add(
                    "routes",
                    route,
                    code="DEMO-CONVERSATION-" + tag,
                    operator_id=op["id"],
                    origin_station_id=stations["Vijayawada"]["id"],
                    destination_station_id=stations["Nellore"]["id"],
                )
                for index, name in enumerate(stations):
                    add(
                        "stops",
                        str(uuid4()),
                        route_id=route,
                        station_id=stations[name]["id"],
                        sequence=index,
                        offset_minutes=index * 60,
                        distance_km=str(index * 60),
                        boarding=True,
                        alighting=True,
                    )
                add(
                    "vehicle-types",
                    kind,
                    name="DEMO conversation AC seater " + tag,
                    ac=True,
                    sleeper=False,
                )
                add(
                    "seat-layouts",
                    layout,
                    name="DEMO conversation layout " + tag,
                    seating_capacity=40,
                    berth_capacity=0,
                )
                services = []
                for index, amount in enumerate((101, 205, None)):
                    service = str(uuid4())
                    vehicle = str(uuid4())
                    services.append(service)
                    at = departure + timedelta(minutes=index * 10)
                    add(
                        "schedules",
                        service,
                        number=f"DEMO-CONV-{tag}-{index + 1}",
                        operator_id=op["id"],
                        category_id=category["id"],
                        route_id=route,
                        departure_minutes=at.hour * 60 + at.minute,
                        valid_from=start,
                        valid_to=end,
                        weekdays="0123456",
                    )
                    add(
                        "vehicles",
                        vehicle,
                        operator_id=op["id"],
                        type_id=kind,
                        layout_id=layout,
                        registration=f"DEMO-CONV-{tag}-{index + 1}",
                    )
                    add(
                        "vehicle-assignments",
                        str(uuid4()),
                        service_id=service,
                        vehicle_id=vehicle,
                    )
                    if amount is not None:
                        add(
                            "fares",
                            str(uuid4()),
                            service_id=service,
                            origin_id=stations["Vijayawada"]["id"],
                            destination_id=stations["Nellore"]["id"],
                            amount=str(amount),
                            valid_from=start,
                            valid_to=end,
                        )
                batch = call(
                    "POST",
                    "/admin/data/changes",
                    {
                        "commands": commands,
                        "operator_id": op["id"],
                        "reason": "Explicit fictional conversation acceptance fixture; never official RTC data",
                    },
                )
                for verb, headers in (
                    ("validate", root),
                    ("approve", {"Authorization": "Bearer " + approver["token"]}),
                    ("publish", root),
                ):
                    batch = call(
                        "POST",
                        f"/admin/imports/batches/{batch['id']}/{verb}",
                        {"revision": batch["revision"]},
                        headers,
                    )
                    assert not (batch.get("validation_report") or {}).get("errors"), (
                        batch
                    )
                report.update(master_batch_id=batch["id"], service_ids=services)
            previous = None
            owner = uuid4().hex + uuid4().hex
            for question in (
                "Next bus to Nellore?",
                "2",
                "What is the fare?",
                "Is it AC?",
                "Does it stop at Ongole?",
                "What about tomorrow?",
                "Cheapest option?",
                "No, I meant Tirupati.",
            ):
                body = {
                    "text": question,
                    "language": "en",
                    "station_context": stations["Vijayawada"]["id"],
                    "owner_token": owner,
                    "client_message_id": str(uuid4()),
                    "expected_state_version": previous["context"]["state_version"]
                    if previous
                    else 0,
                    "debug": True,
                }
                if previous:
                    body["session_id"] = previous["session_id"]
                answer = call("POST", "/conversation/message", body)
                if previous:
                    assert answer["session_id"] == previous["session_id"]
                if question == "2":
                    chosen = answer["selected_journey"]
                    assert chosen["service_id"] == services[1]
                if question == "What is the fare?":
                    assert (
                        answer["results"][0]["query"]["service_id"]
                        == chosen["service_id"]
                    )
                    assert float(answer["results"][0]["results"][0]["amount"]) == 205
                if question == "Is it AC?":
                    assert answer["results"][0]["results"][0]["ac"] is True
                if question == "Does it stop at Ongole?":
                    assert "Yes" in answer["answer"]
                if question == "What about tomorrow?":
                    assert not answer["selected_journey"]
                if question == "No, I meant Tirupati.":
                    assert (
                        answer["context"]["destination"] != stations["Nellore"]["id"]
                        and not answer["selected_journey"]
                    )
                if question in (
                    "Next bus to Nellore?",
                    "2",
                    "What is the fare?",
                    "Is it AC?",
                    "Does it stop at Ongole?",
                ):
                    assert "DEMO" in answer["data_source"]
                report["turns"].append({"question": question, "response": answer})
                previous = answer
            report["passed"] = True
        finally:
            if approver:
                call("DELETE", "/admin/data/users/" + approver["id"])
    Path(
        os.getenv("RTC_LIVE_REPORT_PATH", "docs/conversation-upgrade-live.json")
    ).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "turns": len(report["turns"]),
                "master_batch_id": report["master_batch_id"],
            }
        )
    )


if __name__ == "__main__":
    run()
