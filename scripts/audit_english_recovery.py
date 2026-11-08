"""Measure existing corpus problems before changing or training any candidate."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline


def run():
    enforce_offline()
    import joblib
    from app.domain import Alias, Category, Station, database
    from sklearn.metrics import classification_report
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    output = ROOT / "evaluation/english-recovery-v3"
    output.mkdir(parents=True, exist_ok=True)
    old = ROOT / "training/datasets/splits/2c-v1"
    data = {
        p.stem: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
        for p in old.glob("*.jsonl")
    }
    eligible = {
        s: [
            r
            for r in rows
            if len(r["intent_codes"]) == 1
            and r["dataset_type"] in {"SINGLE_INTENT", "ASR_STYLE"}
        ]
        for s, rows in data.items()
    }
    labels = sorted(
        r["code"]
        for r in json.loads(
            (ROOT / "training/config/intent_registry.yaml").read_text()
        )["intents"]
    )
    train_counts = Counter(r["intent_codes"][0] for r in eligible["train"])
    validation = eligible["validation"]
    model = joblib.load(ROOT / "models/english/nlp/grouped-60-v1/svm.joblib")
    truth = [r["intent_codes"][0] for r in validation]
    predictions = model.predict([r["text"] for r in validation])
    metrics = classification_report(
        truth, predictions, labels=labels, output_dict=True, zero_division=0
    )
    train_vocab = set(
        re.findall(r"[a-z]+", " ".join(r["text"].lower() for r in eligible["train"]))
    )
    tokens = re.findall(r"[a-z]+", " ".join(r["text"].lower() for r in validation))
    flags = []
    for split, rows in eligible.items():
        for row in rows:
            if re.fullmatch(
                r"(what about tomorrow|no tirumala|second one|how much|same bus)[?.! ]*",
                row["text"].lower(),
            ):
                flags.append(
                    {
                        "split": split,
                        "text": row["text"],
                        "label": row["intent_codes"],
                        "issue": "Context-dependent; exclude from standalone classifier",
                    }
                )
    registry = json.loads((ROOT / "training/config/intent_registry.yaml").read_text())[
        "intents"
    ]
    engine = database()
    try:
        with Session(engine) as db:
            vocab = {
                "stations": sorted(
                    set(
                        db.scalars(select(Station.name).where(Station.active.is_(True)))
                    )
                ),
                "aliases": sorted(
                    set(db.scalars(select(Alias.name).where(Alias.active.is_(True))))
                ),
                "categories": sorted(
                    set(
                        db.scalars(
                            select(Category.name).where(Category.active.is_(True))
                        )
                    )
                ),
            }
    finally:
        engine.dispose()
    (output / "db-vocabulary.json").write_text(
        json.dumps(vocab, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report = {
        "source": "ACTUAL_LOCAL_FILES_AND_DATABASE",
        "human_reviewed_independent_test_count": 0,
        "eligible_counts": {s: len(r) for s, r in eligible.items()},
        "per_intent": {
            c: {
                "train_count": train_counts[c],
                "validation_count": sum(t == c for t in truth),
                "validation_f1": metrics[c]["f1-score"],
                "confusions": dict(
                    Counter(
                        p
                        for t, p in zip(truth, predictions, strict=True)
                        if t == c and p != c
                    )
                ),
                "definition": next(r["definition"] for r in registry if r["code"] == c),
            }
            for c in labels
        },
        "validation_unseen_token_fraction": sum(t not in train_vocab for t in tokens)
        / len(tokens),
        "unseen_validation_tokens": Counter(
            t for t in tokens if t not in train_vocab
        ).most_common(50),
        "context_label_flags": flags,
        "missing_training_classes": sorted(set(labels) - set(train_counts)),
        "findings": [
            "Sparse support per class, not missing 60-class output coverage",
            "Old TextCNN trained with 234 texts and 60 outputs; vocabulary/sequence configuration far exceeds effective supervision",
            "Original trainer records nfkc-casefold preprocessing metadata but passes raw strings to estimators; normalize explicitly in recovery corpus",
            "Standalone SVM forces OOS into a transport label; use validation-only rejection calibration",
            "Boarding versus platform, arrival schedule versus live ETA, facilities versus navigation, policy versus action, direct versus reachability require contrastive boundaries",
            "Existing generated record count is not semantic family diversity; preserve grouping and count eligible classifier rows",
            "No independent human-reviewed test set; no promotion conclusion from synthetic metrics",
        ],
    }
    (output / "dataset-audit.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "eligible_counts",
                    "missing_training_classes",
                    "validation_unseen_token_fraction",
                    "human_reviewed_independent_test_count",
                ]
            }
        )
    )


if __name__ == "__main__":
    run()
