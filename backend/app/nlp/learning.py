"""Explicit, offline, reviewed-data candidate workflow. Never run during inference."""

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from ..catalog import Intent
from .feedback import record, reviewed_examples

ROOT = Path(__file__).resolve().parents[3]
LOCK = RLock()


def root():
    return Path(os.getenv("RTC_NLP_WORKFLOW_ROOT", str(ROOT))).resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def leakage_check(examples):
    import re

    seen = {}
    groups = {}
    for r in examples:
        key = re.sub(r"\d+", "#", " ".join(r["text"].casefold().split()))
        previous = seen.get(key)
        if previous and (previous[0] != r["split"] or previous[1] != r["intent"]):
            raise ValueError(
                "Duplicate/conflicting text or cross-split template leakage"
            )
        seen[key] = (r["split"], r["intent"])
        group = r["group_id"]
        if group in groups and groups[group] != r["split"]:
            raise ValueError("Conversation group crosses dataset splits")
        groups[group] = r["split"]
    labels = {r["intent"] for r in examples if r["split"] == "train"}
    if len(labels) < 2:
        raise ValueError("At least two reviewed training labels are required")
    for split in ("validation", "test"):
        if {r["intent"] for r in examples if r["split"] == split} != labels:
            raise ValueError(
                "Reviewed train, validation and test splits must cover identical labels"
            )
    return labels


def train_candidate(session, rows, principal):
    # Reuse the same word/character TF-IDF + LinearSVC infrastructure as training/english/train.py.
    import joblib
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.pipeline import FeatureUnion, make_pipeline
    from sklearn.svm import LinearSVC

    from .selective_svm import ReviewedIntentSVM

    examples = reviewed_examples(rows)
    labels = sorted(leakage_check(examples))
    run_id = str(uuid4())
    folder = root() / "models/english/nlp/reviewed" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    splits = {
        key: [r for r in examples if r["split"] == key]
        for key in ("train", "validation", "test")
    }
    pipeline = make_pipeline(
        FeatureUnion(
            [
                ("word", TfidfVectorizer(ngram_range=(1, 2), max_features=20000)),
                (
                    "char",
                    TfidfVectorizer(
                        analyzer="char_wb", ngram_range=(3, 5), max_features=30000
                    ),
                ),
            ]
        ),
        LinearSVC(random_state=42, class_weight="balanced", max_iter=5000),
    )
    pipeline.fit(
        [r["text"] for r in splits["train"]], [r["intent"] for r in splits["train"]]
    )
    temporary = ReviewedIntentSVM(pipeline, {"margin": 0, "gap": 0})
    scores = temporary.decision_function([r["text"] for r in splits["validation"]])
    ranked = np.sort(scores, axis=1)
    margins = ranked[:, -1]
    gaps = ranked[:, -1] - ranked[:, -2]
    predictions = pipeline.predict([r["text"] for r in splits["validation"]])
    truth = np.array([r["intent"] for r in splits["validation"]])
    options = []
    for margin in sorted(
        {0.0, *map(float, np.quantile(margins, np.linspace(0, 1, 21)))}
    ):
        for gap in sorted({0.0, *map(float, np.quantile(gaps, np.linspace(0, 1, 21)))}):
            accepted = (margins >= margin) & (gaps >= gap)
            if (
                accepted.sum()
                and float((predictions[accepted] == truth[accepted]).mean()) >= 0.95
            ):
                options.append((int(accepted.sum()), margin, gap))
    _, margin, gap = (
        max(options, key=lambda item: (item[0], -item[1], -item[2]))
        if options
        else (0, 1e9, 1e9)
    )
    model = ReviewedIntentSVM(pipeline, {"margin": margin, "gap": gap})
    metrics = {}
    for split in ("validation", "test"):
        actual = [r["intent"] for r in splits[split]]
        predicted = [
            r["intents"][0]
            if r["status"] == "KNOWN"
            else "OUT_OF_SCOPE"
            if r["status"] == "OUT_OF_SCOPE"
            else "REJECTED"
            for r in model.predict_selective([r["text"] for r in splits[split]])
        ]
        accepted = [i for i, p in enumerate(predicted) if p != "REJECTED"]
        metrics[split] = {
            "records": len(actual),
            "accuracy": float(accuracy_score(actual, predicted)),
            "coverage": len(accepted) / len(actual),
            "accepted_accuracy": sum(actual[i] == predicted[i] for i in accepted)
            / len(accepted)
            if accepted
            else None,
            "confusion_labels": [*labels, "REJECTED"],
            "confusion_matrix": confusion_matrix(
                actual, predicted, labels=[*labels, "REJECTED"]
            ).tolist(),
        }
    from . import text_support
    from .components import IntentClassifier
    from .content import NLPContentRepository

    baseline = IntentClassifier(NLPContentRepository(session).rules())
    from .english_model import EnglishIntentModel

    active_model = EnglishIntentModel(root())
    active_descriptor = active_model.descriptor()
    baseline_correct = []
    candidate_correct = []
    for r, predicted in zip(
        splits["test"],
        model.predict_selective([r["text"] for r in splits["test"]]),
        strict=True,
    ):
        predicted_rules = text_support.classify_extra(
            r["text"].casefold(), baseline.classify(r["text"].casefold()), session
        )
        if active_descriptor:
            active_prediction = active_model.predict(r["text"])
            predicted_rules = (
                active_prediction.get("intents", [])
                if active_prediction["status"] == "KNOWN"
                else ["OUT_OF_SCOPE"]
                if active_prediction["status"] == "OUT_OF_SCOPE"
                else []
            )
        baseline_correct.append(predicted_rules == [r["intent"]])
        candidate_correct.append(
            predicted.get("intents") == [r["intent"]]
            or predicted["status"] == "OUT_OF_SCOPE"
            and r["intent"] == "OUT_OF_SCOPE"
        )
    metrics["regression"] = {
        "baseline": "APPROVED_ACTIVE_MODEL"
        if active_descriptor
        else "CURRENT_DATABASE_RULES",
        "baseline_accuracy": sum(baseline_correct) / len(baseline_correct),
        "candidate_accuracy": sum(candidate_correct) / len(candidate_correct),
        "lost_correct_cases": sum(
            a and not b
            for a, b in zip(baseline_correct, candidate_correct, strict=True)
        ),
    }
    required = set(
        session.scalars(
            select(Intent.code).where(
                Intent.registry_kind == "ENQUIRY", Intent.active.is_(True)
            )
        )
    ) | {"OUT_OF_SCOPE"}
    # If legacy registry_kind is not RTC_INTENT, use its actual information-intent registry.
    if required == {"OUT_OF_SCOPE"}:
        required = {r["code"] for r in text_support.registry(session)} | {
            "OUT_OF_SCOPE"
        }
    gates = {
        "human_review_provenance": all(
            r.get("label_provenance") == "HUMAN_REVIEWED" for r in examples
        ),
        "full_taxonomy": required <= set(labels),
        "validation_support": len(splits["validation"]) >= 30,
        "independent_holdout": len(splits["test"]) >= 30
        and all(r.get("independent") for r in splits["test"]),
        "validation_precision": metrics["validation"]["accepted_accuracy"] is not None
        and metrics["validation"]["accepted_accuracy"] >= 0.95,
        "test_accuracy": metrics["test"]["accuracy"] >= 0.90,
        "no_regression": metrics["regression"]["lost_correct_cases"] == 0,
    }
    joblib.dump(model, folder / "svm.joblib")
    dump(folder / "label_map.json", list(model.classes_))
    dump(folder / "reviewed-dataset.json", examples)
    dump(folder / "evaluation.json", {"metrics": metrics, "gates": gates})
    values = {
        "status": "CANDIDATE",
        "run_id": run_id,
        "model_path": (folder / "svm.joblib").relative_to(root()).as_posix(),
        "label_map_path": (folder / "label_map.json").relative_to(root()).as_posix(),
        "sha256": digest(folder / "svm.joblib"),
        "dataset_sha256": digest(folder / "reviewed-dataset.json"),
        "feedback_ids": [r["example_id"] for r in examples],
        "source_versions": {
            r.id: r.version for r in rows if r.id in {e["example_id"] for e in examples}
        },
        "metrics": metrics,
        "gates": gates,
        "thresholds": {
            "decision_threshold": margin,
            "gap_threshold": gap,
            "threshold_source": "validation",
        },
        "initiated_by": principal.username,
        "approved_by": None,
        "training_automatic": False,
    }
    return record(session, "NLP_MODEL_RUN", values, actor=principal.username)


def transition(session, row, action, principal, expected_version):
    if not principal.root:
        raise HTTPException(403, "Global model changes require the local administrator")
    if row.version != expected_version:
        raise HTTPException(409, "Model run changed; reload it")
    values = dict(row.new_values)
    if action == "approve":
        if values["status"] != "CANDIDATE" or not all(values["gates"].values()):
            raise HTTPException(
                422,
                "Independent evaluation, taxonomy coverage or regression gates are unmet",
            )
        values.update(status="APPROVED", approved_by=principal.username)
    elif action in {"deploy", "rollback"}:
        registry = root() / "config/model_registry.yaml"
        registry.parent.mkdir(parents=True, exist_ok=True)
        lock_path = registry.with_suffix(".lock")
        with LOCK:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise HTTPException(409, "Model registry is being updated") from exc
            try:
                current = (
                    json.loads(registry.read_text(encoding="utf-8"))
                    if registry.exists()
                    else {"models": []}
                )
                if action == "deploy":
                    if values["status"] != "APPROVED":
                        raise HTTPException(
                            422, "Manual model approval is required before deployment"
                        )
                    model = (root() / values["model_path"]).resolve()
                    if (
                        not model.is_relative_to(root())
                        or digest(model) != values["sha256"]
                    ):
                        raise HTTPException(422, "Candidate artifact checksum changed")
                    from ..records import Audit
                    from .feedback import FEEDBACK

                    approved = list(
                        session.scalars(
                            select(Audit).where(
                                Audit.id.in_(values["feedback_ids"]),
                                Audit.entity_type == FEEDBACK,
                            )
                        )
                    )
                    if len(reviewed_examples(approved)) != len(values["feedback_ids"]):
                        raise HTTPException(
                            422,
                            "Training source consent/approval expired or was removed",
                        )
                    if any(
                        r.version != values["source_versions"].get(r.id)
                        for r in approved
                    ):
                        raise HTTPException(
                            422,
                            "Reviewed training labels changed after the candidate snapshot",
                        )
                    values["registry_before"] = current
                    updated = json.loads(json.dumps(current))
                    for entry in updated["models"]:
                        if (
                            entry.get("model_type") == "english_intent_svm"
                            and entry.get("deployment_status") == "ACTIVE"
                        ):
                            entry["deployment_status"] = "PREVIOUS"
                    updated["models"].append(
                        {
                            "name": "Reviewed feedback " + values["run_id"],
                            "version": values["run_id"],
                            "model_type": "english_intent_svm",
                            "local_path": values["model_path"],
                            "label_map_path": values["label_map_path"],
                            "sha256": values["sha256"],
                            "dataset_version": values["dataset_sha256"],
                            "approved": True,
                            "independent_evaluation": True,
                            "deployment_status": "ACTIVE",
                            **values["thresholds"],
                        }
                    )
                    values.update(status="DEPLOYED")
                else:
                    active = [
                        e
                        for e in current.get("models", [])
                        if e.get("deployment_status") == "ACTIVE"
                        and e.get("model_type") == "english_intent_svm"
                    ]
                    if (
                        values["status"] != "DEPLOYED"
                        or not active
                        or active[0].get("version") != values["run_id"]
                    ):
                        raise HTTPException(
                            409, "Only the currently deployed run can be rolled back"
                        )
                    if digest(registry) != values["registry_after_sha256"]:
                        raise HTTPException(
                            409,
                            "Registry changed outside this deployment; inspect before rollback",
                        )
                    updated = values["registry_before"]
                    values.update(status="ROLLED_BACK")
                tmp = registry.with_suffix(".tmp")
                dump(tmp, updated)
                os.replace(tmp, registry)
                values["registry_after_sha256"] = digest(registry)
            finally:
                os.close(fd)
                lock_path.unlink(missing_ok=True)
    else:
        raise HTTPException(422, "Unknown model transition")
    row.new_values = values
    row.version += 1
    record(
        session,
        "NLP_MODEL_EVENT",
        {"run_id": values["run_id"], "action": action, "version": row.version},
        actor=principal.username,
    )
    return {"id": row.id, "version": row.version, **values}
