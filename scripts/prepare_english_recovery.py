"""Freeze audited synthetic data before training; never manufacture human review."""

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "training/datasets/recovery-60-v3"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [
        json.loads(x)
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def prepare():
    if (FOLDER / "manifest.json").exists():
        raise ValueError(
            "Frozen corpus exists; choose a new version instead of editing it"
        )
    from offline_guard import enforce_offline

    enforce_offline()
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    labels = sorted(
        r["code"]
        for r in json.loads(
            (ROOT / "training/config/intent_registry.yaml").read_text()
        )["intents"]
    )
    vocab_path = ROOT / "evaluation/english-recovery-v3/db-vocabulary.json"
    vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
    stations = [
        s
        for s in vocab["stations"] + vocab["aliases"]
        if s.isascii()
        and len(s) > 2
        and "DEMO" not in s
        and not any(c.isdigit() for c in s)
    ]
    train = rows(ROOT / "training/datasets/selective-60-v2/train.jsonl")
    validation = rows(ROOT / "training/datasets/selective-60-v2/validation.jsonl")
    challenge = rows(ROOT / "evaluation/english-svm-v2/holdout.jsonl")
    for line in (FOLDER / "train-bank.txt").read_text(encoding="utf-8").splitlines():
        code, *questions = line.split("|")
        if code not in labels:
            raise ValueError("Unknown intent " + code)
        for index, question in enumerate(questions):
            text = question.replace(
                "{station}", stations[index % len(stations)]
            ).replace("{origin}", stations[(index + 3) % len(stations)])
            train.append(
                {
                    "id": f"recovery-{code}-{index}",
                    "text": text,
                    "intent": code,
                    "kind": "IN_SCOPE",
                    "family": f"recovery-authored:{code}:{index}",
                    "source": "AGENT_AUTHORED_RECOVERY",
                    "human_reviewed": False,
                }
            )
    # These are regression data only: previously exposed holdouts, not newly independent evidence.
    forbidden = validation + challenge
    vector = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    vector.fit([normalize(r["text"]) for r in train + forbidden])
    reference = vector.transform([normalize(r["text"]) for r in forbidden])
    scores = linear_kernel(
        vector.transform([normalize(r["text"]) for r in train]), reference
    )
    kept, excluded, seen = [], [], {}
    for i, row in enumerate(train):
        key = re.sub(r"[^\w\s]", " ", normalize(row["text"]))
        key = " ".join(key.split())
        nearest = int(scores[i].argmax())
        if key in seen:
            if seen[key] != row["intent"]:
                raise ValueError("Contradictory labels for " + key)
            excluded.append(
                {
                    "id": row["id"],
                    "intent": row["intent"],
                    "reason": "duplicate_training_text",
                }
            )
        elif float(scores[i, nearest]) >= 0.85:
            excluded.append(
                {
                    "id": row["id"],
                    "intent": row["intent"],
                    "reason": "holdout_near_overlap",
                    "similarity": float(scores[i, nearest]),
                    "text": row["text"],
                    "heldout_id": forbidden[nearest]["id"],
                }
            )
        else:
            kept.append(row)
            seen[key] = row["intent"]
    partitions = {
        "train": kept,
        "validation": validation,
        "synthetic_challenge": challenge,
    }
    family_split, exact_split = {}, {}
    files = {}
    for split, records in partitions.items():
        for row in records:
            row.update(
                split=split,
                human_reviewed=False,
                review_status="PENDING_HUMAN_REVIEW",
                normalized_text=normalize(row["text"]),
            )
            row["group_id"] = row.get("family", row["id"])
            for key, store in [
                (row["group_id"], family_split),
                (row["normalized_text"], exact_split),
            ]:
                if key in store and store[key] != split:
                    raise ValueError("Cross-split leakage " + key)
                store[key] = split
        path = FOLDER / (split + ".jsonl")
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
            encoding="utf-8",
        )
        files[split] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha(path),
            "count": len(records),
            "intent_counts": dict(
                Counter(r["intent"] for r in records if r["kind"] == "IN_SCOPE")
            ),
            "out_of_scope": sum(r["kind"] == "OUT_OF_SCOPE" for r in records),
        }
    # Non-standalone examples remain separate and never enter either 60-way loss.
    contextual = [
        r
        for r in rows(ROOT / "training/datasets/generated/2b-v1/contextual.jsonl")
        if r.get("text")
    ]
    multi = rows(ROOT / "training/datasets/generated/2b-v1/multi_intent.jsonl")
    for name, data in [("contextual", contextual), ("multi_intent", multi)]:
        (FOLDER / (name + ".jsonl")).write_text(
            "".join(json.dumps(dict(r, human_reviewed=False)) + "\n" for r in data),
            encoding="utf-8",
        )
    dump(
        FOLDER / "leakage-audit.json",
        {
            "cutoff": 0.85,
            "excluded_training": excluded,
            "heldout_questions_not_used_as_training": True,
            "family_policy": "Preserve prior families; newly authored sentence families and all placeholder variants remain train-only",
            "semantic_independence": "Not established; synthetic sets share taxonomy concepts and authorship",
            "validation_challenge_relation": "Inherited frozen split family/exact checks; no human independence claimed",
        },
    )
    counts = files["train"]["intent_counts"]
    manifest = {
        "version": "recovery-60-v3",
        "files": files,
        "labels": labels,
        "review_status": "ALL_SYNTHETIC_PENDING_HUMAN_REVIEW",
        "independent_human_test": 0,
        "minimum_train_examples": min(counts.values()),
        "under_30": {c: counts.get(c, 0) for c in labels if counts.get(c, 0) < 30},
        "vocabulary_sha256": sha(vocab_path),
        "bank_sha256": sha(FOLDER / "train-bank.txt"),
        "audit_sha256": sha(FOLDER / "leakage-audit.json"),
        "challenge_role": "Previously exposed synthetic regression holdout; never used to tune recovery models",
        "contextual_count": len(contextual),
        "multi_intent_count": len(multi),
        "progressive_target": 200,
        "promotion_eligible": False,
    }
    dump(FOLDER / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "counts": {s: x["count"] for s, x in files.items()},
                "minimum_train_examples": manifest["minimum_train_examples"],
                "under_30": manifest["under_30"],
                "excluded": len(excluded),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    prepare()
