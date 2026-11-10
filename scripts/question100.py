"""Ask 100 new questions, preserve expectations, and prepare candidate-only learning."""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from prepare_english_recovery import dump, normalize, rows, sha

DATA = ROOT / "training/datasets/question100-v1"
OUT = ROOT / "evaluation/question100-v1"
VERSION = "question100-v1"
PREVIOUS_VERSION = "recovery-60-v3"
BASE_DATA = ROOT / "training/datasets/recovery-60-v3"


def cases():
    from app.domain import Category, database
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    engine = database()
    try:
        with Session(engine) as session:
            categories = sorted(
                set(
                    session.scalars(
                        select(Category.name).where(Category.active.is_(True))
                    )
                )
            )
    finally:
        engine.dispose()
    if len(categories) < 2:
        raise ValueError(
            "Need two recorded active bus categories for the category-comparison case"
        )
    result = []
    for index, line in enumerate(
        (DATA / "questions.txt").read_text(encoding="utf-8").splitlines()
    ):
        target, kind, question = line.split("|", 2)
        question = question.replace("{category1}", categories[0]).replace(
            "{category2}", categories[-1]
        )
        result.append(
            {
                "id": f"Q{index + 1:03}"
                if VERSION == "question100-v1"
                else f"{VERSION}-Q{index + 1:03}",
                "question": question,
                "kind": kind,
                "expected": target.split(","),
                "human_reviewed": False,
                "source": "AGENT_AUTHORED_FOR_USER_REQUEST",
                "expectation_policy": "Labels/context specified before execution; facts must remain DB-grounded or explicitly unknown",
            }
        )
    assert len(result) == 100 and len({normalize(r["question"]) for r in result}) == 100
    if VERSION != "question100-v1":
        prior = set()
        for path in ROOT.glob("evaluation/question100-*/expected.json"):
            if path.parent != OUT:
                prior.update(
                    normalize(r["question"])
                    for r in json.loads(path.read_text(encoding="utf-8"))
                )
        for path in ROOT.glob("training/datasets/**/train.jsonl"):
            if path.parent != DATA:
                prior.update(normalize(r["text"]) for r in rows(path))
        overlap = [r["id"] for r in result if normalize(r["question"]) in prior]
        if overlap:
            raise ValueError(
                "Questions overlap earlier batches/training: " + ", ".join(overlap)
            )
    return result


def canonical_map():
    from app.catalog import Intent
    from app.domain import database
    from app.nlp.taxonomy import IntentRegistry
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    engine = database()
    mapping = {}
    with Session(engine) as db:
        taxonomy = IntentRegistry(db)
        for code in db.scalars(select(Intent.code)):
            spec = taxonomy.get(code)
            mapping[code] = spec.code if spec else code
    engine.dispose()
    return mapping


def judge(case, response, selected, previous, mapping):
    actual = {mapping.get(i, i) for i in response.get("intents", [])}
    context = response.get("context", {})
    expected = set(case["expected"])
    primary = next(iter(expected)) if len(expected) == 1 else None
    checks = {}
    if case["kind"] in {"SINGLE", "MULTI"}:
        checks["expected_intent_or_intents"] = actual == expected
    elif case["kind"] == "OOS":
        reliability = response.get("reliability", {})
        checks["scope_handled"] = response.get("state") in {
            "OUT_OF_SCOPE",
            "UNSUPPORTED",
        } or reliability.get("confidence_state") in {"OUT_OF_SCOPE", "UNSUPPORTED"}
    else:
        selection = context.get("service_id")
        if primary in {"GET_FARE", "BUS_PLATFORM", "JOURNEY_DURATION"}:
            checks["contextual_intent"] = primary in actual
            checks["selected_service_preserved"] = selection == selected["service_id"]
        elif primary in {"PRESERVE_SELECTION", "SELECT_SECOND"}:
            checks["selected_service_preserved"] = selection == selected["service_id"]
            if VERSION not in {"question100-v1", "question100-v2", "question100-v3"}:
                checks["request_resolved_without_clarification"] = not response.get(
                    "requires_clarification"
                )
        elif primary in {"DEST_TIRUMALA", "DEST_TIRUPATI", "DEST_ONGOLE"}:
            checks["destination_corrected"] = (
                context.get("destination_name")
                == {
                    "DEST_TIRUMALA": "Tirumala",
                    "DEST_TIRUPATI": "Tirupati",
                    "DEST_ONGOLE": "Ongole",
                }[primary]
            )
            checks["outdated_selection_removed"] = selection != selected["service_id"]
        elif primary == "ORIGIN_ONGOLE":
            checks["boarding_corrected"] = context.get("origin_name") == "Ongole"
        elif primary == "DATE_PLUS_TWO":
            checks["date_corrected"] = (
                context.get("travel_date")
                == (
                    datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=2)
                ).isoformat()
            )
        elif primary in {"FILTER_AC", "FILTER_NON_AC", "FILTER_SLEEPER"}:
            filters = context.get("filters", {})
            key = "sleeper" if primary == "FILTER_SLEEPER" else "ac"
            checks["filter_corrected"] = filters.get(key) == (
                primary != "FILTER_NON_AC"
            )
            checks["outdated_selection_removed"] = not response.get("selected_journey")
        elif primary == "BUDGET_250":
            checks["budget_applied"] = (
                float(context.get("filters", {}).get("max_fare") or 0) == 250
            )
        elif primary == "REMOVE_BUDGET":
            checks["budget_removed"] = (
                context.get("filters", {}).get("max_fare") is None
            )
        elif primary == "PASSENGERS_TWO":
            checks["passengers_updated"] = context.get("passengers") == 2
        elif primary == "REJECT_SELECTION":
            checks["selection_rejected"] = not response.get(
                "selected_journey"
            ) and response.get("requires_clarification")
        elif primary == "RESET":
            checks["context_reset"] = not context.get(
                "destination"
            ) and not response.get("selected_journey")
        elif primary == "REPEAT":
            checks["answer_repeated"] = response.get("answer") == previous.get("answer")
        elif primary == "LATER_DEPARTURES":
            checks["later_search_requested"] = (
                bool(context.get("filters", {}).get("after")) or "NEXT_BUS" in actual
            )
    checks["nonempty_answer"] = bool(response.get("answer"))
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "canonical_intents": sorted(actual),
        "grading": "Structured intent/context assertions, not human semantic adjudication",
    }


def exercise(client, question_set, mapping):
    results = []
    setup_requests = 0

    def send(body):
        for _ in range(3):
            response = client.post("/api/v1/conversation/message", json=body)
            if response.status_code != 429:
                break
            time.sleep(60)
        response.raise_for_status()
        return response.json()

    for case in question_set:
        owner = uuid4().hex + uuid4().hex
        previous = None
        selected = {}
        body = {
            "text": case["question"],
            "language": "en",
            "station_context": "Vijayawada",
            "owner_token": owner,
        }
        if case["kind"] != "OOS":
            first = send({**body, "text": "Next bus to Nellore tomorrow?"})
            setup_requests += 1
            if len(first.get("result_set", [])) < 2:
                raise ValueError(
                    "Need at least two published future Nellore services for grounded selected-journey testing"
                )
            selected = first["result_set"][1]
            initial_choice = (
                "1"
                if VERSION not in {"question100-v1", "question100-v2", "question100-v3"}
                and case["expected"] == ["SELECT_SECOND"]
                else "2"
            )
            previous = send(
                {**body, "text": initial_choice, "session_id": first["session_id"]}
            )
            setup_requests += 1
            if case["expected"] == ["REMOVE_BUDGET"]:
                previous = send(
                    {**body, "text": "Under 300", "session_id": first["session_id"]}
                )
                setup_requests += 1
            body["session_id"] = previous["session_id"]
        started = time.perf_counter()
        response = send(body)
        elapsed = (time.perf_counter() - started) * 1000
        results.append(
            {
                **case,
                "expected_selected_service": selected.get("service_id"),
                "expected_selected_fare": selected.get("fare"),
                "actual": response,
                "request_ms": elapsed,
                "evaluation": judge(case, response, selected, previous or {}, mapping),
            }
        )
    return {
        "evaluated_questions": len(results),
        "unique_questions": len({r["question"] for r in results}),
        "supporting_setup_requests": setup_requests,
        "passed": sum(r["evaluation"]["passed"] for r in results),
        "by_kind": {
            k: {
                "total": sum(r["kind"] == k for r in results),
                "passed": sum(
                    r["kind"] == k and r["evaluation"]["passed"] for r in results
                ),
            }
            for k in ["SINGLE", "CONTEXT", "MULTI", "OOS"]
        },
        "records": results,
    }


def baseline():
    import httpx

    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "before.json").exists():
        raise ValueError("Baseline already recorded; create a new batch version")
    question_set = cases()
    dump(OUT / "expected.json", question_set)
    with httpx.Client(
        base_url="http://127.0.0.1:8000", timeout=120, trust_env=False
    ) as client:
        report = exercise(client, question_set, canonical_map())
    report.update(
        mode="ACTUAL_RUNNING_BOT_HTTP_LOOPBACK",
        production_model="DETERMINISTIC_RULES",
        human_reviewed=False,
    )
    dump(OUT / "before.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


def prepare():
    original = BASE_DATA
    manifest = json.loads((original / "manifest.json").read_text(encoding="utf-8"))
    if (DATA / "manifest.json").exists():
        raise ValueError("Batch training manifest already frozen")
    train = rows(original / "train.jsonl")
    validation = rows(original / "validation.jsonl")
    challenge = rows(original / "synthetic_challenge.jsonl")
    heldout = {normalize(r["text"]) for r in validation + challenge}
    existing = {normalize(r["text"]) for r in train}
    structured = []
    added = []
    expected = json.loads((OUT / "expected.json").read_text(encoding="utf-8"))
    for case in expected:
        if case["kind"] not in {"SINGLE", "OOS"}:
            structured.append(
                {
                    **case,
                    "role": "STRUCTURED_DIALOGUE_OR_COMPOSITION_TRAINING_TARGET_NOT_60_WAY_LOSS",
                }
            )
            continue
        text = case["question"]
        key = normalize(text)
        if key in heldout:
            raise ValueError("New training question overlaps frozen evaluation")
        if key in existing:
            raise ValueError("Expected a unique new training question")
        row = {
            "id": case["id"],
            "text": text,
            "normalized_text": key,
            "intent": case["expected"][0] if case["kind"] == "SINGLE" else None,
            "kind": "IN_SCOPE" if case["kind"] == "SINGLE" else "OUT_OF_SCOPE",
            "family": "question100:" + case["id"],
            "group_id": "question100:" + case["id"],
            "source": "AGENT_EXPECTATION_NOT_BOT_OUTPUT",
            "human_reviewed": False,
            "review_status": "PENDING_HUMAN_REVIEW",
            "split": "train",
        }
        train.append(row)
        added.append(row)
        existing.add(key)
    files = {}
    for split, records in [
        ("train", train),
        ("validation", validation),
        ("synthetic_challenge", challenge),
    ]:
        path = DATA / (split + ".jsonl")
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
            encoding="utf-8",
        )
        counts = Counter(r["intent"] for r in records if r["kind"] == "IN_SCOPE")
        files[split] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha(path),
            "count": len(records),
            "intent_counts": dict(counts),
            "out_of_scope": sum(r["kind"] == "OUT_OF_SCOPE" for r in records),
        }
    (DATA / "structured_targets.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in structured), encoding="utf-8"
    )
    dump(
        DATA / "manifest.json",
        {
            "version": VERSION,
            "base_dataset_version": manifest["version"],
            "previous_candidate_version": PREVIOUS_VERSION,
            "new_classifier_ids": [r["id"] for r in added],
            "labels": manifest["labels"],
            "files": files,
            "minimum_train_examples": min(files["train"]["intent_counts"].values()),
            "under_30": {},
            "independent_human_test": 0,
            "human_reviewed": False,
            "added_single_label_or_oos": len(added),
            "structured_dialogue_or_multi": len(structured),
            "source_expectations_sha256": sha(OUT / "expected.json"),
            "validation_policy": "Unchanged recovery-v3 validation; no user-batch questions assigned here",
            "challenge_policy": "Unchanged synthetic regression holdout; never fit on these records",
            "evaluation_on_question100": "Training-set memorization check only, NOT independent accuracy",
        },
    )
    print(
        json.dumps(
            {
                "added_classifier_examples": len(added),
                "structured_targets": len(structured),
                "total_train": len(train),
            }
        )
    )


def shadow(previous=False):
    loop = asyncio.new_event_loop()
    from offline_guard import enforce_offline

    enforce_offline()
    import joblib

    with TemporaryDirectory(prefix="rtc-question100-") as temporary:
        target = Path(temporary) / "private.db"
        with (
            closing(sqlite3.connect(ROOT / "rtc.db")) as source,
            closing(sqlite3.connect(target)) as copy,
        ):
            source.backup(copy)
        os.environ.update(
            DATABASE_URL="sqlite:///" + target.as_posix(),
            RTC_MANAGED_RUNTIME="0",
            RTC_REQUESTS_PER_MINUTE="100000",
        )
        from app.main import app, engine
        from app.nlp.english_model import EnglishIntentModel
        from fastapi.testclient import TestClient

        model = joblib.load(
            ROOT
            / (
                f"models/english/nlp/{PREVIOUS_VERSION}/svm.joblib"
                if previous
                else f"models/english/nlp/{VERSION}/svm.joblib"
            )
        )
        original = EnglishIntentModel.predict
        calls = []

        def predict(self, text):
            calls.append(text)
            return model.predict_selective([normalize(text)])[0]

        EnglishIntentModel.predict = predict
        try:
            with TestClient(
                app, backend_options={"loop_factory": lambda: loop}
            ) as client:
                report = exercise(
                    client,
                    json.loads((OUT / "expected.json").read_text(encoding="utf-8")),
                    canonical_map(),
                )
            report.update(
                mode="PRIVATE_DB_OFFLINE_SHADOW_CANDIDATE_NOT_PRODUCTION",
                candidate_fallback_calls=len(calls),
                evaluation_role="Training-batch behavioral check; shared deterministic rules can still dominate",
            )
            dump(
                OUT / ("previous-shadow.json" if previous else "after-shadow.json"),
                report,
            )
            print(
                json.dumps(
                    {k: v for k, v in report.items() if k != "records"}, indent=2
                )
            )
        finally:
            EnglishIntentModel.predict = original
            engine.dispose()
            loop.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["baseline", "prepare", "shadow"])
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--previous-version", default=PREVIOUS_VERSION)
    parser.add_argument("--base-dataset", type=Path, default=BASE_DATA)
    parser.add_argument(
        "--previous",
        action="store_true",
        help="Shadow the pre-training candidate as a control",
    )
    a = parser.parse_args()
    for identifier in (a.version, a.previous_version):
        if not identifier or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in identifier
        ):
            parser.error("Versions must be simple identifiers")
    VERSION = a.version
    PREVIOUS_VERSION = a.previous_version
    BASE_DATA = a.base_dataset.resolve()
    DATA = ROOT / "training/datasets" / VERSION
    OUT = ROOT / "evaluation" / VERSION
    if a.action == "shadow":
        shadow(a.previous)
    else:
        {"baseline": baseline, "prepare": prepare}[a.action]()
