from datetime import date

import pytest
from app import main
from app.demo import enrich
from app.domain import Base, database
from app.engine import RTCEnquiryEngine
from app.resolver import StationResolver
from app.seed import seed
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def local(tmp_path):
    engine = database("sqlite:///" + str(tmp_path / "engine.db"))
    Base.metadata.create_all(engine)
    seed(engine)
    enrich(engine)
    return engine


def test_central_and_resolution(local):
    with Session(local) as session:
        resolver = StationResolver(session)
        assert resolver.resolve("Bezawada")["status"] == "KNOWN"
        assert resolver.resolve("విజయవాడ")["candidates"][0]["name"] == "Vijayawada"
        assert resolver.resolve("Vijaywada")["suggestions"]
        e = RTCEnquiryEngine(session)
        response = e.enquire(
            intent="NEXT_BUS",
            origin="Bezawada",
            destination="Guntur",
            travel_date=date(2026, 11, 8),
        )
        assert response.status == "KNOWN"
        assert response.results
        assert response.results[0]["fare_details"]["fare_status"] == "KNOWN"
        assert (
            e.enquire(
                intent="NEXT_BUS",
                origin="Vijayawada",
                destination="Guntur",
                travel_date=date(2026, 11, 8),
                filters={"category": "NO_SUCH_CATEGORY"},
            ).status
            == "INVALID_QUERY"
        )
        assert not e.enquire(
            intent="AC_BUS_AVAILABILITY",
            origin="Vijayawada",
            destination="Guntur",
            travel_date=date(2026, 11, 8),
        ).results
        assert (
            e.enquire(
                intent="NEXT_BUS",
                origin="Guntur",
                destination="Guntur",
                travel_date=date(2026, 11, 8),
            ).status
            == "INVALID_QUERY"
        )


def test_unified_api(local, monkeypatch):
    monkeypatch.setattr(main, "engine", local)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/enquiry",
            json={
                "intent": "NEXT_BUS",
                "origin": "Vijayawada",
                "destination": "Guntur",
                "travel_date": "2026-11-08",
            },
        )
        assert response.status_code == 200
        assert response.json()["results"]
        assert (
            client.get("/api/v1/stations/resolve", params={"value": "Bezawada"}).json()[
                "data"
            ]["status"]
            == "KNOWN"
        )
