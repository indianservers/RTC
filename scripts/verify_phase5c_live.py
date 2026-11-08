"""Read-only transport acceptance against the running local app; writes only chat state."""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = (
    "Next bus to Nellore?",
    "Second one.",
    "How much?",
    "Does it have AC?",
    "When will it arrive?",
    "Compare with the first one.",
    "What about tomorrow?",
    "Only Super Luxury.",
    "No, I meant Tirupati.",
    "Summarize my journey.",
)


def run():
    owner = uuid4().hex + uuid4().hex
    previous = None
    report = {
        "dataset": "EXISTING LABELLED DEMO",
        "transport_data_mutated": False,
        "turns": [],
    }
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1", trust_env=False, timeout=60
    ) as client:
        for question in QUESTIONS:
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
            response = client.post("/conversation/message", json=body)
            assert response.status_code == 200, response.text
            data = response.json()
            if previous:
                assert data["session_id"] == previous["session_id"]
            if question == "Next bus to Nellore?":
                options = data["result_set"]
                assert len(options) >= 2
            if question == "Second one.":
                chosen = data["selected_journey"]
                assert chosen["service_id"] == options[1]["service_id"]
            if question == "How much?":
                tool = data["results"][0]
                segment = tool["query"]["segments"][0]
                assert (
                    segment["service_id"] == chosen["service_id"]
                    and segment["origin"] == chosen["origin_id"]
                    and segment["destination"] == chosen["destination_id"]
                )
                actual = tool["results"][0]["amount"]
                assert (actual is None and chosen["fare"] is None) or float(
                    actual
                ) == float(chosen["fare"])
                check = client.post(
                    "/enquiry",
                    json={
                        "intent": "GET_FARE",
                        "origin": segment["origin"],
                        "destination": segment["destination"],
                        "service_id": segment["service_id"],
                        "travel_date": segment["service_date"],
                    },
                )
                assert check.status_code == 200
                values = [
                    r.get("amount", r.get("fare")) for r in check.json()["results"]
                ]
                assert any(
                    (v is None and actual is None)
                    or (
                        v is not None
                        and actual is not None
                        and float(v) == float(actual)
                    )
                    for v in values
                )
            if question == "Does it have AC?":
                with sqlite3.connect(
                    f"file:{(ROOT / 'rtc.db').as_posix()}?mode=ro", uri=True
                ) as db:
                    fact = db.execute(
                        "select t.ac from service_vehicles s join vehicles v on v.id=s.vehicle_id join vehicle_types t on t.id=v.type_id where s.service_id=? and s.active=1 and v.active=1 and t.active=1",
                        (chosen["service_id"],),
                    ).fetchone()
                db.close()
                expected = bool(fact[0]) if fact and fact[0] is not None else None
                assert data["results"][0]["results"][0]["ac"] == expected
            if question == "When will it arrive?":
                assert data["results"][0]["results"][0]["arrival"] == chosen["arrival"]
            if question == "Compare with the first one.":
                comparison = data["results"][0]
                assert comparison["query"]["result_ids"] == [
                    options[1]["result_id"],
                    options[0]["result_id"],
                ]
                assert data["selected_journey"]["service_id"] == chosen["service_id"]
                assert [r["fare"] for r in comparison["results"]] == [
                    options[1]["fare"],
                    options[0]["fare"],
                ]
            if question == "What about tomorrow?":
                assert data["selected_journey"] is None
            if question == "Only Super Luxury.":
                assert (
                    data["context"]["filters"].get("category")
                    or data["context"].get("unresolved_category") == "super luxury"
                )
            if question == "No, I meant Tirupati.":
                assert (
                    data["context"]["destination_name"] == "Tirupati"
                    and not data["selected_journey"]
                )
            if question == "Summarize my journey.":
                assert (
                    data["dialogue_act"] == "SUMMARY"
                    and data["context"]["destination_name"] == "Tirupati"
                    and not data["selected_journey"]
                )
            report["turns"].append({"question": question, "response": data})
            previous = data
    report["passed"] = True
    (ROOT / "docs/phase5c-live.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({"passed": True, "turns": len(report["turns"])}))


if __name__ == "__main__":
    run()
