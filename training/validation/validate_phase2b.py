"""Validate records and report candidate diversity, never equating strings to semantics."""

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.validation.records import Example


def normalize(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def family_leakage(rows):
    splits = {}
    violations = []
    for row in rows:
        split = row.get("split")
        if not split:
            continue
        family = row["template_family"]
        if family in splits and splits[family] != split:
            violations.append(family)
        splits[family] = split
    return sorted(set(violations))


def validate(rows, registry, vocabulary):
    if family_leakage(rows):
        raise ValueError("Template family crosses supplied split boundaries")
    codes = {r["code"] for r in registry["intents"]}
    known_types = {
        r["code"]
        for r in json.loads(
            (ROOT / "training/config/entity_registry.yaml").read_text()
        )["entities"]
    }
    known_acts = {
        r["code"]
        for r in json.loads((ROOT / "training/config/dialogue_acts.yaml").read_text())[
            "dialogue_acts"
        ]
    }
    known_ids = {identifier for _, identifier in vocabulary["places"]} | {
        identifier for _, identifier in vocabulary["categories"]
    }
    errors = []
    ids = set()
    texts = Counter()
    record_keys = set()
    single = Counter()
    families = defaultdict(set)
    styles = Counter()
    category = Counter()
    types = Counter()
    entity_values = Counter()
    normalized = []
    shapes = Counter()
    all_ids = {r["example_id"] for r in rows}
    for n, raw in enumerate(rows, 1):
        try:
            row = Example.model_validate(raw)
            if not set(row.intent_codes) <= codes:
                raise ValueError("Unknown intent label")
            if row.example_id in ids:
                raise ValueError("Duplicate example ID")
            ids.add(row.example_id)
            if row.parent_example_id and row.parent_example_id not in all_ids:
                raise ValueError("Unresolved parent example ID")
            if row.dialogue_act and row.dialogue_act not in known_acts:
                raise ValueError("Unknown dialogue act")
            for entity in row.entities:
                if entity.type not in known_types:
                    raise ValueError("Unknown entity type")
                if entity.canonical_id and entity.canonical_id not in known_ids:
                    raise ValueError("Canonical ID not in DB snapshot")
                entity_values[str(entity.value)] += 1
            key = (normalize(row.text), json.dumps(row.context, sort_keys=True))
            if key in record_keys:
                raise ValueError("Normalized duplicate with identical context")
            record_keys.add(key)
            texts[normalize(row.text)] += 1
            normalized.append(
                (n, row.intent_codes, normalize(row.text), row.template_family)
            )
            shape = row.text.casefold()
            for e in sorted(row.entities, key=lambda x: -x.start):
                shape = shape[: e.start] + "<" + e.type + ">" + shape[e.end :]
            shapes[normalize(shape)] += 1
            category[row.dataset_type] += 1
            styles[row.style] += 1
            if row.dialogue_act and row.dialogue_act not in known_acts:
                raise ValueError("Unknown dialogue act")
            for entity in row.entities:
                if entity.type not in known_types:
                    raise ValueError("Unknown entity type")
                types[entity.type] += 1
            if row.dataset_type == "SINGLE_INTENT":
                single[row.intent_codes[0]] += 1
                families[row.intent_codes[0]].add(row.template_family)
            if (
                row.dataset_type == "NEGATION_CORRECTION"
                and re.search(r"\b(?:no ac|non[ -]?ac)\b", row.text, re.IGNORECASE)
                and row.constraints.get("ac") is not False
            ):
                raise ValueError("Negated AC became a positive or missing constraint")
        except ValueError as exc:
            errors.append(
                {"row": n, "example_id": raw.get("example_id"), "error": str(exc)}
            )
    near = []
    # Corpus is intentionally small; bound pair count before admitting larger corpora.
    if len(normalized) > 5000:
        raise ValueError(
            "Large-corpus near-duplicate indexing must be implemented before expansion"
        )
    for i, (left, labels, a, family) in enumerate(normalized):
        for right, other, b, other_family in normalized[i + 1 :]:
            if SequenceMatcher(None, a, b).ratio() >= 0.9:
                near.append(
                    {
                        "left": left,
                        "right": right,
                        "same_family": family == other_family,
                        "label_conflict": labels != other,
                    }
                )
    deficits = {
        code: 200 - single[code] for code in sorted(codes) if single[code] < 200
    }
    grams = [
        set(zip(words, words[1:], words[2:]))
        for _, _, text, _ in normalized
        for words in [text.split()]
    ]
    overlap_total = 0.0
    overlap_pairs = 0
    for index, left in enumerate(grams):
        for right in grams[index + 1 :]:
            union = left | right
            overlap_total += len(left & right) / len(union) if union else 0
            overlap_pairs += 1
    return {
        "mean_pairwise_trigram_jaccard": overlap_total / max(1, overlap_pairs),
        "status": "PHASE 2B INCOMPLETE",
        "records": len(rows),
        "valid_records": len(rows) - len(errors),
        "intent_counts": dict(sorted(single.items())),
        "category_counts": dict(category),
        "style_counts": dict(styles),
        "unique_normalized_text": len(texts),
        "duplicate_normalized_text_pairs": sum(
            v * (v - 1) // 2 for v in texts.values()
        ),
        "exact_duplicate_ids": len(rows) - len(ids),
        "near_duplicate_pairs": len(near),
        "near_duplicate_examples": near[:20],
        "near_duplicate_label_conflicts": sum(x["label_conflict"] for x in near),
        "template_family_counts": {k: len(v) for k, v in families.items()},
        "repeated_sentence_shapes": sum(v - 1 for v in shapes.values()),
        "lexical_diversity": len(set(" ".join(texts).split()))
        / max(1, len(" ".join(texts).split())),
        "entity_annotation_count": sum(types.values()),
        "entity_type_counts": dict(types),
        "entity_distribution": dict(entity_values),
        "unreviewed_records": len(rows),
        "human_reviewed_records": 0,
        "single_intent_shortfalls": deficits,
        "quantity_targets_met": not deficits
        and category["MULTI_INTENT"] >= 1000
        and category["CONTEXTUAL"] >= 1000
        and all(
            category[k] >= 500
            for k in ["OUT_OF_SCOPE", "AMBIGUOUS", "NEGATION_CORRECTION", "ASR_STYLE"]
        ),
        "schema_errors": errors,
        "semantic_diversity_verified": False,
        "split_status": "NOT_CONSTRUCTED_PHASE_2C_DEFERRED",
    }


def main():
    folder = ROOT / "training/datasets/generated/2b-v1"
    rows = [
        json.loads(s)
        for s in (folder / "all.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    registry = json.loads((ROOT / "training/config/intent_registry.yaml").read_text())
    vocabulary = json.loads((folder / "vocabulary.json").read_text(encoding="utf-8"))
    report = validate(rows, registry, vocabulary)
    bad = dict(rows[0])
    bad["text"] = ""
    try:
        Example.model_validate(bad)
    except ValueError as exc:
        report["failed_validation_examples"] = [
            {
                "mutation": "Empty passenger text",
                "result": "REJECTED",
                "error": str(exc).splitlines()[0],
            }
        ]
    report["sha256"] = hashlib.sha256((folder / "all.jsonl").read_bytes()).hexdigest()
    out = ROOT / "training/reports"
    out.mkdir(exist_ok=True)
    (out / "phase2b_quality.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Phase 2B dataset quality report",
        "",
        "PHASE 2B INCOMPLETE. No models trained.",
        "",
        f"Generated: {report['records']}. Schema-valid: {report['valid_records']}. Unreviewed synthetic: {report['unreviewed_records']}. Human-reviewed: 0.",
        "",
        "## Dataset categories",
        "",
    ] + [f"- {k}: {v}" for k, v in report["category_counts"].items()]
    lines += ["", "## Per-intent coverage", ""] + [
        f"- {k}: {v}/200; {report['template_family_counts'].get(k, 0)} authored families."
        for k, v in report["intent_counts"].items()
    ]
    lines += [
        "",
        "## Quality findings",
        "",
        f"Near-duplicate pairs: {report['near_duplicate_pairs']} (normalized character similarity >=0.90; a heuristic, not semantic proof). Normalized duplicate text pairs: {report['duplicate_normalized_text_pairs']}. Exact duplicate IDs: {report['exact_duplicate_ids']}. Repeated annotated sentence shapes: {report['repeated_sentence_shapes']}.",
        "Only five authored seed structures per intent exist. Station substitutions and ASR normalization are not counted toward the 200 single-intent target. Style-specific distribution targets remain incomplete; mean pairwise trigram overlap is recorded in the JSON report. The ASR set contains controlled synthetic phonetic variants, not measured Vosk errors. Most examples lack comprehensive entity labels; exact unambiguous DB spans are annotated, unclear roles are left absent. Unconfigured categories in older question seeds remain hypothetical mentions and have no fabricated IDs. Demo vocabulary is not official operator-service evidence.",
        "No held-out splits were constructed; family and parent IDs are retained for Phase 2C. The supplied 300 Phase 2A examples are preserved separately. Current duplicate/diversity findings block training readiness. No 12000 or 16000 record claim is made.",
        "",
        "## Schema failures",
        "",
        json.dumps(
            {
                "candidate_errors": report["schema_errors"],
                "intentionally_invalid_fixture": report["failed_validation_examples"],
            },
            indent=2,
        ),
        "",
        "## Heuristic near-duplicate examples",
        "",
        json.dumps(report["near_duplicate_examples"], indent=2),
        "",
        "## Remaining styles and entity coverage",
        "",
        json.dumps(
            {
                "styles": report["style_counts"],
                "entity_types": report["entity_type_counts"],
            },
            indent=2,
        ),
    ]
    notes = ROOT / "training/generation/limitations.md"
    if notes.exists():
        lines += ["", notes.read_text(encoding="utf-8")]
    (out / "PHASE_2B_DATASET_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "records",
                    "valid_records",
                    "category_counts",
                    "near_duplicate_pairs",
                    "duplicate_normalized_text_pairs",
                    "quantity_targets_met",
                    "schema_errors",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
