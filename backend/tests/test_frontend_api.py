from datetime import date

import pytest
from app import main
from app.domain import Service
from app.operations import Trip
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_text_dialogue import text_db as _fixture

text_db = _fixture


@pytest.fixture
def browser_api(text_db, monkeypatch):
    monkeypatch.setattr(main, "engine", text_db)
    monkeypatch.setenv("RTC_ADMIN_TOKEN", "unit-only-local-admin")
    with TestClient(main.app) as client:
        yield client


def test_bootstrap_uses_actual_records(browser_api, text_db):
    from app.domain import Station
    from sqlalchemy import func

    body = browser_api.get("/api/v1/app/bootstrap").json()["data"]
    with Session(text_db) as s:
        assert body["counts"]["stations"] == s.scalar(
            select(func.count()).select_from(Station).where(Station.active.is_(True))
        )
    assert body["default_station"]["code"] == "DEMO0"
    assert "DEMO" in body["sources"]


def test_admin_metadata_and_readonly_are_protected(browser_api):
    for path in (
        "/api/v1/admin/ui/metadata",
        "/api/v1/admin/ui/catalog/depots",
        "/api/v1/admin/ui/catalog/fare-rules",
    ):
        assert browser_api.get(path).status_code == 401
        assert (
            browser_api.get(
                path, headers={"Authorization": "Bearer unit-only-local-admin"}
            ).status_code
            == 200
        )
    data = browser_api.get(
        "/api/v1/admin/ui/metadata",
        headers={"Authorization": "Bearer unit-only-local-admin"},
    ).json()["data"]
    assert "stations" in data["resources"] and data["latest_import"] is None


def test_diagnostics_requires_backend_admin(browser_api):
    payload = {"text": "Next bus to Guntur?", "language": "en"}
    assert (
        browser_api.post("/api/v1/admin/ui/diagnostics", json=payload).status_code
        == 401
    )
    response = browser_api.post(
        "/api/v1/admin/ui/diagnostics",
        json=payload,
        headers={"Authorization": "Bearer unit-only-local-admin"},
    )
    assert response.status_code == 200 and response.json()["debug"]
    assert (
        browser_api.post(
            "/api/v1/nlp/interpret", json={**payload, "debug": True}
        ).status_code
        == 401
    )


def test_service_details_and_unknown_fields(browser_api, text_db):
    with Session(text_db) as s:
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        identifier = service.id
    response = browser_api.get(
        f"/api/v1/app/services/{identifier}?travel_date=2026-11-08"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["service"]["id"] == identifier and len(data["stops"]) == 2
    assert data["stops"][0]["sequence"] < data["stops"][1]["sequence"]
    assert data["status"]["gps_status"] in ("UNKNOWN", "STALE", "KNOWN")
    assert (
        browser_api.get(
            "/api/v1/app/services/no-such-service?travel_date=2026-11-08"
        ).status_code
        == 404
    )


def test_cancelled_service_details_do_not_claim_scheduled(browser_api, text_db):
    with Session(text_db) as s, s.begin():
        service = s.scalar(select(Service).where(Service.number == "DEMO99"))
        trip = Trip(
            service_id=service.id, service_date=date(2026, 11, 9), status="cancelled"
        )
        s.add(trip)
        identifier = service.id
    try:
        response = browser_api.get(
            f"/api/v1/app/services/{identifier}?travel_date=2026-11-09"
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"]["status"] == "CANCELLED"
    finally:
        with Session(text_db) as s, s.begin():
            from sqlalchemy import delete

            s.execute(
                delete(Trip).where(
                    Trip.service_id == identifier,
                    Trip.service_date == date(2026, 11, 9),
                )
            )


def test_production_deep_links_and_api_404(browser_api):
    from pathlib import Path

    if not (Path(__file__).resolve().parents[2] / "frontend/dist/index.html").exists():
        pytest.skip("Production assets not built")
    response = browser_api.get("/journeys")
    assert response.status_code == 200 and 'id="root"' in response.text
    response = browser_api.get("/api/v1/unknown-api/no-such-endpoint")
    assert response.status_code == 404 and response.headers["content-type"].startswith(
        "application/json"
    )


def test_local_rate_and_body_limits():
    from app.frontend_security import install_ui_security
    from fastapi import FastAPI

    isolated = FastAPI()

    @isolated.post("/api/test")
    def endpoint():
        return {"ok": True}

    install_ui_security(isolated)
    with TestClient(isolated) as client:
        assert client.post("/api/test", content="x" * 2200001).status_code == 413
        for _ in range(300):
            assert client.post("/api/test", json={}).status_code == 200
        response = client.post("/api/test", json={})
        assert response.status_code == 429 and response.headers["Retry-After"] == "60"


def test_quality_uses_records_and_accepts_recurring_calendar(browser_api, text_db):
    from datetime import UTC, datetime

    from app.catalog import Calendar
    from app.data_quality import quality_report
    from app.domain import Route, Station

    with Session(text_db) as s:
        s.add(Station(id="quality-station", code="QUALITY", name="Quality fixture"))
        s.add(Route(id="quality-route", code="QUALITY-ROUTE"))
        s.flush()
        report = quality_report(
            s, datetime(2026, 11, 8, 12, tzinfo=UTC), date(2026, 11, 8), limit=100
        )
        assert any(
            i["record_id"] == "quality-station" and i["code"] == "MISSING_STATION_ALIAS"
            for i in report["issues"]
        )
        assert any(
            i["record_id"] == "quality-route" and i["code"] == "MISSING_ROUTE_STOPS"
            for i in report["issues"]
        )
        assert report["total"] == sum(c["count"] for c in report["checks"])
        assert report["unavailable_checks"]
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        from sqlalchemy import delete

        s.execute(delete(Calendar).where(Calendar.service_id == service.id))
        report = quality_report(
            s,
            datetime(2026, 11, 8, 12, tzinfo=UTC),
            date(2026, 11, 8),
            kind="NO_CURRENT_CALENDAR",
            limit=100,
        )
        assert not any(i["record_id"] == service.id for i in report["issues"])
    assert browser_api.get("/api/v1/admin/ui/data-quality").status_code == 401
    response = browser_api.get(
        "/api/v1/admin/ui/data-quality?kind=MISSING_STATION_ALIAS&limit=1",
        headers={"Authorization": "Bearer unit-only-local-admin"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["issues"]) <= 1


def test_global_admin_filter_sort_and_permissions(browser_api):
    headers = {"Authorization": "Bearer unit-only-local-admin"}
    first = browser_api.get(
        "/api/v1/admin/stations?limit=1&sort_by=code&descending=true&q=DEMO",
        headers=headers,
    )
    assert first.status_code == 200 and first.json()["total"] >= 20
    assert len(first.json()["data"]) == 1
    assert (
        browser_api.get(
            "/api/v1/admin/stations?sort_by=not-a-column", headers=headers
        ).status_code
        == 422
    )
    assert (
        browser_api.get("/api/v1/admin/ui/catalog/trips", headers=headers).status_code
        == 200
    )


def test_quality_staleness_uses_latest_applicable_record(text_db):
    from datetime import UTC, datetime, timedelta

    from app.data_quality import quality_report
    from app.domain import Stop
    from app.operations import DataSource
    from app.records import TripStopTime

    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    with Session(text_db) as s:
        service = s.scalar(select(Service).where(Service.number == "DEMO0"))
        stop = s.scalar(
            select(Stop)
            .where(Stop.route_id == service.route_id)
            .order_by(Stop.sequence)
        )
        s.add(
            DataSource(
                id="quality-source", code="QUALITY-SOURCE", name="Quality fixture"
            )
        )
        s.add(
            Trip(
                id="quality-trip",
                service_id=service.id,
                service_date=now.date(),
                status="running",
            )
        )
        s.flush()
        old = TripStopTime(
            id="quality-old",
            trip_id="quality-trip",
            stop_id=stop.id,
            source_id="quality-source",
            verified=True,
            effective_at=now - timedelta(hours=1),
            expires_at=now - timedelta(minutes=1),
        )
        s.add(old)
        s.flush()
        report = quality_report(s, now, now.date(), kind="STALE_TRIP_STOP_TIMES")
        assert any(
            i["record_id"] == old.id and i["resource"] == "stop-observations"
            for i in report["issues"]
        )
        fresh = TripStopTime(
            id="quality-fresh",
            trip_id="quality-trip",
            stop_id=stop.id,
            source_id="quality-source",
            verified=True,
            effective_at=now - timedelta(seconds=10),
            expires_at=now + timedelta(minutes=5),
        )
        s.add(fresh)
        s.flush()
        assert not any(
            i["record_id"] == old.id
            for i in quality_report(s, now, now.date(), kind="STALE_TRIP_STOP_TIMES")[
                "issues"
            ]
        )
        fresh.effective_at = now + timedelta(minutes=1)
        s.flush()
        assert any(
            i["record_id"] == old.id
            for i in quality_report(s, now, now.date(), kind="STALE_TRIP_STOP_TIMES")[
                "issues"
            ]
        )


def test_recorded_import_issue_is_not_a_fabricated_row_history(text_db):
    from datetime import UTC, datetime

    from app.catalog import ImportBatch
    from app.data_quality import quality_report
    from app.operations import DataSource
    from app.records import QualityIssue

    with Session(text_db) as s:
        s.add(
            DataSource(
                id="quality-import-source",
                code="QUALITY-IMPORT",
                name="Quality import fixture",
            )
        )
        s.add(
            ImportBatch(
                id="quality-batch",
                resource="stations",
                digest="quality-fixture-digest",
                row_count=0,
            )
        )
        s.flush()
        s.add(
            QualityIssue(
                id="quality-import-issue",
                source_id="quality-import-source",
                batch_id="quality-batch",
                description="CSV row 7: unknown station",
                resolved=False,
            )
        )
        s.flush()
        report = quality_report(
            s,
            datetime(2026, 11, 8, tzinfo=UTC),
            date(2026, 11, 8),
            kind="RECORDED_IMPORT_ISSUE",
        )
        issue = next(
            i for i in report["issues"] if i["record_id"] == "quality-import-issue"
        )
        assert (
            issue["description"] == "CSV row 7: unknown station"
            and issue["batch_id"] == "quality-batch"
        )
        assert any(
            c["code"] == "INVALID_IMPORT_ROW_HISTORY"
            for c in report["unavailable_checks"]
        )


def test_service_metadata_exposes_actual_operational_expiry(browser_api, text_db):
    from datetime import UTC, datetime, timedelta
    from zoneinfo import ZoneInfo

    from app.domain import Stop
    from app.operations import DataSource
    from app.records import DelayEvent

    now = datetime.now(UTC)
    day = now.astimezone(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=2)
    with Session(text_db) as s, s.begin():
        service = s.scalar(select(Service).where(Service.number == "DEMO98"))
        stop = s.scalar(
            select(Stop)
            .where(Stop.route_id == service.route_id)
            .order_by(Stop.sequence)
        )
        s.add(
            DataSource(id="expiry-source", code="EXPIRY-SOURCE", name="Expiry fixture")
        )
        s.add(
            Trip(
                id="expiry-trip",
                service_id=service.id,
                service_date=day,
                status="running",
            )
        )
        s.flush()
        s.add(
            DelayEvent(
                id="expiry-delay",
                trip_id="expiry-trip",
                station_id=stop.station_id,
                source_id="expiry-source",
                verified=True,
                delay_minutes=12,
                effective_at=now - timedelta(seconds=10),
                expires_at=now + timedelta(minutes=2),
            )
        )
        identifier = service.id
    try:
        response = browser_api.get(
            f"/api/v1/app/services/{identifier}?travel_date={day}"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert (
            data["status"]["delay_status"] == "KNOWN"
            and data["status"]["delay_minutes"] == 12
        )
        assert datetime.fromisoformat(
            data["operational_expires_at"]
        ) == now + timedelta(minutes=2)
        assert data["concessions"] is not None
    finally:
        from app.records import DelayEvent
        from sqlalchemy import delete

        with Session(text_db) as s, s.begin():
            s.execute(delete(DelayEvent).where(DelayEvent.id == "expiry-delay"))
            s.execute(delete(Trip).where(Trip.id == "expiry-trip"))
            s.execute(delete(DataSource).where(DataSource.id == "expiry-source"))


def test_journey_diagnostics_name_actual_executor(browser_api):
    response = browser_api.post(
        "/api/v1/admin/ui/diagnostics",
        json={
            "text": "How can I reach Guntur?",
            "station_context": "DEMO0",
            "language": "en",
        },
        headers={"Authorization": "Bearer unit-only-local-admin"},
    )
    assert response.status_code == 200
    assert "JourneyPlanner.search" in response.json()["debug"]["database_function"]


def test_invalid_timezone_csv_returns_row_error_and_rolls_back(browser_api):
    response = browser_api.post(
        "/api/v1/admin/imports/stations?dry_run=false",
        content="code,name,timezone,dataset_source\nINVALID-TZ,Invalid fixture timezone,Not/A_Zone,DEMO",
        headers={
            "Authorization": "Bearer unit-only-local-admin",
            "Content-Type": "text/csv",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["committed"] is False and data["errors"][0]["row"] == 2
    assert (
        browser_api.get(
            "/api/v1/stations/search?q=Invalid%20fixture%20timezone"
        ).json()["data"]
        == []
    )
