"""Train/calibrate using frozen train+validation only. Never opens fresh-test questions."""

import argparse
import hashlib
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from offline_guard import enforce_offline

enforce_offline()
import joblib
import numpy as np
from app.nlp.selective_svm import SelectiveIntentSVM
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def dump(p, data):
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "models/english/nlp/selective-60-v2"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Immutable model version already exists")
    folder = ROOT / "training/datasets/selective-60-v2"
    manifest = load(folder / "manifest.json")
    protocol = load(folder / "protocol.json")
    assert sha(folder / "protocol.json") == manifest["protocol_sha256"]
    assert sha(folder / "leakage-audit.json") == manifest["audit_sha256"]
    data = {}
    for split in ("train", "validation"):
        meta = manifest["files"][split]
        p = ROOT / meta["path"]
        assert sha(p) == meta["sha256"]
        data[split] = [
            json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
        ]
    train, validation = data["train"], data["validation"]
    assert not (
        {r["text"].casefold() for r in train}
        & {r["text"].casefold() for r in validation}
    )
    assert not ({r["family"] for r in train} & {r["family"] for r in validation})
    train_id = [i for i, r in enumerate(train) if r["kind"] == "IN_SCOPE"]
    valid_id = np.array(
        [i for i, r in enumerate(validation) if r["kind"] == "IN_SCOPE"]
    )
    valid_out = np.array(
        [i for i, r in enumerate(validation) if r["kind"] == "OUT_OF_SCOPE"]
    )
    labels = sorted({train[i]["intent"] for i in train_id})
    assert len(labels) == 60
    truth = np.array([r["intent"] or "__OUT_OF_SCOPE__" for r in validation])
    start = perf_counter()
    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True
                ),
            ),
        ]
    )
    vectors = features.fit_transform([r["text"] for r in train])
    valid_vectors = features.transform([r["text"] for r in validation])
    domain = LinearSVC(
        C=1.0, class_weight="balanced", random_state=protocol["seed"], max_iter=10000
    )
    domain.fit(vectors, [int(r["kind"] == "IN_SCOPE") for r in train])
    domain_margins = domain.decision_function(valid_vectors)
    configurations = []
    best = None
    best_model = None
    calibration = protocol["rejection_calibration"]
    for C in protocol["model_grid"]["intent_C"]:
        model = LinearSVC(
            C=C, class_weight="balanced", random_state=protocol["seed"], max_iter=10000
        )
        model.fit(vectors[train_id], [train[i]["intent"] for i in train_id])
        scores = model.decision_function(valid_vectors)
        top = scores.argmax(axis=1)
        pred = model.classes_[top]
        ordered = np.sort(scores, axis=1)
        margins = ordered[:, -1]
        gaps = ordered[:, -1] - ordered[:, -2]
        report = classification_report(
            truth[valid_id],
            pred[valid_id],
            labels=labels,
            zero_division=0,
            output_dict=True,
        )
        for domain_t, margin_t, gap_t in itertools.product(
            calibration["domain_thresholds"],
            calibration["top_margin_thresholds"],
            calibration["gap_thresholds"],
        ):
            accepted = (
                (domain_margins >= domain_t) & (margins >= margin_t) & (gaps >= gap_t)
            )
            oos_accepted = int(accepted[valid_out].sum())
            id_accepted = int(accepted[valid_id].sum())
            correct = int(
                (accepted[valid_id] & (pred[valid_id] == truth[valid_id])).sum()
            )
            wrong = id_accepted - correct
            feasible = (
                oos_accepted / len(valid_out)
                <= calibration["max_oos_false_accept_rate"]
                and correct > 0
            )
            row = {
                "C": C,
                "thresholds": {"domain": domain_t, "margin": margin_t, "gap": gap_t},
                "feasible": feasible,
                "id_total": len(valid_id),
                "id_accepted": id_accepted,
                "id_correct_accepted": correct,
                "id_wrong_accepted": wrong,
                "oos_total": len(valid_out),
                "oos_false_accepted": oos_accepted,
                "closed_set_accuracy": accuracy_score(truth[valid_id], pred[valid_id]),
                "closed_set_macro_f1": report["macro avg"]["f1-score"],
            }
            configurations.append(row)
            key = (
                correct,
                -wrong,
                report["macro avg"]["f1-score"],
                -C,
                domain_t,
                gap_t,
                margin_t,
            )
            if feasible and (best is None or key > best[0]):
                best = (key, row)
                best_model = model
    if best is None:
        raise SystemExit(
            "Validation calibration failed; no fresh-test evaluation permitted"
        )
    selected = best[1]
    bundle = SelectiveIntentSVM(features, best_model, domain, selected["thresholds"])
    assert list(bundle.classes_) == labels
    # Persist only after validation selection, before any fresh-test prediction.
    args.output.mkdir(parents=True)
    joblib.dump(bundle, args.output / "svm.joblib")
    dump(args.output / "label_map.json", labels)
    dump(
        args.output / "validation-search.json",
        {
            "protocol_sha256": sha(folder / "protocol.json"),
            "configurations": configurations,
            "selected": selected,
        },
    )
    predictions = bundle.predict_selective([r["text"] for r in validation])
    dump(
        args.output / "validation-predictions.json",
        {
            "records": [
                dict(row, prediction=pred)
                for row, pred in zip(validation, predictions, strict=True)
            ]
        },
    )
    registry = ROOT / "config/model_registry.yaml"
    descriptor = {
        "version": "selective-60-v2",
        "model_type": "english_intent_svm",
        "local_path": (args.output / "svm.joblib").relative_to(ROOT).as_posix(),
        "sha256": sha(args.output / "svm.joblib"),
        "label_map_path": (args.output / "label_map.json").relative_to(ROOT).as_posix(),
        "deployment_status": "CANDIDATE",
        "approved": False,
        "independent_evaluation": False,
        "human_reviewed": False,
        "decision_threshold": selected["thresholds"]["margin"],
        "selective_thresholds": selected["thresholds"],
        "threshold_source": "validation",
        "validation_metrics": selected,
        "training_counts": dict(Counter(r["kind"] for r in train)),
        "validation_counts": dict(Counter(r["kind"] for r in validation)),
        "training_manifest_sha256": sha(folder / "manifest.json"),
        "protocol_sha256": sha(folder / "protocol.json"),
        "checkpoint_training_seconds": perf_counter() - start,
        "registry_sha256_at_freeze": sha(registry),
        "test_access": "No fresh-test question opened during training/calibration",
        "scope": "Text-only synthetic candidate; approval gates unchanged",
    }
    dump(args.output / "descriptor.json", descriptor)
    print(json.dumps(descriptor, indent=2))


if __name__ == "__main__":
    main()
