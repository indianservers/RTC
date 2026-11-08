"""Offline startup and multi-turn API smoke against a private SQLite snapshot.
No live DB writes; deny all socket egress and DNS before importing the backend.
"""

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

from offline_guard import enforce_offline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def run(
    database_path=ROOT / "rtc.db",
    first_query="Next bus to Nellore?",
    report_path=ROOT / "docs/conversation-upgrade-offline.json",
    phase5c=False,
):
    with TemporaryDirectory(prefix="rtc-offline-conversation-") as folder:
        snapshot = Path(folder) / "offline.db"
        with (
            sqlite3.connect(database_path) as source,
            sqlite3.connect(snapshot) as target,
        ):
            source.backup(target)
        source.close()
        target.close()
        os.environ["DATABASE_URL"] = "sqlite:///" + snapshot.as_posix()
        # Windows asyncio creates a loopback socket pair for its wake-up pipe.
        # Create that test-harness loop before enforcing the deny-all guard;
        # backend import, startup and all API requests remain inside the guard.
        event_loop = asyncio.new_event_loop()
        enforce_offline()
        start = perf_counter()
        from alembic import command
        from alembic.config import Config

        config = Config(str(ROOT / "alembic.ini"))
        command.upgrade(config, "head")
        from app.main import app, engine
        from fastapi.testclient import TestClient

        startup_ms = (perf_counter() - start) * 1000
        previous = None
        owner = uuid4().hex + uuid4().hex
        report = {
            "network": "ALL_SOCKET_EGRESS_AND_DNS_BLOCKED_BEFORE_BACKEND_IMPORT",
            "database": "PRIVATE_SQLITE_SNAPSHOT",
            "startup_and_migrations_ms": startup_ms,
            "turns": [],
        }
        with TestClient(
            app,
            client=("offline-conversation-smoke", 50000),
            backend_options={"loop_factory": lambda: event_loop},
        ) as client:
            assert client.get("/api/v1/nlp/health").status_code == 200
            questions = (
                (
                    first_query,
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
                if phase5c
                else (
                    first_query,
                    "2",
                    "What is the fare?",
                    "Is it AC?",
                    "Does it stop at Ongole?",
                    "What about tomorrow?",
                    "Cheapest option?",
                    "No, I meant Tirupati.",
                )
            )
            for question in questions:
                body = {
                    "text": question,
                    "language": "en",
                    "station_context": "Vijayawada",
                    "owner_token": owner,
                    "client_message_id": str(uuid4()),
                    "expected_state_version": previous["context"]["state_version"]
                    if previous
                    else 0,
                }
                if previous:
                    body["session_id"] = previous["session_id"]
                response = client.post("/api/v1/conversation/message", json=body)
                assert response.status_code == 200, response.text
                data = response.json()
                if previous:
                    assert data["session_id"] == previous["session_id"]
                if question in {"2", "Second one."}:
                    selected = data["selected_journey"]
                    assert selected
                if question in {"What is the fare?", "How much?"}:
                    assert (
                        data["results"][0]["query"]["service_id"]
                        == selected["service_id"]
                    )
                    amount = data["results"][0]["results"][0]["amount"]
                    assert (amount is None and selected["fare"] is None) or float(
                        amount
                    ) == float(selected["fare"])
                report["turns"].append(
                    {
                        "question": question,
                        "duration_ms": data["duration_ms"],
                        "state": data["state"],
                        "selected_service": data["context"].get("service_id"),
                        "data_source": data["data_source"],
                    }
                )
                previous = data
        engine.dispose()
        with sqlite3.connect(snapshot) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert not db.execute("PRAGMA foreign_key_check").fetchall()
        db.close()
        report["passed"] = True
        Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase5c", action="store_true")
    parser.add_argument("--database", type=Path, default=ROOT / "rtc.db")
    parser.add_argument("--first-query", default="Next bus to Nellore?")
    parser.add_argument(
        "--report", type=Path, default=ROOT / "docs/conversation-upgrade-offline.json"
    )
    args = parser.parse_args()
    run(args.database, args.first_query, args.report, args.phase5c)
