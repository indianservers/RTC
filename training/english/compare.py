from typing import Any

"""Evaluate all candidates on the identical synthetic holdouts, without promotion."""

import json
import statistics
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import psutil
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline

enforce_offline()
from app.domain import database
from app.nlp.components import IntentClassifier, LanguageNormalizer
from app.nlp.content import NLPContentRepository
from sqlalchemy.orm import Session

folder = ROOT / "models/english/nlp/grouped-60-v1"
manifest = json.loads(
    (ROOT / "training/datasets/splits/2c-v1/manifest.json").read_text()
)
labels = json.loads((folder / "label_map.json").read_text())
models = {}
report: dict[str,Any] = {}
start = time.perf_counter()
models["svm"] = joblib.load(folder / "svm.joblib")
svm_load = time.perf_counter() - start
start = time.perf_counter()
models["textcnn"] = tf.keras.models.load_model(folder / "textcnn.keras")
cnn_load = time.perf_counter() - start
with Session(database()) as s:
    rules = NLPContentRepository(s).rules()
baseline = IntentClassifier(rules)
for split, metadata in manifest["files"].items():
    all_rows = [
        json.loads(x)
        for x in (ROOT / metadata["path"]).read_text(encoding="utf-8").splitlines()
    ]
    rows = [
        r
        for r in all_rows
        if len(r["intent_codes"]) == 1
        and r["dataset_type"] in ("SINGLE_INTENT", "ASR_STYLE")
    ]
    texts = [r["text"] for r in rows]
    truth = [r["intent_codes"][0] for r in rows]
    results = {}
    for name in ["svm", "textcnn", "deterministic_rule_only"]:
        start = time.perf_counter()
        if name == "svm":
            pred = models[name].predict(texts).tolist()
        elif name == "textcnn":
            pred = [
                labels[int(i)]
                for i in models[name](tf.constant(texts), training=False)
                .numpy()
                .argmax(axis=1)
            ]
        else:
            matches = [
                baseline.classify(LanguageNormalizer().normalize(text))
                for text in texts
            ]
            pred = [
                r[0] if len(r) == 1 else "AMBIGUOUS" if r else "UNKNOWN"
                for r in matches
            ]
        elapsed = time.perf_counter() - start
        results[name] = {
            "accuracy": accuracy_score(truth, pred),
            "classification_report": classification_report(
                truth, pred, labels=labels, output_dict=True, zero_division=0
            ),
            "confusion_labels": labels + ["UNKNOWN", "AMBIGUOUS"],
            "confusion_matrix": confusion_matrix(
                truth, pred, labels=labels + ["UNKNOWN", "AMBIGUOUS"]
            ).tolist(),
            "batch_ms_per_example": elapsed * 1000 / len(rows),
            "count": len(rows),
        }
    report[split] = results
    if split == "validation":
        margins = models["svm"].decision_function(texts)
        top = margins.max(axis=1)
        prediction = models["svm"].predict(texts)
        thresholds = []
        for threshold in sorted({float(x) for x in top}):
            mask = top >= threshold
            support = int(mask.sum())
            precision = float((prediction[mask] == np.asarray(truth)[mask]).mean())
            if support >= 10 and precision >= 0.95:
                thresholds.append(
                    {
                        "decision_threshold": threshold,
                        "validation_precision": precision,
                        "validation_support": support,
                        "validation_coverage": support / len(rows),
                    }
                )
        report["calibration"] = {
            "type": "SVM_DECISION_MARGIN_NOT_PROBABILITY",
            "high_confidence_candidate": thresholds[0] if thresholds else None,
            "policy": "At least ten accepted validation examples at >=0.95 validation precision; no independent safety claim",
            "threshold_source": "validation",
            "production_approved": False,
        }
    multi = [r for r in all_rows if r["dataset_type"] == "MULTI_INTENT"]
    if multi:
        exact = sum(
            set(baseline.classify(LanguageNormalizer().normalize(r["text"])))
            == set(r["intent_codes"])
            for r in multi
        )
        report["multi_intent_rule_only"] = {
            "count": len(multi),
            "exact_match_accuracy": exact / len(multi),
            "statistical_models": "NOT_EVALUATED_SINGLE_LABEL_MODELS",
        }
    outside = [r for r in all_rows if r["dataset_type"] == "OUT_OF_SCOPE"]
    if outside:
        report["out_of_scope_rule_only"] = {
            "count": len(outside),
            "rejection_rate": sum(
                not baseline.classify(LanguageNormalizer().normalize(r["text"]))
                for r in outside
            )
            / len(outside),
        }
warm = {}
for name, model in models.items():
    samples = []
    for _ in range(30):
        start = time.perf_counter()
        if name == "svm":
            model.predict(["When is the next bus?"])
        else:
            model(tf.constant(["When is the next bus?"]), training=False)
        samples.append((time.perf_counter() - start) * 1000)
    warm[name] = {
        "p50_ms": statistics.median(samples),
        "p95_ms": sorted(samples)[28],
        "bytes": (folder / ("svm.joblib" if name == "svm" else "textcnn.keras"))
        .stat()
        .st_size,
    }
report["benchmark"] = {
    "warm": warm,
    "cold_load_seconds": {"svm": svm_load, "textcnn": cnn_load},
    "peak_process_memory_bytes": psutil.Process().memory_info().peak_wset,
}
score = lambda name: report["validation"][name]["classification_report"]["macro avg"][
    "f1-score"
]
report["development_winner"] = max(models, key=score)
report["production_selection"] = None
report["limitations"] = [
    "All holdouts synthetic/unreviewed",
    "No independent test exists",
    "Production deterministic exact-taxonomy-example lookup excluded because it has access to these seed questions",
    "Tiny corpus cannot establish 0.95 real-world target",
    "No OS-level network isolation",
    "Python socket blocking verified during local checkpoint loading/inference",
]
(folder / "comparison.json").write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "validation_macro_f1": {name: score(name) for name in report["validation"]},
            "synthetic_challenge_macro_f1": {
                name: report["synthetic_challenge"][name]["classification_report"][
                    "macro avg"
                ]["f1-score"]
                for name in report["synthetic_challenge"]
            },
            "development_winner": report["development_winner"],
            "calibration": report["calibration"],
            "benchmark": report["benchmark"],
        },
        indent=2,
    )
)
