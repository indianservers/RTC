"""Reproducible same-corridor stress fixture, including capacity refusals."""

import json
import socket
import statistics
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil
from sqlalchemy import event, insert
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import catalog, links, operations, records, schema1a  # noqa: F401
from app.domain import Base, Category, Operator, Route, Service, Station, Stop, database
from app.journey import JourneyConstraints, JourneyPlanner


def run(size):
    with tempfile.TemporaryDirectory() as tmp:
        engine = database("sqlite:///" + str(Path(tmp) / "bench.db"))
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                insert(Operator),
                [{"id": "op", "code": "OP", "name": "Synthetic operator"}],
            )
            conn.execute(
                insert(Category),
                [{"id": "cat", "operator_id": "op", "name": "Synthetic category"}],
            )
            conn.execute(
                insert(Station), [{"id": n, "code": n, "name": n} for n in ("A", "B")]
            )
            conn.execute(insert(Route), [{"id": "route", "code": "R"}])
            conn.execute(
                insert(Stop),
                [
                    {
                        "id": "a",
                        "route_id": "route",
                        "station_id": "A",
                        "sequence": 0,
                        "offset_minutes": 0,
                        "distance_km": 0,
                    },
                    {
                        "id": "b",
                        "route_id": "route",
                        "station_id": "B",
                        "sequence": 1,
                        "offset_minutes": 120,
                        "distance_km": 100,
                    },
                ],
            )
            conn.execute(
                insert(Service),
                [
                    {
                        "id": f"s{i}",
                        "number": f"S{i}",
                        "route_id": "route",
                        "operator_id": "op",
                        "category_id": "cat",
                        "departure_minutes": 600 + i % 600,
                        "valid_from": date(2026, 1, 1),
                        "valid_to": date(2026, 12, 31),
                    }
                    for i in range(size)
                ],
            )
        counts = []
        count = [0]

        @event.listens_for(engine, "before_cursor_execute")
        def query_count(*args):
            count[0] += 1

        c = JourneyConstraints(
            origin="A",
            destination="B",
            earliest_departure=datetime(
                2026, 11, 8, 9, tzinfo=ZoneInfo("Asia/Kolkata")
            ),
            horizon_hours=12,
            max_transfers=0,
            max_expansions=20000,
            max_services_per_segment=10000,
        )
        samples = []
        status = "OK"
        stats = {}
        iterations = (
            100 if size == 100 else 30 if size == 1000 else 3 if size == 10000 else 1
        )
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        for _ in range(iterations):
            count[0] = 0
            start = time.perf_counter()
            try:
                with Session(engine) as s:
                    result = JourneyPlanner(s).search(c)
                    stats = result.search_stats
            except ValueError as exc:
                status = str(exc)
            samples.append((time.perf_counter() - start) * 1000)
            counts.append(count[0])
        cpu = time.process_time() - cpu_start
        wall = time.perf_counter() - wall_start
        out = {
            "services": size,
            "iterations": iterations,
            "status": status,
            "median_ms": statistics.median(samples),
            "min_ms": min(samples),
            "max_ms": max(samples),
            "query_counts": counts,
            "search_stats": stats,
            "rss_bytes": psutil.Process().memory_info().rss,
            "cpu_one_core_percent": 100 * cpu / wall,
        }
        if len(samples) >= 30:
            ordered = sorted(samples)
            out["p50_ms"] = statistics.median(samples)
            out["p95_ms"] = ordered[int(0.95 * (len(ordered) - 1))]
            if len(samples) >= 100:
                out["p99_ms"] = ordered[int(0.99 * (len(ordered) - 1))]
        engine.dispose()
        return out


if __name__ == "__main__":

    def blocked(*args, **kwargs):
        raise RuntimeError("Outbound networking disabled during routing benchmark")

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    results = []
    for size in (100, 1000, 10000, 50000):
        value = run(size)
        results.append(value)
        print(json.dumps(value), flush=True)
    path = Path("models/benchmarks/phase3b-routing.json")
    path.write_text(
        json.dumps(
            {
                "fixture": "Synthetic single corridor; no fares or operations; warm Python process, fresh Session per search",
                "offline": "Python socket egress blocked; not OS firewall isolation",
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
