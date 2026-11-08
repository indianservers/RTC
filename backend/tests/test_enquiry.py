from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from app.domain import Base, Repository, database
from app.seed import seed
from sqlalchemy.orm import Session


@pytest.fixture
def engine():
    engine = database("sqlite://")
    Base.metadata.create_all(engine)
    seed(engine)
    return engine


def test_seed_idempotent(engine):
    seed(engine)
    from app.domain import Service
    from sqlalchemy import func, select

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Service)) == 100


@pytest.mark.parametrize("clock", ["23:59", "00:00", "00:01"])
def test_boundary(engine, clock):
    at = datetime.fromisoformat("2026-11-08T" + clock).replace(
        tzinfo=ZoneInfo("Asia/Kolkata")
    )
    with Session(engine) as session:
        rows = Repository(session).journeys("Vijayawada", "Guntur", at)
        assert rows
        assert all(row["departure"] >= at for row in rows)
        assert rows == sorted(rows, key=lambda r: r["departure"])
        assert all(row["seat_availability"] == "unknown" for row in rows)


def test_naive_rejected(engine):
    with Session(engine) as session, pytest.raises(ValueError):
        Repository(session).journeys("Vijayawada", "Guntur", datetime(2026, 11, 8))
