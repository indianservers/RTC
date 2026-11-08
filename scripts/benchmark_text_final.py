"""Database-grounded text-only benchmark with a fixed clock."""

import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from offline_guard import enforce_offline

enforce_offline()
from app.domain import database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from sqlalchemy.orm import Session

engine = database()
times = []
database_times = []
for _ in range(30):
    with Session(engine) as session:
        nlp = RTCNLPEngine(session)
        start = time.perf_counter()
        result = nlp.process(
            NLPRequest(
                text="When is the next bus to Guntur?",
                station_context="DEMO0",
                language="en",
                debug=True,
            ),
            datetime(2026, 11, 8, tzinfo=UTC),
            persist=False,
        )
        assert result.results and result.results[0]["results"]
        assert result.results[0]["results"][0]["dataset_source"] == "DEMO"
        times.append((time.perf_counter() - start) * 1000)
        database_times.append(result.debug.get("timings_ms", {}))
report = {
    "runs": len(times),
    "p50_end_to_end_ms": statistics.median(times),
    "p95_end_to_end_ms": sorted(times)[28],
    "timing_breakdowns_first_run": database_times[0],
    "hardware": platform.processor(),
    "clock": "2026-11-08T00:00:00+00:00",
    "dataset": "local fictional 100-service DEMO database",
    "network_guard": "Python audit hook; not OS isolation",
    "statistical_model": "not approved; deterministic DB fallback active",
}
(ROOT / "models/benchmarks/phase2-final-end-to-end.json").write_text(
    json.dumps(report, indent=2)
)
print(report)
