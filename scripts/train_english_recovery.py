"""Train immutable English candidates from train/validation only; offline, no promotion."""

import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline
from prepare_english_recovery import dump, rows, sha

DATA = ROOT / "training/datasets/recovery-60-v3"
OUTPUT = ROOT / "models/english/nlp/recovery-60-v3"
VERSION = "recovery-60-v3"


def data():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    partitions = {}
    # Deliberately never open the challenge file here.
    for split in ("train", "validation"):
        p = ROOT / manifest["files"][split]["path"]
        if sha(p) != manifest["files"][split]["sha256"]:
            raise ValueError("Frozen dataset checksum differs")
        partitions[split] = rows(p)
    if manifest["under_30"] or len(manifest["labels"]) != 60:
        raise ValueError("Corpus fails initial 60-intent minimum")
    return manifest, partitions["train"], partitions["validation"]


def calibration(prediction, truth, domain, margins, gaps):
    outside = truth == "OUT_OF_SCOPE"
    candidates = []
    for d in (-1, -0.5, 0, 0.25, 0.5, 1):
        for m in (-1, -0.5, 0, 0.25, 0.5, 1):
            for g in (0, 0.1, 0.2, 0.4, 0.6):
                accepted = (domain >= d) & (margins >= m) & (gaps >= g)
                support = int((accepted & ~outside).sum())
                correct = int((accepted & (prediction == truth) & ~outside).sum())
                precision = correct / support if support else 0
                far = float(accepted[outside].mean())
                candidates.append(
                    {
                        "thresholds": {"domain": d, "margin": m, "gap": g},
                        "id_support": support,
                        "id_precision": precision,
                        "oos_false_accept_rate": far,
                        "correctly_accepted": correct,
                        "feasible": support >= 30 and precision >= 0.95 and far <= 0.05,
                    }
                )
    feasible = [r for r in candidates if r["feasible"]]
    selected = (
        max(
            feasible,
            key=lambda r: (
                r["correctly_accepted"],
                r["id_precision"],
                -r["oos_false_accept_rate"],
            ),
        )
        if feasible
        else None
    )
    return {
        "selected": selected,
        "search": candidates,
        "policy": "validation-only; >=30 accepted ID, ID precision >=.95, OOS false acceptance <=.05; no independent safety claim",
    }


def svm():
    import joblib
    import numpy as np
    from app.nlp.selective_svm import SelectiveIntentSVM
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.pipeline import FeatureUnion
    from sklearn.svm import LinearSVC

    manifest, train, validation = data()
    target = OUTPUT / "svm.joblib"
    if target.exists():
        raise ValueError("Immutable SVM version already exists")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    labels = manifest["labels"]
    truth = np.array([r["intent"] or "OUT_OF_SCOPE" for r in validation])
    inside = truth != "OUT_OF_SCOPE"
    train_inside = np.array([r["kind"] == "IN_SCOPE" for r in train])
    x = [r["normalized_text"] for r in train]
    vx = [r["normalized_text"] for r in validation]
    y = np.array([r["intent"] or "OUT_OF_SCOPE" for r in train])
    best = None
    search = []
    started = perf_counter()
    for char_weight in (0.5, 1, 2):
        features = FeatureUnion(
            [
                ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                (
                    "char",
                    TfidfVectorizer(
                        analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True
                    ),
                ),
            ],
            transformer_weights={"word": 1, "char": char_weight},
        )
        matrix = features.fit_transform(x)
        valid = features.transform(vx)
        for c in (0.25, 1, 4, 16):
            model = LinearSVC(
                C=c, class_weight="balanced", random_state=73421, max_iter=10000
            )
            model.fit(matrix[train_inside], y[train_inside])
            pred = model.predict(valid)
            score = f1_score(
                truth[inside],
                pred[inside],
                labels=labels,
                average="macro",
                zero_division=0,
            )
            item = {
                "C": c,
                "char_weight": char_weight,
                "validation_macro_f1": score,
                "validation_accuracy": accuracy_score(truth[inside], pred[inside]),
            }
            search.append(item)
            if best is None or score > best[0]:
                best = (score, features, model, item)
    _, features, model, configuration = best
    domain = LinearSVC(C=1, class_weight="balanced", random_state=73421, max_iter=10000)
    domain.fit(features.transform(x), train_inside.astype(int))
    valid = features.transform(vx)
    scores = model.decision_function(valid)
    ordered = np.sort(scores, axis=1)
    calibrated = calibration(
        model.classes_[scores.argmax(axis=1)],
        truth,
        domain.decision_function(valid),
        ordered[:, -1],
        ordered[:, -1] - ordered[:, -2],
    )
    thresholds = (
        calibrated["selected"]["thresholds"]
        if calibrated["selected"]
        else {"domain": 100, "margin": 100, "gap": 100}
    )
    bundle = SelectiveIntentSVM(features, model, domain, thresholds)
    assert list(bundle.classes_) == labels
    joblib.dump(bundle, target)
    dump(OUTPUT / "label_map.json", labels)
    descriptor = {
        "version": VERSION,
        "model_type": "english_intent_svm",
        "local_path": target.relative_to(ROOT).as_posix(),
        "sha256": sha(target),
        "label_map_path": (OUTPUT / "label_map.json").relative_to(ROOT).as_posix(),
        "deployment_status": "CANDIDATE",
        "approved": False,
        "independent_evaluation": False,
        "human_reviewed": False,
        "preprocessing": "NFKC_CASEFOLD_COLLAPSE_WHITESPACE_REQUIRED",
        "training_manifest_sha256": sha(DATA / "manifest.json"),
        "configuration": configuration,
        "threshold_source": "validation",
        "decision_threshold": thresholds["margin"],
        "selective_thresholds": thresholds,
        "calibration_feasible": calibrated["selected"] is not None,
        "training_seconds": perf_counter() - started,
    }
    dump(
        OUTPUT / "svm-validation-search.json",
        {"configurations": search, "calibration": calibrated},
    )
    dump(OUTPUT / "svm-descriptor.json", descriptor)
    print(json.dumps(descriptor, indent=2))


def cnn():
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "4")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
    import numpy as np
    import tensorflow as tf
    from sklearn.metrics import f1_score

    manifest, train, validation = data()
    if (OUTPUT / "textcnn.keras").exists():
        raise ValueError("Immutable TextCNN version already exists")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    labels = manifest["labels"]
    labelmap = {c: i for i, c in enumerate(labels)}
    train = [r for r in train if r["kind"] == "IN_SCOPE"]
    validation = [r for r in validation if r["kind"] == "IN_SCOPE"]
    x = [r["normalized_text"] for r in train]
    vx = [r["normalized_text"] for r in validation]
    y = np.array([labelmap[r["intent"]] for r in train])
    vy = np.array([labelmap[r["intent"]] for r in validation])
    length = min(48, max(16, int(np.percentile([len(t.split()) for t in x], 99)) + 2))
    options = tf.data.Options()
    options.threading.private_threadpool_size = 2
    train_data = (
        tf.data.Dataset.from_tensor_slices((tf.constant(x), y))
        .shuffle(len(x), seed=73421)
        .batch(32)
        .with_options(options)
        .prefetch(1)
    )
    valid_data = (
        tf.data.Dataset.from_tensor_slices((tf.constant(vx), vy))
        .batch(64)
        .with_options(options)
    )
    best = -1
    histories = []
    started = perf_counter()
    for index, (embedding, filters, dropout) in enumerate(
        [(64, 64, 0.3), (96, 96, 0.4)]
    ):
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(73421 + index)
        vector = tf.keras.layers.TextVectorization(
            max_tokens=6000,
            output_sequence_length=length,
            standardize="lower_and_strip_punctuation",
        )
        vector.adapt(tf.constant(x))
        inputs = tf.keras.Input(shape=(), dtype=tf.string)
        embedded = tf.keras.layers.Embedding(
            len(vector.get_vocabulary()),
            embedding,
            embeddings_regularizer=tf.keras.regularizers.l2(1e-5),
        )(vector(inputs))
        branches = [
            tf.keras.layers.GlobalMaxPooling1D()(
                tf.keras.layers.Conv1D(filters, k, activation="relu")(embedded)
            )
            for k in (2, 3, 4, 5)
        ]
        combined = tf.keras.layers.Concatenate()(branches)
        outputs = tf.keras.layers.Dense(60, activation="softmax")(
            tf.keras.layers.Dropout(dropout)(combined)
        )
        model = tf.keras.Model(inputs, outputs)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        history = model.fit(
            train_data,
            validation_data=valid_data,
            epochs=60,
            verbose=2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss", patience=8, restore_best_weights=True
                ),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor="val_loss", patience=3, factor=0.5, min_lr=1e-5
                ),
            ],
        )
        predictions = model(tf.constant(vx), training=False).numpy().argmax(axis=1)
        score = f1_score(
            vy, predictions, labels=list(range(60)), average="macro", zero_division=0
        )
        info = {
            "configuration": {
                "embedding": embedding,
                "filters_per_kernel": filters,
                "dropout": dropout,
                "sequence_length": length,
                "vocabulary_size": len(vector.get_vocabulary()),
                "kernels": [2, 3, 4, 5],
                "learning_rate": 0.001,
                "class_weights": "None; actual per-intent counts differ by <=1",
            },
            "validation_macro_f1": score,
            "history": history.history,
        }
        histories.append(info)
        if score > best:
            best = score
            model.save(OUTPUT / "textcnn.keras")
            selected = info
    dump(OUTPUT / "textcnn-training-history.json", histories)
    dump(OUTPUT / "label_map.json", labels)
    descriptor = {
        "version": VERSION,
        "model_type": "english_intent_textcnn",
        "local_path": (OUTPUT / "textcnn.keras").relative_to(ROOT).as_posix(),
        "sha256": sha(OUTPUT / "textcnn.keras"),
        "label_map_path": (OUTPUT / "label_map.json").relative_to(ROOT).as_posix(),
        "deployment_status": "CANDIDATE",
        "approved": False,
        "independent_evaluation": False,
        "human_reviewed": False,
        "preprocessing": "NFKC_CASEFOLD_COLLAPSE_WHITESPACE_REQUIRED",
        "configuration": selected["configuration"],
        "validation_macro_f1": best,
        "training_seconds": perf_counter() - started,
        "training_manifest_sha256": sha(DATA / "manifest.json"),
        "threshold_source": "validation_pending_comparison",
        "test_access": "No challenge questions opened during fitting/selection",
    }
    dump(OUTPUT / "textcnn-descriptor.json", descriptor)
    print(json.dumps(descriptor, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=["svm", "cnn"])
    parser.add_argument("--output-version", default=VERSION)
    parser.add_argument("--dataset", type=Path, default=DATA)
    args = parser.parse_args()
    if not args.output_version or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in args.output_version
    ):
        parser.error("output-version must be a simple version identifier")
    VERSION = args.output_version
    DATA = args.dataset.resolve()
    OUTPUT = ROOT / "models/english/nlp" / VERSION
    enforce_offline()
    (svm if args.model == "svm" else cnn)()
