"""Run from repository root: $env:PYTHONPATH='backend'; python scripts/verify.py."""

from datetime import datetime
from statistics import median
from time import perf_counter
from zoneinfo import ZoneInfo

from app.domain import database
from app.enquiry import Enquiry, JourneyQuery
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

engine = database()
q = JourneyQuery(
    origin="Vijayawada",
    destination="Guntur",
    at=datetime(2026, 11, 8, tzinfo=ZoneInfo("Asia/Kolkata")),
)
with engine.connect() as connection:
    if engine.dialect.name == "sqlite":
        assert connection.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert not connection.execute(text("PRAGMA foreign_key_check")).all()
with Session(engine) as session:
    timings = []
    for _ in range(10):
        start = perf_counter()
        assert Enquiry(session).get_next_buses(q)
        timings.append((perf_counter() - start) * 1000)
print(
    {
        "tables": len(inspect(engine).get_table_names()),
        "next_bus_median_ms": round(median(timings), 2),
        "runs": len(timings),
        "dialect": engine.dialect.name,
    }
)
