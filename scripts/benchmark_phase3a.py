"""Reproducible in-memory SQLite text-conversation benchmark; no audio or network."""

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
import psutil
from app.demo import enrich
from app.domain import Base, database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp_seed import seed_nlp
from app.seed import seed
from app.taxonomy_seed import seed_taxonomy
from sqlalchemy.orm import Session

engine = database("sqlite://")
Base.metadata.create_all(engine)
seed(engine)
enrich(engine)
seed_nlp(engine)
seed_taxonomy(engine)
metrics = {
    key: []
    for key in [
        "total_ms",
        "intent_inference_ms",
        "context_update_ms",
        "database_lookup_ms",
    ]
}
process = psutil.Process()
cpu_before = sum(process.cpu_times()[:2])
started = time.perf_counter()
with Session(engine) as session:
    nlp = RTCNLPEngine(session)
    sid = None
    for _ in range(100):
        start = time.perf_counter()
        result = nlp.process(
            NLPRequest(
                text="Next bus to Guntur",
                station_context="DEMO0",
                session_id=sid,
                language="en",
                debug=True,
            ),
            datetime(2026, 11, 8, tzinfo=UTC),
        )
        assert (
            result.results
            and result.results[0]["results"]
            and result.context["revision"] > 0
        )
        sid = result.session_id
        metrics["total_ms"].append((time.perf_counter() - start) * 1000)
        for key, bucket in metrics.items():
            if key != "total_ms" and key in result.debug["timings_ms"]:
                bucket.append(result.debug["timings_ms"][key])
elapsed = time.perf_counter() - started
report = {
    "runs": 100,
    "scenario": "same active enquiry with persisted in-transaction state, fictional 100-service fixture",
    "hardware": platform.processor(),
    "memory_rss_bytes": process.memory_info().rss,
    "cpu_percent_one_core": 100 * (sum(process.cpu_times()[:2]) - cpu_before) / elapsed,
    "network_guard": "Python socket audit only",
    "metrics": {},
}
for key, values in metrics.items():
    values = sorted(values)
    report["metrics"][key] = {
        "samples": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": values[int(len(values) * 0.95) - 1],
        "p99_ms": values[int(len(values) * 0.99) - 1],
    }
report["limitation"] = (
    "Context stage includes station resolution; memory is process RSS, not model-specific peak. This is a happy-path microbenchmark, not passenger accuracy or concurrent-load certification."
)
(ROOT / "models/benchmarks/phase3a-latency.json").write_text(
    json.dumps(report, indent=2)
)
print(json.dumps(report, indent=2))
