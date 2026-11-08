"""DEMO-only repair/feedback/review acceptance. Offline mode uses a private DB copy."""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def exercise(client, token, first_query):
    root_headers = {"Authorization": "Bearer " + token}
    owner = uuid4().hex + uuid4().hex
    report = {
        "dataset": "LABELLED DEMO",
        "model_promoted": False,
        "automatic_training": False,
        "turns": [],
    }
    previous = None

    def call(method, path, body=None, headers=None):
        response = client.request(method, path, json=body, headers=headers or {})
        assert response.status_code < 400, (path, response.status_code, response.text)
        value = response.json()
        return value.get("data", value)

    def ask(question):
        nonlocal previous
        started = perf_counter()
        body = {
            "text": question,
            "station_context": "Vijayawada",
            "language": "en",
            "owner_token": owner,
            "client_message_id": str(uuid4()),
            "expected_state_version": previous["context"]["state_version"]
            if previous
            else 0,
        }
        if previous:
            body["session_id"] = previous["session_id"]
        data = call("POST", "/api/v1/conversation/message", body)
        if previous:
            assert data["session_id"] == previous["session_id"]
        report["turns"].append(
            {
                "question": question,
                "response": data,
                "request_ms": (perf_counter() - started) * 1000,
            }
        )
        previous = data
        return data

    first = ask(first_query)
    assert first["result_set"]
    last = ask("No, I meant the last bus.")
    assert (
        last["intents"] == ["LAST_BUS"]
        and last["context"]["destination"] == first["context"]["destination"]
    )
    selected = ask("1")
    assert selected["selected_journey"]
    fare = ask("What is the fare?")
    assert (
        fare["results"][0]["query"]["service_id"] == selected["context"]["service_id"]
    )
    actual = fare["results"][0]["results"][0]["amount"]
    expected = selected["selected_journey"]["fare"]
    assert (actual is None and expected is None) or float(actual) == float(expected)
    wrong = ask("That's the wrong bus.")
    assert wrong["requires_clarification"] and not wrong["selected_journey"]
    fresh = ask("Next bus")
    assert len(fresh["result_set"]) >= 2
    correct = ask("2")
    assert (
        correct["selected_journey"]["service_id"]
        == fresh["result_set"][1]["service_id"]
    )
    platform = ask("Which platform?")
    assert (
        platform["results"][0]["query"]["service_id"]
        == correct["context"]["service_id"]
    )
    started = perf_counter()
    saved = call(
        "POST",
        "/api/v1/conversation/feedback",
        {
            "session_id": platform["session_id"],
            "message_id": platform["message_id"],
            "owner_token": owner,
            "category": "WRONG_BUS",
            "retain_question": True,
        },
    )
    report["feedback_write_ms"] = (perf_counter() - started) * 1000
    assert saved["saved"] and saved.get("text_retained"), saved
    rows = call("GET", "/api/v1/admin/nlp/reviews?limit=200", headers=root_headers)
    item = next(r for r in rows if r["id"] == saved["id"])
    operator = item["operator_id"]
    assert operator
    user = call(
        "POST",
        "/api/v1/admin/data/users",
        {
            "username": "demo-5d-reviewer-" + uuid4().hex[:8],
            "role": "APPROVER",
            "operator_ids": [operator],
        },
        root_headers,
    )
    try:
        reviewed = call(
            "POST",
            f"/api/v1/admin/nlp/reviews/{item['id']}/review",
            {
                "expected_version": item["version"],
                "status": "APPROVED_FOR_TRAINING",
                "error_group": "CONTEXT_ERROR",
                "error_category": "AMBIGUOUS_REFERENCE",
                "corrected_intent": "BUS_PLATFORM",
                "notes": "Automated DEMO acceptance label, not independent human review. Valid only as workflow verification; no production model approval.",
                "example_kind": "CONTEXTUAL",
                "label_provenance": "AUTOMATED_DEMO_ACCEPTANCE",
                "independent": False,
            },
            {"Authorization": "Bearer " + user["token"]},
        )
        assert reviewed["training_eligible"]
        exported = client.get("/api/v1/admin/nlp/export", headers=root_headers)
        assert exported.status_code == 200
        examples = [json.loads(line) for line in exported.text.splitlines()]
        example = next(r for r in examples if r["example_id"] == item["id"])
        assert (
            example["intent"] == "BUS_PLATFORM"
            and example["label_provenance"] == "AUTOMATED_DEMO_ACCEPTANCE"
        )
        assert owner not in exported.text and platform["session_id"] not in json.dumps(
            example
        )
        report.update(
            feedback_id=item["id"],
            approved_example=example,
            model_promotion_eligible=False,
        )
    finally:
        call("DELETE", "/api/v1/admin/data/users/" + user["id"], headers=root_headers)
    no_results = ask("Under 1")
    assert (
        no_results["state"] == "NO_RESULTS" and no_results["reliability"]["diagnosis"]
    )
    report["diagnostic_probe_ms"] = no_results["reliability"]["diagnostic_ms"]
    uncertainty = ask("First or next bus?")
    assert (
        uncertainty["requires_clarification"]
        and len(uncertainty["clarification_choices"]) == 2
    )
    report["clarification_ms"] = uncertainty["duration_ms"]
    report["repair_detection_ms"] = last["reliability"]["repair_detection_ms"]
    report["passed"] = True
    return report


def run(offline=False):
    if offline:
        with TemporaryDirectory(prefix="rtc-5d-offline-") as folder:
            snapshot = Path(folder) / "smoke.db"
            source = sqlite3.connect(ROOT / "rtc.db")
            target = sqlite3.connect(snapshot)
            source.backup(target)
            source.close()
            target.close()
            os.environ["DATABASE_URL"] = "sqlite:///" + snapshot.as_posix()
            token = uuid4().hex + uuid4().hex
            os.environ["RTC_ADMIN_TOKEN"] = token
            os.environ["RTC_FEEDBACK_RETAIN_TEXT"] = "1"
            os.environ["RTC_REQUEST_LOG"] = str(
                ROOT / f"data/runtime/offline-phase5d-{os.getpid()}.jsonl"
            )
            event_loop = asyncio.new_event_loop()
            from offline_guard import enforce_offline

            enforce_offline()
            sys.path.insert(0, str(ROOT / "backend"))
            from app.main import app, engine
            from fastapi.testclient import TestClient

            try:
                with TestClient(
                    app,
                    client=("offline-phase5d", 50000),
                    backend_options={"loop_factory": lambda: event_loop},
                ) as client:
                    report = exercise(client, token, "Next bus to Nellore tomorrow?")
            finally:
                engine.dispose()
            with sqlite3.connect(snapshot) as db:
                assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert not db.execute("PRAGMA foreign_key_check").fetchall()
            db.close()
            report["network"] = (
                "ALL_SOCKET_EGRESS_AND_DNS_BLOCKED_BEFORE_BACKEND_IMPORT"
            )
    else:
        import httpx

        with httpx.Client(
            base_url="http://127.0.0.1:8000", trust_env=False, timeout=90
        ) as client:
            report = exercise(
                client, os.environ["RTC_ADMIN_TOKEN"], "Next bus to Nellore?"
            )
        report["network"] = "LOCAL_APP_LOOPBACK"
    path = ROOT / ("docs/phase5d-offline.json" if offline else "docs/phase5d-live.json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "conversation_turns": len(report["turns"]),
                "feedback_write_ms": report["feedback_write_ms"],
                "network": report["network"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    run(parser.parse_args().offline)
