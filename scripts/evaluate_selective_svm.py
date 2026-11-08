"""One-way evaluation of frozen candidates; no fitting or threshold changes."""

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from offline_guard import enforce_offline

enforce_offline()
import joblib
import psutil
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - radius, center + radius]


def main():
    folder = ROOT / "evaluation/english-svm-v2"
    if (folder / "results.json").exists():
        raise SystemExit("Fresh evaluation is frozen; do not overwrite or tune on it")
    manifest = load(folder / "manifest.json")
    datafile = folder / "holdout.jsonl"
    eligiblefile = folder / "eligibility.json"
    assert (
        sha(datafile) == manifest["sha256"]
        and sha(eligiblefile) == manifest["eligibility_sha256"]
    )
    assert (
        sha(ROOT / "training/datasets/selective-60-v2/manifest.json")
        == manifest["training_manifest_sha256"]
    )
    eligibility = load(eligiblefile)
    records = [
        json.loads(line) for line in datafile.read_text(encoding="utf-8").splitlines()
    ]
    records = [r for r in records if eligibility[r["id"]]]
    id_indices = [i for i, r in enumerate(records) if r["kind"] == "IN_SCOPE"]
    out_indices = [i for i, r in enumerate(records) if r["kind"] == "OUT_OF_SCOPE"]
    checkpoint = ROOT / "models/english/nlp/selective-60-v2"
    descriptor = load(checkpoint / "descriptor.json")
    labels = load(checkpoint / "label_map.json")
    assert len(labels) == 60
    assert sha(checkpoint / "svm.joblib") == descriptor["sha256"]
    registry = ROOT / "config/model_registry.yaml"
    registry_hash = sha(registry)
    report = {
        "protocol": "Training and thresholds frozen before reading fresh test questions. Agent-authored synthetic labels; not human adjudicated.",
        "test_manifest": manifest,
        "checkpoint_descriptor_sha256": sha(checkpoint / "descriptor.json"),
        "models": {},
        "registry_sha256_before": registry_hash,
        "network": "Python socket egress blocked; not OS-isolated",
    }
    for name, artifact in [
        ("grouped-60-v1", ROOT / "models/english/nlp/grouped-60-v1/svm.joblib"),
        ("selective-60-v2", checkpoint / "svm.joblib"),
    ]:
        digest = sha(artifact)
        start = perf_counter()
        model = joblib.load(artifact)
        load_seconds = perf_counter() - start
        assert list(model.classes_) == labels
        raw = list(map(str, model.predict([r["text"] for r in records])))
        if hasattr(model, "predict_selective"):
            model.predict_selective([records[0]["text"]])
        else:
            model.predict([records[0]["text"]])
        preds = []
        latencies = []
        for row in records:
            start = perf_counter()
            pred = (
                model.predict_selective([row["text"]])[0]
                if hasattr(model, "predict_selective")
                else {
                    "status": "KNOWN",
                    "intents": [str(model.predict([row["text"]])[0])],
                }
            )
            latencies.append((perf_counter() - start) * 1000)
            preds.append(pred)
        truth = [records[i]["intent"] for i in id_indices]
        raw_id = [raw[i] for i in id_indices]
        selective_id = [
            preds[i]["intents"][0] if preds[i]["status"] == "KNOWN" else "__REJECTED__"
            for i in id_indices
        ]
        accepted = [i for i in id_indices if preds[i]["status"] == "KNOWN"]
        correct = sum(preds[i]["intents"] == [records[i]["intent"]] for i in accepted)
        out_accepted = [i for i in out_indices if preds[i]["status"] == "KNOWN"]
        false_rejects = len(id_indices) - len(accepted)
        metrics = classification_report(
            truth, raw_id, labels=labels, output_dict=True, zero_division=0
        )
        selective_metrics = classification_report(
            truth, selective_id, labels=labels, output_dict=True, zero_division=0
        )
        id_acc = accuracy_score(truth, raw_id)
        result = {
            "artifact": artifact.relative_to(ROOT).as_posix(),
            "sha256": digest,
            "class_count": len(labels),
            "id_count": len(id_indices),
            "out_of_scope_count": len(out_indices),
            "closed_set_accuracy": id_acc,
            "closed_set_correct": sum(
                a == b for a, b in zip(truth, raw_id, strict=True)
            ),
            "closed_set_accuracy_wilson_95": wilson(
                sum(a == b for a, b in zip(truth, raw_id, strict=True)), len(id_indices)
            ),
            "closed_set_macro_f1": metrics["macro avg"]["f1-score"],
            "id_accepted": len(accepted),
            "id_rejected": false_rejects,
            "id_acceptance_coverage": len(accepted) / len(id_indices),
            "accepted_id_correct": correct,
            "accepted_id_accuracy": correct / len(accepted) if accepted else None,
            "correct_acceptance_coverage": correct / len(id_indices),
            "selective_macro_f1": selective_metrics["macro avg"]["f1-score"],
            "oos_false_accepted": len(out_accepted),
            "oos_false_accept_rate": len(out_accepted) / len(out_indices),
            "oos_rejected": len(out_indices) - len(out_accepted),
            "oos_rejection_rate": 1 - len(out_accepted) / len(out_indices),
            "oos_false_accept_wilson_95": wilson(len(out_accepted), len(out_indices)),
            "in_scope_acceptance_precision": len(accepted)
            / (len(accepted) + len(out_accepted))
            if accepted or out_accepted
            else None,
            "balanced_scope_accuracy": 0.5
            * (
                len(accepted) / len(id_indices)
                + 1
                - len(out_accepted) / len(out_indices)
            ),
            "overall_decision_accuracy": (
                correct + len(out_indices) - len(out_accepted)
            )
            / len(records),
            "per_class_closed": metrics,
            "per_class_selective": selective_metrics,
            "confusion_labels": labels + ["__REJECTED__"],
            "confusion_matrix": confusion_matrix(
                truth, selective_id, labels=labels + ["__REJECTED__"]
            ).tolist(),
            "load_seconds": load_seconds,
            "latency_median_ms": statistics.median(latencies),
            "latency_p95_ms": sorted(latencies)[int(0.95 * len(latencies)) - 1],
            "process_memory_bytes": psutil.Process().memory_info().rss,
            "records": [
                dict(r, raw_intent=raw[i], prediction=preds[i])
                for i, r in enumerate(records)
            ],
        }
        assert sha(artifact) == digest
        report["models"][name] = result
    old = report["models"]["grouped-60-v1"]["records"]
    new = report["models"]["selective-60-v2"]["records"]
    report["paired_closed_set_comparison"] = {
        "baseline_errors_fixed": sum(
            a["raw_intent"] != a["intent"] and b["raw_intent"] == b["intent"]
            for a, b in zip(old, new, strict=True)
            if a["kind"] == "IN_SCOPE"
        ),
        "new_errors_introduced": sum(
            a["raw_intent"] == a["intent"] and b["raw_intent"] != b["intent"]
            for a, b in zip(old, new, strict=True)
            if a["kind"] == "IN_SCOPE"
        ),
    }
    assert sha(registry) == registry_hash
    report["registry_sha256_after"] = sha(registry)
    (folder / "results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Fresh held-out selective SVM evaluation",
        "",
        "New agent-authored English questions, frozen before training. Not a human-reviewed or field-collected benchmark. Neither the old evaluation set nor fresh-test results were used to train or calibrate this candidate.",
        "",
    ]
    for name, r in report["models"].items():
        lines += [
            "## " + name,
            "",
            f"- Closed-set intent accuracy: {r['closed_set_correct']}/{r['id_count']} ({r['closed_set_accuracy']:.2%}); macro F1 {r['closed_set_macro_f1']:.4f}.",
            f"- In-scope accepted: {r['id_accepted']}/{r['id_count']} ({r['id_acceptance_coverage']:.2%}). Accepted-ID accuracy: {r['accepted_id_accuracy']:.2%}.",
            f"- Correctly accepted ID / all ID: {r['accepted_id_correct']}/{r['id_count']} ({r['correct_acceptance_coverage']:.2%}). Selective macro F1 (rejections count against recall): {r['selective_macro_f1']:.4f}.",
            f"- OOS rejected: {r['oos_rejected']}/{r['out_of_scope_count']} ({r['oos_rejection_rate']:.2%}); false accepts {r['oos_false_accepted']} ({r['oos_false_accept_rate']:.2%}).",
            f"- Overall decision accuracy, including rejected OOS and counting rejected ID as errors: {r['overall_decision_accuracy']:.2%}.",
            f"- Warm prediction median {r['latency_median_ms']:.3f} ms, p95 {r['latency_p95_ms']:.3f} ms.",
            "",
        ]
    lines += [
        "Per-class metrics, confusion matrices, hashes, margins and every raw/selective prediction are in results.json. Rejection thresholds were selected only on validation. Only three questions per intent and 60 OOS questions were tested; results do not establish field accuracy or certify a population false-acceptance limit. No checkpoint or approval registry entry was changed by evaluation.",
        "",
    ]
    (folder / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
