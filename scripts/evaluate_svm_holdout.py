"""Frozen evaluation only: no fitting, threshold selection, registry mutation or promotion."""

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from offline_guard import enforce_offline

enforce_offline()
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.metrics.pairwise import linear_kernel


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in text).split())


def strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("text", "question", "utterance") and isinstance(v, str):
                yield v
            elif k == "examples" and isinstance(v, list):
                yield from (x for x in v if isinstance(x, str))
            elif isinstance(v, (dict, list)):
                yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def wilson(success, total):
    if not total:
        return None
    z = 1.959963984540054
    p = success / total
    den = 1 + z * z / total
    middle = (p + z * z / (2 * total)) / den
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return [middle - radius, middle + radius]


def main():
    folder = ROOT / "evaluation/english-svm-v1"
    test = folder / "holdout.jsonl"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert sha(test) == manifest["sha256"], "Frozen evaluation checksum changed"
    rows = [json.loads(x) for x in test.read_text(encoding="utf-8").splitlines()]
    taxonomy = json.loads(
        (ROOT / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
    )
    labels = sorted(r["code"] for r in taxonomy["intents"])
    aliases = taxonomy["legacy_aliases"]
    assert len(labels) == 60 and len(rows) == 200
    assert Counter(
        r["expected_intents"][0] for r in rows if r["type"] == "SINGLE_INTENT"
    ) == Counter({label: 3 for label in labels})
    assert len({normalize(r["text"]) for r in rows}) == len(rows)
    # Freeze audit criteria before any model is loaded: exclude exact or >=0.85 character ngram similarity.
    sources = sorted(
        [
            *ROOT.glob("training/datasets/**/*.jsonl"),
            ROOT / "training/config/intent_registry.yaml",
            ROOT / "config/nlp_rules.json",
        ]
    )
    seen = {}
    hashes = {}
    for path in sources:
        hashes[path.relative_to(ROOT).as_posix()] = sha(path)
        try:
            values = (
                [
                    json.loads(x)
                    for x in path.read_text(encoding="utf-8-sig").splitlines()
                ]
                if path.suffix == ".jsonl"
                else [json.loads(path.read_text(encoding="utf-8-sig"))]
            )
            texts = [t for value in values for t in strings(value)]
            if path.name == "nlp_rules.json":
                texts += [s for group in values[0].values() for s in group]
            for text in texts:
                seen.setdefault(normalize(text), str(path.relative_to(ROOT)))
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError(f"Cannot audit {path}: {exc}") from exc
    corpus = list(seen)
    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), max_features=40000
    )
    vectors = vectorizer.fit_transform(corpus)
    similarities = linear_kernel(
        vectorizer.transform([normalize(r["text"]) for r in rows]), vectors
    )
    for i, r in enumerate(rows):
        j = int(similarities[i].argmax())
        r["audit"] = {
            "exact_overlap": normalize(r["text"]) in seen,
            "nearest_similarity": float(similarities[i, j]),
            "nearest_text": corpus[j],
            "nearest_source": seen[corpus[j]],
        }
        r["eligible"] = (
            not r["audit"]["exact_overlap"] and r["audit"]["nearest_similarity"] < 0.85
        )
    registry = ROOT / "config/model_registry.yaml"
    registry_sha = sha(registry)
    report = {
        "protocol": manifest,
        "network": "Python socket egress denied; not OS isolation",
        "audit_threshold": 0.85,
        "audited_training_files": hashes,
        "unique_source_texts": len(corpus),
        "exact_overlap_count": sum(r["audit"]["exact_overlap"] for r in rows),
        "near_overlap_count": sum(
            not r["audit"]["exact_overlap"] and not r["eligible"] for r in rows
        ),
        "review_status": "Agent-authored, not human-adjudicated or field-collected; lexical overlap audit does not prove semantic independence.",
        "models": {},
    }
    for version in ("pilot-v2", "grouped-60-v1"):
        path = ROOT / f"models/english/nlp/{version}/svm.joblib"
        digest = sha(path)
        start = perf_counter()
        model = joblib.load(path)
        load = perf_counter() - start
        model.predict([rows[0]["text"]])
        predictions = []
        latencies = []
        for row in rows:
            start = perf_counter()
            pred = str(model.predict([row["text"]])[0])
            latencies.append((perf_counter() - start) * 1000)
            predictions.append(aliases.get(pred, pred))
        indices = [
            i
            for i, r in enumerate(rows)
            if r["type"] == "SINGLE_INTENT" and r["eligible"]
        ]
        truth = [rows[i]["expected_intents"][0] for i in indices]
        pred = [predictions[i] for i in indices]
        correct = sum(a == b for a, b in zip(truth, pred))
        scores = classification_report(
            truth, pred, labels=labels, zero_division=0, output_dict=True
        )
        oos = [
            i
            for i, r in enumerate(rows)
            if r["type"] == "OUT_OF_SCOPE" and r["eligible"]
        ]
        result = {
            "artifact": str(path.relative_to(ROOT)),
            "sha256": digest,
            "model_classes": list(map(str, model.classes_)),
            "class_count": len(model.classes_),
            "single_intent_evaluated": len(indices),
            "correct": correct,
            "accuracy": accuracy_score(truth, pred),
            "accuracy_wilson_95": wilson(correct, len(indices)),
            "macro_f1_60_labels": scores["macro avg"]["f1-score"],
            "per_class": {label: scores[label] for label in labels},
            "confusion_matrix": confusion_matrix(
                truth, pred, labels=sorted(set(labels) | set(pred))
            ).tolist(),
            "confusion_labels": sorted(set(labels) | set(pred)),
            "predicted_labels_outside_taxonomy": sorted(set(pred) - set(labels)),
            "out_of_scope_count": len(oos),
            "out_of_scope_false_accepts": len(oos),
            "out_of_scope_policy": "Forced-choice SVM predict has no abstention. No new threshold was selected; every OOS question receives a bus-intent label.",
            "load_seconds": load,
            "latency_median_ms": sorted(latencies)[len(latencies) // 2],
            "latency_p95_ms": sorted(latencies)[int(0.95 * len(latencies)) - 1],
            "records": [
                dict(
                    row,
                    predicted_intent=predictions[i],
                    correct=predictions[i] in row["expected_intents"],
                )
                for i, row in enumerate(rows)
            ],
            "promotion": "NONE; registry and artifacts unchanged",
        }
        assert sha(path) == digest
        report["models"][version] = result
    assert sha(registry) == registry_sha and sha(test) == manifest["sha256"]
    (folder / "results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Frozen English SVM held-out evaluation",
        "",
        "New agent-authored English questions; not human-reviewed or an independent field study. No retraining, threshold tuning or promotion.",
        "",
        f"Overlap audit: {report['exact_overlap_count']} exact and {report['near_overlap_count']} near-overlap rows excluded from primary scores; character ngram similarity cutoff 0.85.",
        "",
    ]
    for name, r in report["models"].items():
        lines += [
            f"## {name}",
            "",
            f"- Classes: {r['class_count']}; scored questions: {r['single_intent_evaluated']}.",
            f"- Accuracy: {r['correct']}/{r['single_intent_evaluated']} ({r['accuracy']:.2%}); Wilson 95% interval {r['accuracy_wilson_95'][0]:.2%}–{r['accuracy_wilson_95'][1]:.2%}.",
            f"- Macro F1 across 60 canonical labels: {r['macro_f1_60_labels']:.4f}.",
            f"- Out-of-scope false accepts: {r['out_of_scope_false_accepts']}/{r['out_of_scope_count']} with forced-choice predict; no rejection mechanism tested.",
            f"- Warm prediction median {r['latency_median_ms']:.3f} ms, p95 {r['latency_p95_ms']:.3f} ms.",
            "- Full per-class metrics, confusion matrix, source hashes and all predictions: results.json.",
            "",
        ]
    lines += [
        "Only three authored samples per class before exclusions; class-level scores are noisy. Related intent definitions share vocabulary. The lexical audit cannot rule out semantic template exposure. These results do not justify activating either candidate.",
        "",
    ]
    (folder / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
