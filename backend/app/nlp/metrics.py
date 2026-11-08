import hashlib

"""Text-free daily aggregate counters in the existing audit store."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from ..records import Audit


def capture(session, operator_id, response, repair):
    day = datetime.now(UTC).date().isoformat()
    key = "nlp-metrics:" + str(operator_id) + ":" + day
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    session.execute(
        insert(Audit)
        .values(
            id=str(uuid4()),
            idempotency_key=key,
            operator_id=operator_id,
            entity_type="NLP_DAILY_METRICS",
            entity_id=day,
            operation="AGGREGATE",
            actor="system",
            recorded_at=datetime.now(UTC),
            dataset_source="LOCAL",
            active=True,
            version=1,
            new_values={},
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )
    row = session.scalar(
        select(Audit).where(Audit.idempotency_key == key).with_for_update()
    )
    v = dict(row.new_values)
    v["day"] = day
    for counter, delta in {
        "turns": 1,
        "clarifications": int(response.requires_clarification),
        "out_of_scope": int(response.state == "OUT_OF_SCOPE"),
        "no_results": int(response.state == "NO_RESULTS"),
        "repairs": int(bool(repair)),
        "entity_errors": int(
            response.reliability.error_category == "ENTITY_RESOLUTION_ERROR"
        ),
    }.items():
        v[counter] = v.get(counter, 0) + delta
    intents = dict(v.get("intents", {}))
    for code in response.intents:
        intents[code] = intents.get(code, 0) + 1
    v["intents"] = intents
    for field, values in (
        (
            "station_ids",
            [response.context.get("origin"), response.context.get("destination")],
        ),
        ("category_ids", [response.context.get("filters", {}).get("category")]),
    ):
        v[field] = sorted(set(v.get(field, [])) | {x for x in values if x})[:200]
    names = dict(v.get("station_name_hashes", {}))
    for slot in ("origin", "destination"):
        identifier = response.context.get(slot)
        name = response.context.get(slot + "_name")
        if identifier and name:
            names[identifier] = hashlib.sha256(name.casefold().encode()).hexdigest()[
                :16
            ]
    v["station_name_hashes"] = dict(list(names.items())[-200:])
    row.new_values = v
    row.version += 1


def report(rows):
    now = datetime.now(UTC).date()
    recent = []
    previous = []
    for row in rows:
        v = row.new_values or {}
        day = datetime.fromisoformat(v["day"]).date()
        if now - timedelta(days=7) < day <= now:
            recent.append(v)
        elif now - timedelta(days=14) < day <= now - timedelta(days=7):
            previous.append(v)

    def counts(values):
        out = Counter()
        for v in values:
            for key in (
                "turns",
                "clarifications",
                "out_of_scope",
                "no_results",
                "repairs",
                "entity_errors",
            ):
                out[key] += v.get(key, 0)
        return dict(out)

    a, b = counts(recent), counts(previous)
    drift = {
        "status": "INSUFFICIENT_EVIDENCE",
        "minimum_window_samples": 100,
        "recent_samples": a.get("turns", 0),
        "previous_samples": b.get("turns", 0),
    }
    if min(a.get("turns", 0), b.get("turns", 0)) >= 100:

        def distribution(values):
            counter = Counter()
            for v in values:
                counter.update(v.get("intents", {}))
            total = sum(counter.values()) or 1
            return {k: n / total for k, n in counter.items()}

        x, y = distribution(recent), distribution(previous)
        distance = sum(abs(x.get(k, 0) - y.get(k, 0)) for k in set(x) | set(y)) / 2
        drift.update(
            status="QUESTION_MIX_SHIFT_REVIEW"
            if distance > 0.2
            else "NO_QUESTION_MIX_SHIFT_DETECTED",
            total_variation=distance,
            model_drift_claim=False,
        )
    old = {s for v in previous for s in v.get("station_ids", [])}
    drift["new_recorded_station_ids"] = sorted(
        {s for v in recent for s in v.get("station_ids", [])} - old
    )
    old_categories = {s for v in previous for s in v.get("category_ids", [])}
    drift["new_recorded_category_ids"] = sorted(
        {s for v in recent for s in v.get("category_ids", [])} - old_categories
    )
    return {
        "recent_usage": a,
        "previous_usage": b,
        "usage_rates": {
            key: a.get(key, 0) / a["turns"] if a.get("turns") else None
            for key in (
                "clarifications",
                "out_of_scope",
                "no_results",
                "repairs",
                "entity_errors",
            )
        },
        "drift": drift,
    }
