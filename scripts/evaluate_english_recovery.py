"""Identical frozen synthetic evaluation; no training, threshold retuning or activation."""

import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline
from prepare_english_recovery import dump, rows, sha


def main():
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "4")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
    enforce_offline()
    import joblib
    import numpy as np
    import psutil
    import tensorflow as tf
    from app.domain import database
    from app.nlp.components import IntentClassifier
    from app.nlp.content import NLPContentRepository
    from app.nlp.taxonomy import IntentRegistry
    from app.nlp.text_support import classify_extra
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sqlalchemy.orm import Session

    folder = ROOT / "models/english/nlp/recovery-60-v3"
    target = ROOT / "evaluation/english-recovery-v3"
    manifest = json.loads(
        (ROOT / "training/datasets/recovery-60-v3/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    labels = manifest["labels"]
    process = psutil.Process()
    partitions = {}
    for split in ["validation", "synthetic_challenge"]:
        path = ROOT / manifest["files"][split]["path"]
        if sha(path) != manifest["files"][split]["sha256"]:
            raise ValueError("Frozen evaluation checksum differs")
        partitions[split] = rows(path)
    engine = database()
    session = Session(engine)
    rules = IntentClassifier(NLPContentRepository(session).rules())
    taxonomy = IntentRegistry(session)

    def deterministic(texts):
        result = []
        for text in texts:
            hits = classify_extra(text, rules.classify(text), session)
            canonical = {spec.code if (spec := taxonomy.get(i)) else i for i in hits}
            result.append(
                next(iter(canonical))
                if len(canonical) == 1 and next(iter(canonical)) in labels
                else "CLARIFICATION_REQUIRED"
                if canonical
                else "UNKNOWN"
            )
        return np.array(result)

    artifacts = {
        "grouped_svm": ROOT / "models/english/nlp/grouped-60-v1/svm.joblib",
        "selective_svm_v2": ROOT / "models/english/nlp/selective-60-v2/svm.joblib",
        "new_svm": folder / "svm.joblib",
        "old_textcnn": ROOT / "models/english/nlp/grouped-60-v1/textcnn.keras",
        "new_textcnn": folder / "textcnn.keras",
    }
    models = {}
    loading = {}
    for name, path in artifacts.items():
        before = process.memory_info().rss
        started = perf_counter()
        models[name] = (
            tf.keras.models.load_model(path) if "textcnn" in name else joblib.load(path)
        )
        loading[name] = {
            "artifact": path.relative_to(ROOT).as_posix(),
            "sha256": sha(path),
            "serialized_bytes": path.stat().st_size,
            "load_ms": (perf_counter() - started) * 1000,
            "rss_increment_bytes": process.memory_info().rss - before,
            "process_rss_after_load_bytes": process.memory_info().rss,
        }
    oldlabels = json.loads(
        (ROOT / "models/english/nlp/grouped-60-v1/label_map.json").read_text()
    )
    assert (
        oldlabels == labels
        and list(models["new_svm"].classes_) == labels
        and models["new_textcnn"].output_shape[-1] == 60
    )
    # Calibrate CNN rejection on validation only, before accessing challenge predictions.
    valid = partitions["validation"]
    vtruth = np.array([r["intent"] or "OUT_OF_SCOPE" for r in valid])
    vprob = models["new_textcnn"](
        tf.constant([r["normalized_text"] for r in valid]), training=False
    ).numpy()
    ordered = np.sort(vprob, axis=1)
    raw = np.array(labels)[vprob.argmax(axis=1)]
    outside = vtruth == "OUT_OF_SCOPE"
    candidates = []
    for threshold in [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        for gap in [0, 0.05, 0.1, 0.2, 0.3]:
            accepted = (ordered[:, -1] >= threshold) & (
                (ordered[:, -1] - ordered[:, -2]) >= gap
            )
            support = int((accepted & ~outside).sum())
            correct = int((accepted & (raw == vtruth) & ~outside).sum())
            precision = correct / support if support else 0
            far = float(accepted[outside].mean())
            if support >= 30 and precision >= 0.95 and far <= 0.05:
                candidates.append(
                    {
                        "softmax_threshold": threshold,
                        "gap": gap,
                        "support": support,
                        "precision": precision,
                        "oos_false_accept_rate": far,
                        "correct": correct,
                    }
                )
    calibrated = (
        max(
            candidates,
            key=lambda r: (r["correct"], r["precision"], -r["oos_false_accept_rate"]),
        )
        if candidates
        else None
    )
    dump(
        target / "textcnn-validation-calibration.json",
        {
            "selected": calibrated,
            "score_kind": "UNCALIBRATED_SOFTMAX; thresholds are empirical validation operating points, not calibrated probabilities",
            "independent_evidence": False,
        },
    )

    def predictions(name, texts):
        if name == "deterministic_rules":
            p = deterministic(texts)
            return p, p
        model = models[name]
        if "textcnn" in name:
            probability = model(tf.constant(texts), training=False).numpy()
            ordered = np.sort(probability, axis=1)
            pred = np.array(labels)[probability.argmax(axis=1)]
            selective = pred.copy()
            if name == "new_textcnn":
                rejected = (
                    np.ones(len(texts), dtype=bool)
                    if calibrated is None
                    else (ordered[:, -1] < calibrated["softmax_threshold"])
                    | ((ordered[:, -1] - ordered[:, -2]) < calibrated["gap"])
                )
                selective[rejected] = "CLARIFICATION_REQUIRED"
            return pred, selective
        raw = model.predict(texts)
        if hasattr(model, "predict_selective"):
            decisions = model.predict_selective(texts)
            return raw, np.array(
                [
                    r["intents"][0] if r["status"] == "KNOWN" else r["status"]
                    for r in decisions
                ]
            )
        return raw, raw

    report = {
        "source": "SYNTHETIC_UNREVIEWED_PREVIOUSLY_EXPOSED_REGRESSION_SETS",
        "independent_human_test_count": 0,
        "promotion": "DO_NOT_PROMOTE",
        "manifest_sha256": sha(ROOT / "training/datasets/recovery-60-v3/manifest.json"),
        "loading": loading,
        "models": {},
    }
    for name in ["deterministic_rules", *artifacts]:
        output = {}
        for split, records in partitions.items():
            texts = [r["normalized_text"] for r in records]
            truth = np.array([r["intent"] or "OUT_OF_SCOPE" for r in records])
            inside = truth != "OUT_OF_SCOPE"
            raw, selective = predictions(name, texts)
            acceptance = np.isin(selective, labels)
            times = []
            for index in np.linspace(0, len(texts) - 1, 30, dtype=int):
                started = perf_counter()
                predictions(name, [texts[int(index)]])
                times.append((perf_counter() - started) * 1000)
            output[split] = {
                "count": len(records),
                "in_scope_count": int(inside.sum()),
                "out_of_scope_count": int((~inside).sum()),
                "accuracy": accuracy_score(truth[inside], raw[inside]),
                "per_intent": classification_report(
                    truth[inside],
                    raw[inside],
                    labels=labels,
                    output_dict=True,
                    zero_division=0,
                ),
                "decision_accuracy_with_rejection": float(
                    ((inside & (selective == truth)) | (~inside & ~acceptance)).mean()
                ),
                "selective_per_intent": classification_report(
                    truth[inside],
                    selective[inside],
                    labels=labels,
                    output_dict=True,
                    zero_division=0,
                ),
                "accepted_id_count": int((acceptance & inside).sum()),
                "accepted_id_precision": float(
                    (
                        selective[inside & acceptance] == truth[inside & acceptance]
                    ).mean()
                )
                if (inside & acceptance).any()
                else None,
                "id_rejection_rate": float((~acceptance[inside]).mean()),
                "oos_false_acceptance_rate": float(acceptance[~inside].mean()),
                "confusion_labels": labels
                + ["OUT_OF_SCOPE", "CLARIFICATION_REQUIRED", "UNKNOWN"],
                "confusion_matrix": confusion_matrix(
                    truth,
                    selective,
                    labels=labels
                    + ["OUT_OF_SCOPE", "CLARIFICATION_REQUIRED", "UNKNOWN"],
                ).tolist(),
                "warm_single_p50_ms": float(np.percentile(times, 50)),
                "warm_single_p95_ms": float(np.percentile(times, 95)),
                "process_rss_bytes": process.memory_info().rss,
                "records": [
                    {
                        "id": r["id"],
                        "text": r["text"],
                        "expected": t,
                        "raw_prediction": str(p),
                        "decision": str(s),
                        "correct": bool(t == p),
                    }
                    for r, t, p, s in zip(records, truth, raw, selective, strict=True)
                ],
            }
        report["models"][name] = output
    multi = rows(ROOT / "training/datasets/recovery-60-v3/multi_intent.jsonl")
    multi_results = []
    for row in multi:
        text = row["text"].lower()
        hits = classify_extra(text, rules.classify(text), session)
        canonical = {spec.code if (spec := taxonomy.get(i)) else i for i in hits}
        multi_results.append(
            {
                "text": row["text"],
                "expected": row["intent_codes"],
                "predicted": sorted(canonical),
                "correct": canonical == set(row["intent_codes"]),
            }
        )
    report["composition"] = {
        "rule_exact_match": sum(r["correct"] for r in multi_results)
        / len(multi_results),
        "count": len(multi_results),
        "records": multi_results,
        "statistical_models": "Single-label; deliberately not forced onto multi-intent examples",
    }
    session.close()
    engine.dispose()
    dump(target / "comparison.json", report)
    for name, results in report["models"].items():
        print(
            json.dumps(
                {
                    "model": name,
                    **{
                        s: {
                            "accuracy": r["accuracy"],
                            "macro_f1": r["per_intent"]["macro avg"]["f1-score"],
                            "accepted_id_precision": r["accepted_id_precision"],
                            "id_rejection_rate": r["id_rejection_rate"],
                            "oos_false_acceptance_rate": r["oos_false_acceptance_rate"],
                        }
                        for s, r in results.items()
                    },
                }
            )
        )


if __name__ == "__main__":
    main()
