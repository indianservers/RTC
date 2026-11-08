"""Shadow candidate integration on private DB copy; no registry activation or live writes."""

import asyncio
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]


def main():
    loop = asyncio.new_event_loop()
    from offline_guard import enforce_offline

    enforce_offline()
    import joblib
    import numpy as np
    import tensorflow as tf
    from prepare_english_recovery import dump, normalize

    tf.config.threading.set_intra_op_parallelism_threads(4)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    candidates = {
        "grouped_svm": joblib.load(
            ROOT / "models/english/nlp/grouped-60-v1/svm.joblib"
        ),
        "new_svm": joblib.load(ROOT / "models/english/nlp/recovery-60-v3/svm.joblib"),
        "old_textcnn": tf.keras.models.load_model(
            ROOT / "models/english/nlp/grouped-60-v1/textcnn.keras"
        ),
        "new_textcnn": tf.keras.models.load_model(
            ROOT / "models/english/nlp/recovery-60-v3/textcnn.keras"
        ),
    }
    labels = json.loads(
        (ROOT / "models/english/nlp/recovery-60-v3/label_map.json").read_text()
    )
    with TemporaryDirectory(prefix="rtc-recovery-dialogue-") as tmp:
        db = Path(tmp) / "private.db"
        with (
            closing(sqlite3.connect(ROOT / "rtc.db")) as source,
            closing(sqlite3.connect(db)) as target,
        ):
            source.backup(target)
        os.environ.update(
            DATABASE_URL="sqlite:///" + db.as_posix(),
            RTC_MANAGED_RUNTIME="0",
            RTC_REQUESTS_PER_MINUTE="100000",
        )
        from app.main import app, engine
        from app.nlp.english_model import EnglishIntentModel
        from fastapi.testclient import TestClient

        original = EnglishIntentModel.predict
        reports = {}
        try:
            with TestClient(
                app, backend_options={"loop_factory": lambda: loop}
            ) as client:
                for name in ["deterministic_rules", *candidates]:
                    calls = []

                    def predict(self, text, name=name, calls=calls):
                        calls.append(text)
                        if name == "deterministic_rules":
                            return {"status": "NOT_READY", "intents": []}
                        model = candidates[name]
                        text = normalize(text)
                        if name == "new_svm":
                            return model.predict_selective([text])[0]
                        if name == "new_textcnn":
                            return {"status": "CLARIFICATION_REQUIRED", "intents": []}
                        code = (
                            labels[
                                int(
                                    np.argmax(
                                        model(
                                            tf.constant([text]), training=False
                                        ).numpy()[0]
                                    )
                                )
                            ]
                            if "textcnn" in name
                            else str(model.predict([text])[0])
                        )
                        return {
                            "status": "KNOWN",
                            "intents": [code],
                            "probability": None,
                            "version": "SHADOW_" + name,
                        }

                    EnglishIntentModel.predict = predict
                    owner = uuid4().hex + uuid4().hex
                    state = None
                    steps = []

                    def ask(text, owner=owner):
                        nonlocal state
                        request = {
                            "text": text,
                            "owner_token": owner,
                            "language": "en",
                            "station_context": "Vijayawada",
                        }
                        if state:
                            request["session_id"] = state["session_id"]
                        response = client.post(
                            "/api/v1/conversation/message", json=request
                        )
                        response.raise_for_status()
                        state = response.json()
                        return state

                    first = ask("Next bus to Nellore tomorrow?")
                    available = first.get("result_set", [])
                    steps.append(
                        {
                            "case": "database_departure_search",
                            "passed": len(available) >= 2,
                        }
                    )
                    if len(available) < 2:
                        reports[name] = {
                            "steps": steps,
                            "candidate_fallback_calls": len(calls),
                        }
                        continue
                    second = available[1]
                    selected = ask("Second one.")
                    steps.append(
                        {
                            "case": "Second one.",
                            "passed": selected["context"].get("service_id")
                            == second["service_id"],
                        }
                    )
                    fare = ask("How much?")
                    fare_rows = [
                        r
                        for section in fare["results"]
                        for r in section.get("results", [])
                    ]
                    actual = fare_rows[0].get("amount") if fare_rows else None
                    expected = second.get("fare")
                    correct_fare = (
                        Decimal(str(actual)) == Decimal(str(expected))
                        if expected is not None and actual is not None
                        else expected is None and actual is None
                    )
                    steps.append(
                        {
                            "case": "How much?",
                            "passed": correct_fare
                            and fare["context"].get("service_id")
                            == second["service_id"],
                            "expected_recorded_fare": expected,
                            "actual_fare": actual,
                        }
                    )
                    same = ask("Same bus.")
                    steps.append(
                        {
                            "case": "Same bus.",
                            "passed": same["context"].get("service_id")
                            == second["service_id"],
                        }
                    )
                    tomorrow = ask("What about tomorrow?")
                    steps.append(
                        {
                            "case": "What about tomorrow?",
                            "passed": tomorrow["context"].get("travel_date")
                            == (date.today() + timedelta(days=1)).isoformat(),
                        }
                    )
                    corrected = ask("No, Tirumala.")
                    steps.append(
                        {
                            "case": "No, Tirumala.",
                            "passed": corrected["context"].get("destination_name")
                            == "Tirumala"
                            and corrected["context"].get("service_id")
                            != second["service_id"],
                        }
                    )
                    # Deliberately non-template first question exercises statistical fallback separately.
                    state = None
                    shadow = ask(
                        "Pick the soonest coach I could still board to Nellore tomorrow."
                    )
                    steps.append(
                        {
                            "case": "shadow_paraphrase_next_bus",
                            "passed": bool(shadow.get("result_set"))
                            and shadow["context"].get("destination_name") == "Nellore",
                        }
                    )
                    reports[name] = {
                        "steps": steps,
                        "passed": sum(r["passed"] for r in steps),
                        "total": len(steps),
                        "candidate_fallback_calls": len(calls),
                        "fallback_was_exercised": bool(calls),
                        "context_resolution": "Shared actual conversation manager, not a forced single-label follow-up classifier",
                    }
        finally:
            EnglishIntentModel.predict = original
            engine.dispose()
            loop.close()
    dump(
        ROOT / "evaluation/english-recovery-v3/conversation.json",
        {
            "scope": "PRIVATE_DB_SOCKET_DENIED_SHADOW_INTEGRATION_NOT_PRODUCTION_APPROVAL",
            "models": reports,
        },
    )
    print(
        json.dumps(
            {
                name: {k: v for k, v in report.items() if k != "steps"}
                for name, report in reports.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
