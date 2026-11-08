# ruff: noqa: B008
"""Versioned local feedback/review APIs over existing schema and capabilities."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..records import Audit
from . import feedback, learning
from .feedback import FeedbackInput, ReviewInput


class VersionInput(BaseModel):
    expected_version: int = Field(ge=1)


def review_router(engine_getter, authenticate):
    router = APIRouter(prefix="/api/v1", tags=["Offline NLP quality"])

    def reviewer(principal=Depends(authenticate)):
        if principal.role not in {"ADMIN", "EDITOR", "APPROVER"}:
            raise HTTPException(
                403, "NLP review access requires an authorized data administrator"
            )
        return principal

    def scope(query, principal):
        return (
            query
            if principal.root or principal.global_scope
            else query.where(Audit.operator_id.in_(principal.operators))
        )

    def expire(session, rows, principal):
        for row in rows:
            deadline = (row.new_values or {}).get("expires_at")
            if (
                deadline
                and datetime.fromisoformat(deadline) <= datetime.now(UTC)
                and not row.new_values.get("anonymized")
            ):
                feedback.purge(session, row, principal)

    @router.post("/conversation/feedback")
    def submit(request: FeedbackInput):
        from time import perf_counter

        started = perf_counter()
        with Session(engine_getter()) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            result = feedback.save_feedback(session, request)
        return {**result, "duration_ms": (perf_counter() - started) * 1000}

    @router.get("/admin/nlp/reviews")
    def reviews(
        status: str | None = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        principal=Depends(reviewer),
    ):
        with Session(engine_getter()) as session, session.begin():
            query = scope(
                select(Audit).where(Audit.entity_type == feedback.FEEDBACK), principal
            )
            if status:
                if status not in feedback.STATUSES:
                    raise HTTPException(422, "Unknown review status")
                query = query.where(Audit.new_values["status"].as_string() == status)
            rows = list(
                session.scalars(
                    query.order_by(Audit.recorded_at.desc(), Audit.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            expire(session, rows, principal)
            session.flush()
            total = session.scalar(select(func.count()).select_from(query.subquery()))
            return {
                "data": [
                    feedback.payload(r)
                    for r in rows
                    if not status or r.new_values.get("status") == status
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    @router.post("/admin/nlp/reviews/{identifier}/review")
    def review(identifier: str, request: ReviewInput, principal=Depends(reviewer)):
        with Session(engine_getter()) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            if session.get_bind().dialect.name == "sqlite" and not getattr(
                session.connection().connection.driver_connection,
                "in_transaction",
                False,
            ):
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = feedback.load_review(session, identifier, principal)
            return {"data": feedback.update_review(session, row, request, principal)}

    @router.post("/admin/nlp/reviews/{identifier}/anonymize")
    def anonymize(identifier: str, request: VersionInput, principal=Depends(reviewer)):
        with Session(engine_getter()) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite" and not getattr(
                session.connection().connection.driver_connection,
                "in_transaction",
                False,
            ):
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = feedback.load_review(session, identifier, principal)
            if row.version != request.expected_version:
                raise HTTPException(409, "Review changed")
            return {"data": feedback.purge(session, row, principal)}

    @router.delete("/admin/nlp/reviews/{identifier}")
    def delete(
        identifier: str,
        expected_version: int = Query(ge=1),
        principal=Depends(reviewer),
    ):
        with Session(engine_getter()) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite" and not getattr(
                session.connection().connection.driver_connection,
                "in_transaction",
                False,
            ):
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = feedback.load_review(session, identifier, principal)
            if row.version != expected_version:
                raise HTTPException(409, "Review changed")
            return {"data": feedback.purge(session, row, principal, True)}

    @router.get("/admin/nlp/export")
    def export(principal=Depends(reviewer)):
        with Session(engine_getter()) as session, session.begin():
            rows = list(
                session.scalars(
                    scope(
                        select(Audit).where(Audit.entity_type == feedback.FEEDBACK),
                        principal,
                    )
                )
            )
            expire(session, rows, principal)
            return Response(
                "".join(
                    json.dumps(r, ensure_ascii=False) + "\n"
                    for r in feedback.reviewed_examples(rows)
                ),
                media_type="application/x-ndjson",
                headers={
                    "Content-Disposition": "attachment; filename=reviewed-feedback.jsonl",
                    "Cache-Control": "no-store",
                },
            )

    @router.post("/admin/nlp/retention")
    def retention(limit: int = Query(1000, ge=1, le=5000), principal=Depends(reviewer)):
        with Session(engine_getter()) as session, session.begin():
            rows = list(
                session.scalars(
                    scope(
                        select(Audit)
                        .where(
                            Audit.entity_type == feedback.FEEDBACK,
                            Audit.new_values["expires_at"].as_string()
                            <= datetime.now(UTC).isoformat(),
                            Audit.new_values["anonymized"].as_boolean().is_not(True),
                        )
                        .order_by(Audit.id)
                        .limit(limit),
                        principal,
                    )
                )
            )
            before = sum(bool(r.new_values.get("anonymized")) for r in rows)
            expire(session, rows, principal)
            return {
                "scanned": len(rows),
                "redacted": sum(bool(r.new_values.get("anonymized")) for r in rows)
                - before,
                "retention_days": feedback.retention_days(),
            }

    @router.get("/admin/nlp/quality")
    def quality(principal=Depends(reviewer)):
        with Session(engine_getter()) as session, session.begin():
            rows = list(
                session.scalars(
                    scope(
                        select(Audit).where(Audit.entity_type == feedback.FEEDBACK),
                        principal,
                    )
                )
            )
            expire(session, rows, principal)
            from .metrics import report as metric_report

            counts = list(
                session.scalars(
                    scope(
                        select(Audit).where(Audit.entity_type == "NLP_DAILY_METRICS"),
                        principal,
                    )
                )
            )
            from .english_model import EnglishIntentModel

            model = EnglishIntentModel(learning.root()).descriptor()
            runs = (
                list(
                    session.scalars(
                        select(Audit)
                        .where(Audit.entity_type == "NLP_MODEL_RUN")
                        .order_by(Audit.recorded_at.desc())
                        .limit(100)
                    )
                )
                if principal.root or principal.global_scope
                else []
            )
            return {
                "data": {
                    **feedback.quality_report(rows),
                    **metric_report(counts),
                    "model_readiness": "APPROVED_ACTIVE"
                    if model
                    else "DETERMINISTIC_FALLBACK",
                    "model_version": model.get("version") if model else None,
                    "dataset_version": model.get("dataset_version") if model else None,
                    "runs": [feedback.payload(r) for r in runs],
                    "deployment_history": [
                        {
                            **feedback.payload(r),
                            "recorded_at": r.recorded_at.isoformat(),
                            "actor": r.actor,
                        }
                        for r in session.scalars(
                            select(Audit)
                            .where(Audit.entity_type == "NLP_MODEL_EVENT")
                            .order_by(Audit.recorded_at.desc())
                            .limit(100)
                        )
                    ]
                    if principal.root or principal.global_scope
                    else [],
                    "taxonomy": [x.value for x in feedback.ErrorCategory],
                    "statuses": sorted(feedback.STATUSES),
                    "retention_days": feedback.retention_days(),
                    "text_retention_enabled": __import__("os").getenv(
                        "RTC_FEEDBACK_RETAIN_TEXT", "0"
                    )
                    == "1",
                }
            }

    @router.post("/admin/nlp/training")
    def training(principal=Depends(reviewer)):
        if not principal.root:
            raise HTTPException(
                403,
                "Explicit global administrator authorization is required to train a candidate",
            )
        with Session(engine_getter()) as session, session.begin():
            rows = list(
                session.scalars(
                    select(Audit)
                    .where(Audit.entity_type == feedback.FEEDBACK)
                    .limit(5001)
                )
            )
            if len(rows) > 5000:
                raise HTTPException(
                    422, "Narrow the reviewed corpus below 5000 records"
                )
            try:
                run = learning.train_candidate(session, rows, principal)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            return {"data": feedback.payload(run)}

    @router.post("/admin/nlp/models/{identifier}/{action}")
    def model_action(
        identifier: str, action: str, request: VersionInput, principal=Depends(reviewer)
    ):
        with Session(engine_getter()) as session, session.begin():
            if session.get_bind().dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = session.scalar(
                select(Audit)
                .where(Audit.id == identifier, Audit.entity_type == "NLP_MODEL_RUN")
                .with_for_update()
            )
            if not row:
                raise HTTPException(404, "Model run not found")
            return {
                "data": learning.transition(
                    session, row, action, principal, request.expected_version
                )
            }

    return router
