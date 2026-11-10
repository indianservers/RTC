"""Compare batch memorization and unchanged synthetic holdouts without promotion."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline
from prepare_english_recovery import dump, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="question100-v1")
    parser.add_argument("--previous-version", default="recovery-60-v3")
    args = parser.parse_args()
    for identifier in (args.version, args.previous_version):
        if not identifier or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in identifier
        ):
            parser.error("Versions must be simple identifiers")
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "4")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
    enforce_offline()
    import joblib
    import numpy as np
    import tensorflow as tf
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

    folder = ROOT / "models/english/nlp" / args.version
    out = ROOT / "evaluation" / args.version
    data = ROOT / "training/datasets" / args.version
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    labels = json.loads((folder / "label_map.json").read_text())
    models = {
        "previous_svm": joblib.load(
            ROOT / f"models/english/nlp/{args.previous_version}/svm.joblib"
        ),
        "trained_svm": joblib.load(folder / "svm.joblib"),
        "previous_cnn": tf.keras.models.load_model(
            ROOT / f"models/english/nlp/{args.previous_version}/textcnn.keras"
        ),
        "trained_cnn": tf.keras.models.load_model(folder / "textcnn.keras"),
    }
    partitions = {
        "question100_training_check": [
            r
            for r in rows(data / "train.jsonl")
            if r["id"] in manifest.get("new_classifier_ids", [])
            or (args.version == "question100-v1" and r["id"].startswith("Q"))
        ],
        "validation": rows(data / "validation.jsonl"),
        "synthetic_holdout": rows(data / "synthetic_challenge.jsonl"),
    }
    # CNN uncertainty is measured on validation before scoring challenge predictions.
    valid = partitions["validation"]
    truth = np.array([r["intent"] or "OUT_OF_SCOPE" for r in valid])
    inside = truth != "OUT_OF_SCOPE"
    scores = models["trained_cnn"](
        tf.constant([r["normalized_text"] for r in valid]), training=False
    ).numpy()
    ordered = np.sort(scores, axis=1)
    pred = np.array(labels)[scores.argmax(axis=1)]
    operating = []
    for t in [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        for g in [0, 0.05, 0.1, 0.2, 0.3]:
            accepted = (ordered[:, -1] >= t) & ((ordered[:, -1] - ordered[:, -2]) >= g)
            support = int((accepted & inside).sum())
            correct = int((accepted & inside & (pred == truth)).sum())
            precision = correct / support if support else 0
            far = float(accepted[~inside].mean())
            if support >= 30 and precision >= 0.95 and far <= 0.05:
                operating.append(
                    {
                        "softmax_threshold": t,
                        "gap": g,
                        "support": support,
                        "precision": precision,
                        "oos_false_acceptance": far,
                        "correct": correct,
                    }
                )
    calibration = (
        max(operating, key=lambda r: (r["correct"], r["precision"]))
        if operating
        else None
    )
    report = {
        "training_check_warning": "Questions Q001-Q100 were supplied for training; these checks are not independent accuracy",
        "human_reviewed": False,
        "cnn_calibration": calibration,
        "models": {},
    }
    for name, model in models.items():
        results = {}
        for split, records in partitions.items():
            texts = [r["normalized_text"] for r in records]
            truth = np.array([r["intent"] or "OUT_OF_SCOPE" for r in records])
            inside = truth != "OUT_OF_SCOPE"
            if "cnn" in name:
                scores = model(tf.constant(texts), training=False).numpy()
                pred = np.array(labels)[scores.argmax(axis=1)]
                decisions = pred.copy()
                if name == "trained_cnn":
                    ordered = np.sort(scores, axis=1)
                    rejected = (
                        np.ones(len(texts), dtype=bool)
                        if calibration is None
                        else (ordered[:, -1] < calibration["softmax_threshold"])
                        | ((ordered[:, -1] - ordered[:, -2]) < calibration["gap"])
                    )
                    decisions[rejected] = "CLARIFICATION_REQUIRED"
                else:
                    decisions[:] = (
                        "CLARIFICATION_REQUIRED"  # v3 calibration failed; preserve its reject-all policy
                    )
            else:
                pred = model.predict(texts)
                decisions = np.array(
                    [
                        d["intents"][0] if d["status"] == "KNOWN" else d["status"]
                        for d in model.predict_selective(texts)
                    ]
                )
            accepted = np.isin(decisions, labels)
            results[split] = {
                "count": len(records),
                "in_scope_count": int(inside.sum()),
                "raw_in_scope_accuracy": accuracy_score(truth[inside], pred[inside]),
                "per_intent": classification_report(
                    truth[inside],
                    pred[inside],
                    labels=labels,
                    zero_division=0,
                    output_dict=True,
                ),
                "accepted_id": int((accepted & inside).sum()),
                "accepted_id_precision": float(
                    (decisions[accepted & inside] == truth[accepted & inside]).mean()
                )
                if (accepted & inside).any()
                else None,
                "oos_false_acceptance": float(accepted[~inside].mean()),
                "decisions_correct_including_rejected_oos": int(
                    ((inside & (decisions == truth)) | (~inside & ~accepted)).sum()
                ),
                "confusion_labels": labels + ["OUT_OF_SCOPE", "CLARIFICATION_REQUIRED"],
                "confusion_matrix": confusion_matrix(
                    truth,
                    decisions,
                    labels=labels + ["OUT_OF_SCOPE", "CLARIFICATION_REQUIRED"],
                ).tolist(),
                "records": [
                    {
                        "id": r["id"],
                        "expected": t,
                        "raw_prediction": str(p),
                        "decision": str(d),
                    }
                    for r, t, p, d in zip(records, truth, pred, decisions, strict=True)
                ],
            }
        report["models"][name] = results
    dump(out / "model-comparison.json", report)
    print(
        json.dumps(
            {
                name: {
                    s: {
                        k: r[k]
                        for k in [
                            "count",
                            "raw_in_scope_accuracy",
                            "accepted_id",
                            "accepted_id_precision",
                            "oos_false_acceptance",
                        ]
                    }
                    for s, r in splits.items()
                }
                for name, splits in report["models"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
