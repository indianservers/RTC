"""Phase 4C actual local records, diagnostics privacy and conversation continuation."""

import io
import json
import logging
from datetime import UTC, date, datetime

from app.data_quality import quality_report
from app.diagnostics import install_diagnostics
from app.domain import Station, Stop
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_frontend_api import browser_api as _browser_api
from test_frontend_api import text_db as _text_db

text_db = _text_db
browser_api = _browser_api


def test_correlated_logs_are_bounded_and_do_not_capture_passenger_text():
    app = FastAPI()

    @app.post("/api/v1/check/{identifier}")
    def check(identifier: str):
        raise RuntimeError("SECRET exception body")

    install_diagnostics(app)
    logger = logging.getLogger("rtc.local.requests")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    try:
        with TestClient(app) as client:
            result = client.post(
                "/api/v1/check/SECRET?query=SECRET",
                json={"text": "SECRET conversation"},
                headers={"Authorization": "Bearer SECRET"},
            )
        assert result.status_code == 500
        assert len(result.headers["X-Request-ID"]) == 32
        assert (
            result.json()["error"]["correlation_id"] == result.headers["X-Request-ID"]
        )
        assert "SECRET" not in stream.getvalue()
        record = json.loads(stream.getvalue())
        assert record["endpoint"] == "/api/v1/check/{identifier}"
        assert record["severity"] == "ERROR" and record["duration_ms"] >= 0
    finally:
        logger.removeHandler(handler)


def test_ambiguity_preserves_pending_question_and_resumes_after_code(text_db):
    with Session(text_db) as session:
        session.add_all(
            [
                Station(id="4c-central-a", code="4C-A", name="4C Central"),
                Station(id="4c-central-b", code="4C-B", name="4C Central"),
            ]
        )
        session.commit()
        nlp = RTCNLPEngine(session)
        first = nlp.process(
            NLPRequest(
                text="Next bus to 4C Central?", language="en", station_context="DEMO0"
            ),
            datetime.now(UTC),
        )
        assert first.requires_clarification
        assert len(first.context["station_clarification"]["choices"]) == 2
        next_reply = nlp.process(
            NLPRequest(
                text="4C-A",
                language="en",
                station_context="DEMO0",
                session_id=first.session_id,
            ),
            datetime.now(UTC),
        )
        assert next_reply.context["destination"] == "4c-central-a"
        assert "station_clarification" not in next_reply.context
        assert next_reply.intents == ["NEXT_BUS"]
        assert next_reply.state == "NO_RESULTS"


def test_category_recovery_preserves_hard_accessibility(text_db):
    with Session(text_db) as session:
        nlp = RTCNLPEngine(session)
        first = nlp.process(
            NLPRequest(
                text="Accessible buses to Nellore",
                language="en",
                station_context="DEMO0",
            ),
            datetime.now(UTC),
        )
        assert first.context["filters"]["accessible"] is True
        next_reply = nlp.process(
            NLPRequest(text="Any bus type", language="en", session_id=first.session_id),
            datetime.now(UTC),
        )
        assert next_reply.context["filters"]["accessible"] is True


def test_new_quality_checks_use_actual_rows(text_db):
    with Session(text_db) as session:
        session.add_all(
            [
                Station(code="4C-DUP-A", name="4C duplicate"),
                Station(code="4C-DUP-B", name="4C duplicate"),
            ]
        )
        stops = list(
            session.scalars(select(Stop).order_by(Stop.route_id, Stop.sequence))
        )
        route_id = stops[0].route_id
        route = [s for s in stops if s.route_id == route_id]
        if len(route) >= 2:
            route[0].offset_minutes = route[-1].offset_minutes + 60
        session.flush()
        report = quality_report(session, datetime.now(UTC), date.today())
        counts = {r["code"]: r["count"] for r in report["checks"]}
        assert counts["POSSIBLE_DUPLICATE_STATION"] >= 2
        assert counts["INVALID_ROUTE_SEQUENCE"] >= 1
        session.rollback()


def test_api_error_has_correlation_and_server_duration(browser_api):
    result = browser_api.get("/api/v1/admin/stations")
    assert result.status_code == 401
    assert len(result.headers["x-request-id"]) == 32
    assert result.headers["server-timing"].startswith("app;dur=")


def test_missing_service_is_rejected_when_selecting_current_list(text_db):
    from app.domain import Service

    now = datetime(2026, 11, 8, 0, 0, tzinfo=UTC)
    with Session(text_db) as session:
        nlp = RTCNLPEngine(session)
        first = nlp.process(
            NLPRequest(
                text="Next bus to Guntur", language="en", station_context="DEMO0"
            ),
            now,
        )
        candidate = first.context["candidates"][0]
        service = session.get(Service, candidate["service_id"])
        service.active = False
        session.flush()
        reply = nlp.process(
            NLPRequest(text="First one", language="en", session_id=first.session_id),
            now,
        )
        assert reply.requires_clarification
        assert "no longer eligible" in reply.answer
        service.active = True
        session.commit()


def test_empty_refresh_removes_old_result_references(text_db):
    from app.domain import Service

    now = datetime(2026, 11, 8, 0, 0, tzinfo=UTC)
    with Session(text_db) as session:
        nlp = RTCNLPEngine(session)
        first = nlp.process(
            NLPRequest(
                text="Next bus to Guntur", language="en", station_context="DEMO0"
            ),
            now,
        )
        services = [
            session.get(Service, c["service_id"]) for c in first.context["candidates"]
        ]
        for service in services:
            service.active = False
        session.flush()
        reply = nlp.process(
            NLPRequest(text="Next bus", language="en", session_id=first.session_id), now
        )
        assert reply.state == "NO_RESULTS"
        assert reply.context["candidates"] == []
        for service in services:
            service.active = True
        session.commit()
