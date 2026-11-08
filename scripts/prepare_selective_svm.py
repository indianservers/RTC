"""Build immutable text-only training/validation snapshots and a fresh test, before fitting."""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "training/datasets/selective-60-v2"
TEST = ROOT / "evaluation/english-svm-v2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def rows(path):
    return [
        json.loads(x)
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]


def dump(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_rows(path, data):
    path.write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in data),
        encoding="utf-8",
    )


def bank(path, split, kind):
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        label, *texts = line.split("|")
        for i, text in enumerate(texts):
            result.append(
                {
                    "id": f"{split}-{kind}-{label}-{i:02}",
                    "text": text,
                    "intent": label if kind == "IN_SCOPE" else None,
                    "kind": kind,
                    "split": split,
                    "family": f"{split}:{kind}:{label}:authored-{i}",
                    "source": "NEW_AGENT_AUTHORED",
                    "human_reviewed": False,
                }
            )
    return result


def main():
    if (FOLDER / "manifest.json").exists() or (TEST / "manifest.json").exists():
        raise SystemExit(
            "Version already frozen; create a new version rather than overwrite"
        )
    sys.path.insert(0, str(ROOT / "scripts"))
    from offline_guard import enforce_offline

    enforce_offline()
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    labels = {
        r["code"]
        for r in json.loads(
            (ROOT / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
        )["intents"]
    }
    original = ROOT / "training/datasets/splits/2c-v1/train.jsonl"
    prior_manifest = json.loads(
        (original.parent / "manifest.json").read_text(encoding="utf-8")
    )
    assert digest(original) == prior_manifest["files"]["train"]["sha256"]
    train = bank(FOLDER / "train-bank.txt", "train", "IN_SCOPE") + bank(
        FOLDER / "oos-train-bank.txt", "train", "OUT_OF_SCOPE"
    )
    for row in rows(original):
        if row["dataset_type"] == "SINGLE_INTENT" and len(row["intent_codes"]) == 1:
            train.append(
                {
                    "id": "prior-" + row["example_id"],
                    "text": row["text"],
                    "intent": row["intent_codes"][0],
                    "kind": "IN_SCOPE",
                    "split": "train",
                    "family": "prior:" + row["leakage_group"],
                    "source": "PRIOR_TRAIN_SPLIT_ONLY",
                    "human_reviewed": False,
                }
            )
    validation = bank(FOLDER / "validation-bank.txt", "validation", "IN_SCOPE") + bank(
        FOLDER / "oos-validation-bank.txt", "validation", "OUT_OF_SCOPE"
    )
    test = bank(TEST / "intent-bank.txt", "test", "IN_SCOPE") + bank(
        TEST / "oos-bank.txt", "test", "OUT_OF_SCOPE"
    )
    forbidden_paths = sorted(
        [
            *ROOT.glob("evaluation/english-svm-v1/*.jsonl"),
            ROOT / "training/datasets/splits/2c-v1/validation.jsonl",
            ROOT / "training/datasets/splits/2c-v1/synthetic_challenge.jsonl",
            *ROOT.glob("rtc-simulation-lab/benchmarks/*.jsonl"),
        ]
    )
    forbidden = []
    for path in forbidden_paths:
        for row in rows(path):
            text = row.get("text") or row.get("question")
            if text:
                forbidden.append((text, path.relative_to(ROOT).as_posix()))
    audit = {
        "forbidden_source_hashes": {
            str(p.relative_to(ROOT)): digest(p) for p in forbidden_paths
        },
        "cutoff": 0.85,
        "excluded": [],
        "decisions": [],
    }
    cleaned = {}
    accepted = []
    for split, candidates in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:
        references = forbidden + [(r["text"], r["id"]) for r in accepted]
        source_texts = [normalize(t) for t, _ in references]
        vector = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), max_features=60000
        )
        matrix = vector.fit_transform(source_texts)
        similarities = linear_kernel(
            vector.transform([normalize(r["text"]) for r in candidates]), matrix
        )
        unique = {}
        kept = []
        for i, row in enumerate(candidates):
            key = normalize(row["text"])
            j = int(similarities[i].argmax())
            similarity = float(similarities[i, j])
            exact = key in set(source_texts)
            reason = (
                "exact_cross_split_or_forbidden"
                if exact
                else "near_cross_split_or_forbidden"
                if similarity >= 0.85
                else None
            )
            if key in unique:
                if unique[key]["intent"] != row["intent"]:
                    raise ValueError("Contradictory labels")
                reason = "within_split_duplicate"
            unique[key] = row
            decision = {
                "id": row["id"],
                "split": split,
                "similarity": similarity,
                "nearest_text": references[j][0],
                "nearest_source": references[j][1],
                "reason": reason,
            }
            audit["decisions"].append(decision)
            if reason:
                audit["excluded"].append(dict(row, audit=decision))
            else:
                kept.append(row)
        assert {r["intent"] for r in kept if r["kind"] == "IN_SCOPE"} == labels, (
            f"Missing {split} labels"
        )
        assert any(r["kind"] == "OUT_OF_SCOPE" for r in kept)
        cleaned[split] = kept
        accepted += kept
    assert not (
        {normalize(r["text"]) for r in cleaned["train"]}
        & {normalize(r["text"]) for r in cleaned["validation"]}
    )
    assert not (
        {r["family"] for r in cleaned["train"]}
        & {r["family"] for r in cleaned["validation"]}
    )
    files = {}
    for split in ("train", "validation"):
        p = FOLDER / f"{split}.jsonl"
        write_rows(p, cleaned[split])
        files[split] = {
            "path": p.relative_to(ROOT).as_posix(),
            "sha256": digest(p),
            "records": len(cleaned[split]),
            "kind_counts": dict(Counter(r["kind"] for r in cleaned[split])),
            "intent_counts": dict(
                Counter(r["intent"] for r in cleaned[split] if r["intent"])
            ),
        }
    testpath = TEST / "holdout.jsonl"
    write_rows(testpath, test)
    # Keep every pre-authored fresh question frozen; eligibility is a separate pre-training audit.
    eligibility = {r["id"]: r["id"] in {x["id"] for x in cleaned["test"]} for r in test}
    dump(TEST / "eligibility.json", eligibility)
    dump(FOLDER / "leakage-audit.json", audit)
    manifest = {
        "version": "selective-60-v2",
        "files": files,
        "protocol_sha256": digest(FOLDER / "protocol.json"),
        "audit_sha256": digest(FOLDER / "leakage-audit.json"),
        "old_train_sha256": digest(original),
        "test_question_access": "Training must not open the fresh test questions; separate evaluation step after checkpoint freeze",
        "source_status": "Synthetic agent-authored, not human-reviewed",
    }
    dump(FOLDER / "manifest.json", manifest)
    dump(
        TEST / "manifest.json",
        {
            "version": "english-svm-v2",
            "sha256": digest(testpath),
            "eligibility_sha256": digest(TEST / "eligibility.json"),
            "protocol_sha256": digest(FOLDER / "protocol.json"),
            "total": len(test),
            "eligible": len(cleaned["test"]),
            "kind_counts": dict(Counter(r["kind"] for r in cleaned["test"])),
            "training_manifest_sha256": digest(FOLDER / "manifest.json"),
            "notes": "Frozen before model fitting; no test-driven model or threshold updates. Prior evaluation never used as training/validation examples; overlap audit only.",
        },
    )
    print(
        json.dumps(
            {
                "files": files,
                "fresh_test_total": len(test),
                "fresh_test_eligible": len(cleaned["test"]),
                "exclusions": dict(Counter(r["split"] for r in audit["excluded"])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
