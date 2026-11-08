"""Local, deterministic candidate generation. Never pads missing diversity."""

import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from app.domain import Alias, Category, Operator, Service, Station, Stop, database

from training.generation.annotations import annotate
from training.validation.records import Example

VERSION = "2b-v1"


def snapshot(engine):
    with Session(engine) as s:
        stations = list(
            s.scalars(
                select(Station).where(Station.active.is_(True)).order_by(Station.code)
            )
        )
        station_ids = {p.id for p in stations}
        places = [(p.name, p.id) for p in stations] + [
            (a.name, a.station_id)
            for a in s.scalars(
                select(Alias).where(Alias.active.is_(True)).order_by(Alias.name)
            )
            if a.station_id in station_ids
        ]
        categories = [
            (c.name, c.id)
            for c in s.scalars(
                select(Category)
                .where(Category.active.is_(True))
                .order_by(Category.name)
            )
        ]
        service = s.scalar(
            select(Service).where(Service.active.is_(True)).order_by(Service.number)
        )
        stops = (
            list(
                s.scalars(
                    select(Stop)
                    .where(Stop.route_id == service.route_id)
                    .order_by(Stop.sequence)
                )
            )
            if service
            else []
        )
        journey = (
            {
                "origin": stops[0].station_id,
                "destination": stops[-1].station_id,
                "service_id": service.id,
            }
            if len(stops) > 1
            else {}
        )
        return {
            "places": sorted(set(places)),
            "categories": categories,
            "operators": [
                (o.code, o.id, o.dataset_source)
                for o in s.scalars(
                    select(Operator)
                    .where(Operator.active.is_(True))
                    .order_by(Operator.code)
                )
            ],
            "journey": journey,
            "station_names": {p.id: p.name for p in stations},
        }


def generate(registry, vocabulary):
    rows = []
    digest = hashlib.sha256(json.dumps(vocabulary, sort_keys=True).encode()).hexdigest()

    def add(text, codes, kind, family, **extra):
        identifier = hashlib.sha256(
            json.dumps([VERSION, text, codes, extra], sort_keys=True).encode()
        ).hexdigest()[:24]
        row = {
            "example_id": identifier,
            "text": text,
            "language": "en",
            "intent_codes": codes,
            "dialogue_act": None,
            "dataset_type": kind,
            "style": "natural",
            "entities": annotate(text, vocabulary),
            "context": {},
            "source_type": "SYNTHETIC",
            "generator_version": "bounded-authored-banks-v1",
            "template_family": family,
            "quality_status": "PENDING_HUMAN_REVIEW",
            "dataset_version": VERSION,
            "provenance": {
                "seed": 42,
                "vocabulary_source": "LOCAL_DATABASE_SNAPSHOT",
                "vocabulary_sha256": digest,
                "augmentation": "none",
            },
            **extra,
        }
        rows.append(Example.model_validate(row).model_dump(mode="json"))

    for spec in registry["intents"]:
        for i, text in enumerate(spec["examples"]):
            parent = hashlib.sha256(text.encode()).hexdigest()[:24]
            add(
                text,
                [spec["code"]],
                "SINGLE_INTENT",
                f"{spec['code']}:authored:{i}",
                parent_example_id=parent,
            )
    base = vocabulary["journey"]
    if not base:
        raise ValueError("A real database journey is required for context generation")
    dest = vocabulary["station_names"][base["destination"]]
    other = next(
        identifier
        for _, identifier in vocabulary["places"]
        if identifier not in (base["origin"], base["destination"])
    )
    other_name = vocabulary["station_names"][other]
    multi = [
        (
            "NEXT_BUS",
            "GET_FARE",
            [
                f"When is the next bus to {dest}, and how much does its ticket cost?",
                f"Show the next departure for {dest} together with its applicable fare.",
                f"I need both the upcoming {dest} departure and the price for the same segment.",
                f"Which bus for {dest} leaves next, and what will that ride cost?",
            ],
        ),
        (
            "BUS_DELAY",
            "BUS_PLATFORM",
            [
                "Is the selected trip delayed, and which platform is confirmed?",
                "Tell me the reported delay and the assigned bay for this bus.",
                "Has this departure been held up, and where should I board it?",
                "Can you check both the delay minutes and the boarding platform?",
            ],
        ),
        (
            "FASTEST_BUS",
            "INTERMEDIATE_STOP",
            [
                f"Which bus reaches {dest} fastest, and does that service call at the via station?",
                f"Find the quickest ride to {dest} and verify its intermediate halt.",
                f"Among {dest} buses, which is fastest and will it stop at my requested station?",
                f"Check the fastest {dest} option and whether boarding is allowed at its intermediate stop.",
            ],
        ),
        (
            "ARRIVAL_TIME",
            "JOURNEY_DURATION",
            [
                "When does the selected bus reach my destination, and how long is the ride?",
                "Give me its scheduled arrival together with the journey duration.",
                "How many hours will I travel, and at what time will this service arrive?",
                "For this boarding segment, check the arrival time and total travel duration.",
            ],
        ),
    ]
    for left, right, questions in multi:
        for i, text in enumerate(questions):
            add(
                text,
                [left, right],
                "MULTI_INTENT",
                f"{left}+{right}:{i}",
                context={
                    **base,
                    **({"via_station": other} if left == "FASTEST_BUS" else {}),
                },
            )
    followups = [
        (
            "Only air-conditioned options, please.",
            "CHANGE_BUS_TYPE",
            {"filters": {"ac": True}},
        ),
        (
            "I would prefer a seater rather than a sleeper.",
            "CHANGE_BUS_TYPE",
            {"filters": {"sleeper": False}},
        ),
        (
            f"Actually, make the destination {other_name}.",
            "CHANGE_DESTINATION",
            {"destination": other},
        ),
        (
            f"I need to board from {other_name} instead.",
            "CORRECTION",
            {"origin": other},
        ),
        (
            "Could you check tomorrow instead?",
            "CHANGE_DATE",
            {"travel_date": "2026-11-09"},
        ),
        ("Make that three passengers.", "CORRECTION", {"passengers": 3}),
        (
            "What is the fare for the service you just showed?",
            "CLARIFICATION_REPLY",
            {},
        ),
        ("Yes, that is the service I meant.", "AFFIRMATION", {}),
        ("No, that is not the departure I want.", "NEGATION", {"service_id": None}),
        ("Start a completely new enquiry.", "RESET_CONVERSATION", {}),
        ("Please repeat the previous answer.", "REPEAT_REQUEST", {}),
        (
            "The second listed option is the one I mean.",
            "CLARIFICATION_REPLY",
            {"selection_index": 1},
        ),
    ]
    for i, (text, act, changes) in enumerate(followups):
        before = {
            **base,
            "travel_date": "2026-11-08",
            "current_time": "2026-11-08T10:00:00+05:30",
            "last_intent": "NEXT_BUS",
        }
        after = {**before, **changes}
        if any(k in changes for k in ("origin", "destination", "travel_date")):
            after.pop("service_id", None)
        if act == "RESET_CONVERSATION":
            after = {}
        if "selection_index" in changes:
            # No invented second service: ask for the list when a real result set is absent.
            after = before.copy()
            changes = {}
            before["pending_clarification"] = "result_list_required"
            after = {**before, "dialogue_state": "AWAITING_SERVICE_SELECTION"}
        add(
            text,
            ["GET_FARE"] if i == 6 else [],
            "CONTEXTUAL",
            f"followup:{act}:{i}",
            dialogue_act=act,
            context=before,
            slot_changes=changes,
            expected_context=after,
            style="contextual",
        )
    outside = [
        "What is the cricket score?",
        "Can you book a hotel for me?",
        "Will it rain tomorrow?",
        "Who won the election?",
        "How do I open a bank account?",
        "Tell me a joke about cats.",
        "Can you order lunch for delivery?",
        "What is the price of gold today?",
        "Please solve this algebra problem.",
        "Can you diagnose my headache?",
        "How do I repair my washing machine?",
        "Play my favourite song.",
        "What movies are showing tonight?",
        "Can you send an email to my boss?",
        "Where can I buy a new phone?",
        "What is the current stock market index?",
        "Translate this legal contract.",
        "How do I renew my passport?",
        "Can you pay my electricity bill?",
        "What is the recipe for vegetable biryani?",
    ]
    for i, text in enumerate(outside):
        add(
            text,
            [],
            "OUT_OF_SCOPE",
            f"out_of_scope:topic:{i}",
            dialogue_act="OUT_OF_SCOPE",
        )
    ambiguous_phrases = [
        "What is the earliest bus?",
        "Can I catch a bus before services end?",
        "When will it get here?",
        "What is going around seven?",
        "Does it go through that town?",
        "Can I get there on a bus?",
        "What do these options cost?",
        "Is there a cheaper ticket for me?",
        "What is happening with my bus?",
        "Which bay are we using now?",
        "Is my seat confirmed?",
    ]
    for i, pair in enumerate(registry["ambiguity_matrix"]):
        add(
            ambiguous_phrases[i],
            [],
            "AMBIGUOUS",
            f"ambiguity:{i}",
            possible_intents=[pair["left"], pair["right"]],
            missing_slots=["intent_qualifier"],
            clarification_target="intent_qualifier",
            context={"requires_previous_context": False},
            style="clarification",
        )
    negatives = [
        ("No AC buses, please.", {"ac": False}),
        ("Only non-AC services.", {"ac": False}),
        ("Not a sleeper.", {"sleeper": False}),
        ("A seater rather than a sleeper.", {"sleeper": False}),
        ("Keep the price under 500 rupees.", {"max_fare": "500"}),
        ("After 8 PM, not before.", {"departure_after": "20:00"}),
        ("Before 6 AM, not later.", {"departure_before": "06:00"}),
        ("No, tomorrow rather than today.", {"travel_date": "2026-11-09"}),
        (f"No, I meant {other_name}, not {dest}.", {"destination": other}),
    ]
    for name, identifier in vocabulary["categories"]:
        negatives.append(
            (f"Anything except {name}.", {"exclude_categories": [identifier]})
        )
    for i, (text, constraint) in enumerate(negatives):
        add(
            text,
            [],
            "NEGATION_CORRECTION",
            f"constraint:{i}",
            constraints=constraint,
            dialogue_act=(
                "CHANGE_DATE"
                if "travel_date" in constraint
                else "CHANGE_DESTINATION"
                if "destination" in constraint
                else "CHANGE_BUS_TYPE"
                if any(k in constraint for k in ("ac", "sleeper", "exclude_categories"))
                else "CORRECTION"
            ),
            context={**base, "current_time": "2026-11-08T10:00:00+05:30"},
            style="negation",
        )
    # Explicit synthetic phonetic variants; only apply where the source phrase occurs.
    replacements = [
        ("Nellore", "nelore"),
        ("Tirupati", "tirupathi"),
        ("Super Luxury", "super luxery"),
        ("platform", "plat form"),
    ]
    for spec in registry["intents"]:
        for index, text in enumerate(spec["examples"]):
            for original, altered in replacements:
                if original.casefold() not in text.casefold():
                    continue
                import re

                noisy = re.sub(re.escape(original), altered, text, flags=re.IGNORECASE)
                add(
                    noisy,
                    [spec["code"]],
                    "ASR_STYLE",
                    f"{spec['code']}:authored:{index}",
                    clean_transcript=text,
                    noisy_transcript=noisy,
                    parent_example_id=hashlib.sha256(text.encode()).hexdigest()[:24],
                    style="asr_like",
                    provenance={
                        "seed": 42,
                        "vocabulary_source": "LOCAL_DATABASE_SNAPSHOT",
                        "vocabulary_sha256": digest,
                        "augmentation": "SYNTHETIC_PHONETIC_VARIANT_NOT_MEASURED_VOSK",
                    },
                )
    for row in rows:
        if row["dataset_type"] == "SINGLE_INTENT":
            row["provenance"]["source_example_sha256"] = row["parent_example_id"]
            row["provenance"]["source_dataset"] = (
                "training/datasets/phase2a_seed_examples.jsonl"
            )
            row["parent_example_id"] = None
        elif row["dataset_type"] == "ASR_STYLE":
            parent = next(
                r
                for r in rows
                if r["dataset_type"] == "SINGLE_INTENT"
                and r["text"] == row["clean_transcript"]
            )
            row["parent_example_id"] = parent["example_id"]
    # Exact and normalized duplicates are quarantined, never counted as accepted data.
    from training.validation.validate_phase2b import normalize

    unique = []
    seen = set()
    for row in rows:
        key = (normalize(row["text"]), json.dumps(row["context"], sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def main():
    manifest = json.loads((ROOT / "training/config/intent_registry.yaml").read_text())
    vocabulary = snapshot(database())
    rows = generate(manifest, vocabulary)
    output = ROOT / "training/datasets/generated" / VERSION
    output.mkdir(parents=True, exist_ok=True)
    (output / "vocabulary.json").write_text(
        json.dumps(vocabulary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for kind in sorted({r["dataset_type"] for r in rows}):
        (output / (kind.lower() + ".jsonl")).write_text(
            "\n".join(
                json.dumps(r, ensure_ascii=False, sort_keys=True)
                for r in rows
                if r["dataset_type"] == kind
            )
            + "\n",
            encoding="utf-8",
        )
    (output / "all.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
        + "\n",
        encoding="utf-8",
    )
    specs = [
        {
            **r,
            "generation_resources": "five independently authored Phase 2A seeds; no padding",
            "negative_examples": r["similar_intents"],
            "context_requirements": r["required_slot_alternatives"],
            "edge_cases": ["unknown data", "missing required slots"],
            "valid_response_expectations": r["result_statuses"],
            "query_patterns": r["examples"],
            "linguistic_variations_available": len(r["examples"]),
            "target_distinct_candidates": 200,
            "generation_shortfall_expected": max(0, 200 - len(r["examples"])),
        }
        for r in manifest["intents"]
    ]
    for spec in specs:
        alternatives = [
            other
            for other in manifest["intents"]
            if other["intent_group"] == spec["intent_group"]
            and other["code"] != spec["code"]
        ]
        negative = alternatives[0]
        spec["negative_examples"] = [
            {
                "text": negative["examples"][0],
                "intent_codes": [negative["code"]],
                "review_status": "PENDING_HUMAN_REVIEW",
            }
        ]
        spec["confusable_intents"] = [r["intent"] for r in spec["similar_intents"]]
        spec["common_passenger_situations"] = [
            "station enquiry with missing context",
            "follow-up about a selected journey",
        ]
    (ROOT / "training/generation/intent_specs.json").write_text(
        json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "records": len(rows),
                "output": str(output),
                "status": "INCOMPLETE_DIVERSITY_SHORTFALL",
            }
        )
    )


if __name__ == "__main__":
    main()
