"""Train only explicitly partitioned, reviewed database utterances."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from app.catalog import Intent, Utterance
from app.domain import database
from sqlalchemy import select
from sqlalchemy.orm import Session

p = argparse.ArgumentParser()
p.add_argument("--tensorflow", action="store_true")
p.add_argument(
    "--pilot",
    action="store_true",
    help="Unreviewed rule corpus; training-only evaluation; never eligible for promotion",
)
p.add_argument("--epochs", type=int, default=10)
p.add_argument("--version", default=None)
p.add_argument(
    "--manifest",
    type=Path,
    help="Validated frozen synthetic split manifest; not an independent test",
)
a = p.parse_args()
prepared_metadata = None
if a.manifest:
    import hashlib

    root = Path(__file__).resolve().parents[2]
    prepared_metadata = json.loads(a.manifest.read_text(encoding="utf-8"))
    records = []
    leakage: dict[str, str] = {}
    for split, metadata in prepared_metadata["files"].items():
        path = (root / metadata["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid snapshot path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("Dataset snapshot checksum mismatch")
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            group = row["leakage_group"]
            if group in leakage and leakage[group] != split:
                raise ValueError("Leaked family group")
            leakage[group] = split
            if len(row["intent_codes"]) == 1 and row["dataset_type"] in (
                "SINGLE_INTENT",
                "ASR_STYLE",
            ):
                records.append(
                    (
                        row["text"],
                        row["intent_codes"][0],
                        "test" if split == "synthetic_challenge" else split,
                    )
                )
else:
    with Session(database()) as s:
        records = list(
            s.execute(
                select(Utterance.text, Intent.code, Utterance.dataset_split)
                .join(Intent, Intent.id == Utterance.intent_id)
                .where(
                    Utterance.active.is_(True),
                    Utterance.language == "en",
                    Intent.active.is_(True),
                    (Utterance.source_type == "RULE")
                    if a.pilot
                    else (Utterance.quality_status == "REVIEWED"),
                )
            )
        )
splits = {
    name: [
        (text, label)
        for text, label, split in records
        if split and split.lower() == name
    ]
    for name in ["train", "validation", "test"]
}
if a.pilot:
    splits = {
        "train": list(
            dict.fromkeys((text, label) for text, label, _ in records if text.isascii())
        ),
        "validation": [],
        "test": [],
    }
if not a.pilot and not all(splits.values()):
    raise SystemExit(
        "BLOCKED: reviewed train/validation/test utterances are missing in the database. No model trained."
    )
seen: dict[str, tuple[str, str]] = {}
for split, rows in splits.items():
    for text, label in rows:
        key = " ".join(text.casefold().split())
        if key in seen and seen[key] != (split, label):
            raise ValueError("Contradiction or split leakage")
        seen[key] = (split, label)
labels = sorted({label for _, label in splits["train"]})
if len(labels) < 40:
    raise SystemExit("BLOCKED: fewer than 40 reviewed training intents")
for split in [] if a.pilot else ["validation", "test"]:
    if {y for _, y in splits[split]} != set(labels):
        raise ValueError("All splits must cover the same intents")
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.svm import LinearSVC

folder = Path("models/english/nlp") / (
    a.version or ("pilot-v2" if a.pilot else "candidate-v1")
)
if folder.exists():
    raise SystemExit("Output version exists; refusing to overwrite checkpoint")
folder.mkdir(parents=True, exist_ok=True)
X, y = zip(*splits["train"], strict=True)
model = make_pipeline(
    FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=(1, 2))),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
        ]
    ),
    LinearSVC(random_state=42, class_weight="balanced"),
)
model.fit(X, y)
joblib.dump(model, folder / "svm.joblib")
import hashlib

checksum = hashlib.sha256(
    json.dumps(records, default=str, sort_keys=True).encode()
).hexdigest()
(folder / "label_map.json").write_text(json.dumps(labels))
report = {
    "prepared_manifest": prepared_metadata,
    "dataset": {
        "records": len(records),
        "training": len(splits["train"]),
        "validation": len(splits["validation"]),
        "independent_test": 0 if a.manifest else len(splits["test"]),
        "synthetic_challenge": len(splits["test"]) if a.manifest else 0,
        "sha256": checksum,
        "review_status": "UNREVIEWED_SYNTHETIC_GROUPED"
        if a.manifest
        else "UNREVIEWED_RULE_PHRASES"
        if a.pilot
        else "REVIEWED_DB",
        "human_reviewed": False
        if a.pilot or a.manifest
        else "not independently verified",
    },
    "deployment_status": "CANDIDATE",
    "promotion_eligible": False,
    "preprocessing_version": "nfkc-casefold-v1",
    "seed": 42,
}
train_pred = model.predict(X)
report["svm_training_only"] = classification_report(
    y, train_pred, labels=labels, output_dict=True, zero_division=0
)

for split in [] if a.pilot else ["validation", "test"]:
    texts, truth = zip(*splits[split], strict=True)
    start = time.perf_counter()
    pred = model.predict(texts)
    report["svm_" + split] = {
        "metrics": classification_report(
            truth, pred, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(truth, pred, labels=labels).tolist(),
        "ms_per_example": (time.perf_counter() - start) * 1000 / len(texts),
    }
if a.tensorflow:
    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)
    vector = tf.keras.layers.TextVectorization(
        max_tokens=20000, output_sequence_length=64
    )
    vector.adapt(np.asarray(X))
    inputs = tf.keras.Input(shape=(), dtype=tf.string)
    x = vector(inputs)
    x = tf.keras.layers.Embedding(20000, 64)(x)
    x = tf.keras.layers.Conv1D(64, 3, activation="relu")(x)
    x = tf.keras.layers.GlobalMaxPooling1D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(len(labels), activation="softmax")(x)
    cnn = tf.keras.Model(inputs, outputs)
    cnn.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    encode = lambda targets: np.asarray([labels.index(label) for label in targets])
    train_x = tf.constant(list(X))
    train_y = encode(y)
    validation = None
    if not a.pilot:
        vx, vy = zip(*splits["validation"], strict=True)
        validation = (tf.constant(list(vx)), encode(vy))
    history = cnn.fit(
        train_x,
        train_y,
        validation_data=validation,
        epochs=a.epochs,
        batch_size=16,
        verbose=2,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="loss" if a.pilot else "val_loss",
                patience=3,
                restore_best_weights=True,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="loss" if a.pilot else "val_loss", patience=2
            ),
        ],
    )
    cnn.save(folder / "textcnn.keras")
    (folder / "training_history.json").write_text(json.dumps(history.history))
    targets = ["train"] if a.pilot else ["validation", "test"]
    for split in targets:
        tx, ty = zip(*splits[split], strict=True)
        pred = [
            labels[i]
            for i in cnn(tf.constant(list(tx)), training=False).numpy().argmax(axis=1)
        ]
        report["textcnn_" + split] = classification_report(
            ty, pred, labels=labels, output_dict=True, zero_division=0
        )
if a.manifest:
    if "svm_test" in report:
        report["svm_synthetic_challenge"] = report.pop("svm_test")
    if "textcnn_test" in report:
        report["textcnn_synthetic_challenge"] = report.pop("textcnn_test")
(folder / "evaluation.json").write_text(
    json.dumps({"labels": labels, "results": report}, indent=2)
)
