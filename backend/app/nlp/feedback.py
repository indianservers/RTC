"""Local opt-in feedback in namespaced existing audit records; no schema changes."""

import hashlib
import os
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..catalog import Context, Intent, Message
from ..records import Audit
from .reliability import ErrorCategory
from .session_access import check_owner

FEEDBACK = "NLP_FEEDBACK"
STATUSES = {
    "NEW",
    "TRIAGED",
    "NEEDS_DATA_FIX",
    "NEEDS_LABEL_REVIEW",
    "APPROVED_FOR_TRAINING",
    "RESOLVED",
    "REJECTED",
}
GROUPS = {
    "MODEL_ERROR",
    "DATA_ERROR",
    "CONTEXT_ERROR",
    "RESPONSE_ERROR",
    "OPERATIONAL_ERROR",
}


def scrub(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[EMAIL]", text or "")
    return re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)", "[NUMBER]", text)[:2000]


def retention_days():
    return min(365, max(1, int(os.getenv("RTC_FEEDBACK_RETENTION_DAYS", "30"))))


def record(session, kind, values, operator_id=None, actor="passenger"):
    row = Audit(
        id=str(uuid4()),
        actor=actor,
        entity_type=kind,
        entity_id=str(uuid4()),
        operation="CREATE",
        recorded_at=datetime.now(UTC),
        operator_id=operator_id,
        version=1,
        new_values=values,
        dataset_source="LOCAL",
    )
    session.add(row)
    session.flush()
    return row


def permitted(row, principal):
    if not (
        principal.root
        or principal.global_scope
        or row.operator_id
        and row.operator_id in principal.operators
    ):
        raise HTTPException(403, "Review record is outside your operator scope")


def payload(row):
    return {
        "id": row.id,
        "operator_id": row.operator_id,
        "version": row.version,
        **(row.new_values or {}),
    }


class FeedbackInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message_id: str = Field(min_length=1, max_length=120)
    owner_token: str = Field(min_length=32, max_length=256, repr=False)
    category: Literal[
        "HELPFUL",
        "NOT_HELPFUL",
        "INCORRECT_INFORMATION",
        "WRONG_DESTINATION",
        "WRONG_BUS",
        "WRONG_FARE",
        "WRONG_TIMING",
        "WRONG_INTENT",
        "OTHER",
    ]
    retain_question: bool = False


class ReviewInput(BaseModel):
    expected_version: int = Field(ge=1)
    status: str
    error_group: str | None = None
    error_category: ErrorCategory | None = None
    corrected_intent: str | None = None
    corrected_entities: list[dict] = Field(default_factory=list)
    corrected_slots: dict = Field(default_factory=dict)
    notes: str = Field(default="", max_length=2000)
    split: Literal["train", "validation", "test"] = "train"
    example_kind: Literal[
        "CORRECTION",
        "HARD_NEGATIVE",
        "CONFUSION",
        "SHORT_FOLLOWUP",
        "CONTEXTUAL",
        "OUT_OF_SCOPE",
    ] = "CORRECTION"
    answer_correct: bool | None = None
    independent: bool = False
    label_provenance: Literal["HUMAN_REVIEWED", "AUTOMATED_DEMO_ACCEPTANCE"] = (
        "HUMAN_REVIEWED"
    )


def save_feedback(session, request):
    context = session.scalar(
        select(Context)
        .where(Context.session_id == request.session_id)
        .with_for_update()
    )
    if not context:
        raise HTTPException(404, "This conversation is unavailable")
    check_owner(context.values, request.owner_token)
    if not context.values.get("_owner_hash"):
        raise HTTPException(403, "Owner-bound conversation required")
    if datetime.fromisoformat(context.values["expires_at"]) <= datetime.now(UTC):
        raise HTTPException(410, "This conversation expired")
    envelope = context.values.get("_feedback_messages", {}).get(request.message_id)
    if not envelope:
        raise HTTPException(404, "This reply is no longer available for feedback")
    key = (
        "nlp-feedback:"
        + hashlib.sha256((request.session_id + request.message_id).encode()).hexdigest()
    )
    existing = session.scalar(select(Audit).where(Audit.idempotency_key == key))
    if existing:
        if existing.new_values["feedback"] != request.category:
            raise HTTPException(409, "Feedback was already submitted for this reply")
        return {"id": existing.id, "saved": True, "duplicate": True}
    user = session.scalar(
        select(Message).where(
            Message.session_id == request.session_id,
            Message.sequence_number == envelope["sequence"] - 1,
        )
    )
    assistant = session.scalar(
        select(Message).where(
            Message.session_id == request.session_id,
            Message.sequence_number == envelope["sequence"],
        )
    )
    if not user or not assistant:
        raise HTTPException(404, "This reply was reset or removed")
    retain = (
        request.retain_question and os.getenv("RTC_FEEDBACK_RETAIN_TEXT", "0") == "1"
    )
    text = scrub(user.text) if retain else None
    now = datetime.now(UTC)
    data = {
        **envelope,
        "message_id": request.message_id,
        "feedback": request.category,
        "status": "NEW",
        "text": text,
        "answer": scrub(assistant.text) if retain else None,
        "text_consent": retain,
        "context": envelope.get("context", {}),
        "group_id": hashlib.sha256(request.session_id.encode()).hexdigest(),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=retention_days())).isoformat(),
        "training_eligible": False,
        "error_group": None,
        "error_category": None,
        "reviewer": None,
        "reviewer_notes": "",
        "corrected_intent": None,
        "corrected_entities": [],
    }
    data.pop("sequence", None)
    row = record(session, FEEDBACK, data, envelope.get("operator_id"))
    row.idempotency_key = key
    return {"id": row.id, "saved": True, "text_retained": retain}


def load_review(session, identifier, principal):
    row = session.scalar(
        select(Audit)
        .where(Audit.id == identifier, Audit.entity_type == FEEDBACK)
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "Review record not found")
    permitted(row, principal)
    return row


def update_review(session, row, request, principal):
    if row.version != request.expected_version:
        raise HTTPException(409, "Review changed; reload before saving")
    if request.status not in STATUSES:
        raise HTTPException(422, "Unknown review status")
    if request.error_group is not None and request.error_group not in GROUPS:
        raise HTTPException(422, "Unknown error group")
    values = {
        **row.new_values,
        **request.model_dump(exclude={"expected_version", "notes"}, mode="json"),
        "reviewer_notes": scrub(request.notes),
        "reviewer": principal.username,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "training_eligible": False,
    }
    if request.corrected_intent and not session.scalar(
        select(Intent).where(
            Intent.code == request.corrected_intent, Intent.active.is_(True)
        )
    ):
        raise HTTPException(422, "Choose an active registered intent or dialogue act")
    allowed_slots = {
        "origin",
        "destination",
        "via",
        "passengers",
        "ac",
        "sleeper",
        "category",
        "operator",
    }
    if (
        not set(request.corrected_slots) <= allowed_slots
        or len(str(request.corrected_slots)) > 2000
    ):
        raise HTTPException(422, "Unsupported corrected entity slots")
    text = values.get("text") or ""
    for span in request.corrected_entities:
        if set(span) - {"start", "end", "type", "surface", "canonical_value"}:
            raise HTTPException(422, "Unsupported entity annotation fields")
        start, end = span.get("start"), span.get("end")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start < end <= len(text)
            or span.get("surface") != text[start:end]
        ):
            raise HTTPException(422, "Entity span must match the retained text")
        from ..catalog import EntityType

        if not session.scalar(
            select(EntityType.id).where(
                EntityType.code == span.get("type"), EntityType.active.is_(True)
            )
        ):
            raise HTTPException(422, "Unknown entity type")
    if request.status == "APPROVED_FOR_TRAINING":
        if not (principal.root or principal.role == "APPROVER"):
            raise HTTPException(
                403, "An authorized reviewer must approve training eligibility"
            )
        if (
            not text
            or not values.get("text_consent")
            or not request.corrected_intent
            or not request.notes.strip()
            or request.error_group not in {"MODEL_ERROR", "CONTEXT_ERROR"}
        ):
            raise HTTPException(
                422,
                "Training approval requires retained consented text, corrected label, reviewer notes and a model/context error classification",
            )
        if datetime.fromisoformat(values["expires_at"]) <= datetime.now(UTC):
            raise HTTPException(410, "Retained feedback expired")
        values["training_eligible"] = True
    row.new_values = values
    row.version += 1
    record(
        session,
        "NLP_REVIEW_EVENT",
        {
            "feedback_id": row.id,
            "status": request.status,
            "error_group": request.error_group,
            "error_category": request.error_category,
            "version": row.version,
        },
        row.operator_id,
        principal.username,
    )
    return payload(row)


def purge(session, row, principal, delete=False):
    values = {
        k: v
        for k, v in row.new_values.items()
        if k
        in {"feedback", "created_at", "expires_at", "model_version", "dataset_version"}
    }
    row.new_values = {
        **values,
        "status": "RESOLVED",
        "training_eligible": False,
        "anonymized": True,
        "deleted": delete,
    }
    row.version += 1
    from .learning import root

    for run in session.scalars(
        select(Audit).where(Audit.entity_type == "NLP_MODEL_RUN").with_for_update()
    ):
        values = dict(run.new_values or {})
        if row.id not in values.get("feedback_ids", []):
            continue
        values["source_revoked"] = True
        values["gates"] = {**values.get("gates", {}), "source_consent": False}
        run.new_values = values
        run.version += 1
        if values.get("model_path"):
            artifact = (
                root() / values["model_path"]
            ).resolve().parent / "reviewed-dataset.json"
            if artifact.is_relative_to(root()):
                artifact.unlink(missing_ok=True)
    record(
        session,
        "NLP_REVIEW_EVENT",
        {"feedback_id": row.id, "action": "DELETE" if delete else "ANONYMIZE"},
        row.operator_id,
        principal.username,
    )
    return {"id": row.id, "anonymized": True, "training_eligible": False}


def reviewed_examples(rows):
    result = []
    for row in rows:
        v = row.new_values or {}
        if (
            v.get("status") != "APPROVED_FOR_TRAINING"
            or not v.get("training_eligible")
            or not v.get("text_consent")
            or not v.get("text")
            or datetime.fromisoformat(v["expires_at"]) <= datetime.now(UTC)
        ):
            continue
        result.append(
            {
                "example_id": row.id,
                "text": v["text"],
                "intent": v["corrected_intent"],
                "entities": v.get("corrected_entities", []),
                "context": v.get("context", {}),
                "group_id": v["group_id"],
                "split": v["split"],
                "example_kind": v["example_kind"],
                "independent": v.get("independent", False),
                "label_provenance": v.get("label_provenance", "UNKNOWN"),
                "source": "REVIEWED_LOCAL_FEEDBACK",
                "approval_status": "APPROVED_FOR_TRAINING",
                "reviewer": v["reviewer"],
                "model_version": v.get("model_version"),
                "dataset_version": v.get("dataset_version"),
                "approved_at": v["reviewed_at"],
            }
        )
    return result


def quality_report(rows):
    values = [r.new_values or {} for r in rows]
    reviewed = [
        v
        for v in values
        if v.get("reviewer")
        and v.get("status") not in {"NEW", "REJECTED"}
        and v.get("label_provenance") == "HUMAN_REVIEWED"
    ]
    labelled = [v for v in reviewed if v.get("corrected_intent")]
    confusion = Counter(
        (
            v.get("predicted_intents", [None])[0]
            if v.get("predicted_intents")
            else None,
            v["corrected_intent"],
        )
        for v in labelled
    )
    correctness = [
        v["answer_correct"] for v in reviewed if v.get("answer_correct") is not None
    ]
    entities = [v for v in reviewed if v.get("corrected_entities")]
    slot_cases = [v for v in reviewed if v.get("corrected_slots")]
    slot_scores = [
        all(
            v.get("extracted_entities", {}).get(
                k, v.get("extracted_entities", {}).get("filters", {}).get(k)
            )
            == expected
            for k, expected in v["corrected_slots"].items()
        )
        for v in slot_cases
    ]
    return {
        "feedback_count": len(values),
        "feedback_categories": dict(Counter(v.get("feedback") for v in values)),
        "error_groups": dict(
            Counter(v.get("error_group") for v in reviewed if v.get("error_group"))
        ),
        "error_categories": dict(
            Counter(
                v.get("error_category") for v in reviewed if v.get("error_category")
            )
        ),
        "reviewed_intent_examples": len(labelled),
        "intent_accuracy": sum(
            v.get("predicted_intents", []) == [v["corrected_intent"]] for v in labelled
        )
        / len(labelled)
        if labelled
        else None,
        "confusions": [
            {"predicted": p, "corrected": c, "count": n}
            for (p, c), n in confusion.items()
        ],
        "entity_review_count": len(entities),
        "entity_labelled_cases": len(slot_cases),
        "entity_slot_accuracy": sum(slot_scores) / len(slot_scores)
        if slot_scores
        else None,
        "entity_exact_match": None,
        "entity_metric_status": "Predicted extractor spans are not available; reviewed span count is evidence, not a computed span accuracy",
        "reviewed_answer_count": len(correctness),
        "answer_correctness": sum(correctness) / len(correctness)
        if correctness
        else None,
        "missing_feedback_is_positive": False,
        "drift": {
            "status": "INSUFFICIENT_EVIDENCE",
            "minimum_window_samples": 100,
            "reason": "Feedback is a selected sample; compare stored aggregate windows before claiming drift.",
        },
    }
