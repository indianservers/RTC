"""Reproducible text-only benchmark. Runs with socket egress denied and temporary demo DB."""

import argparse
import json
import statistics
import sys
import tempfile
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from offline_guard import enforce_offline

enforce_offline()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import catalog, links, operations, records, schema1a  # noqa: F401
from app.demo import enrich
from app.domain import Base, database
from app.nlp.pipeline import NLPRequest, RTCNLPEngine
from app.nlp_seed import seed_nlp
from app.seed import seed
from sqlalchemy.orm import Session


def summary(values):
    ordered = sorted(values)
    return {
        "samples": len(values),
        "median_ms": statistics.median(values),
        "p95_ms": ordered[max(0, int(len(values) * 0.95) - 1)],
        "max_ms": max(values),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("iterations must be positive")
    now = datetime(2026, 11, 8, tzinfo=UTC)
    metrics = {
        k: []
        for k in (
            "intent_inference_ms",
            "entity_extraction_ms",
            "database_lookup_ms",
            "end_to_end_ms",
        )
    }
    tracemalloc.start()
    with tempfile.TemporaryDirectory() as directory:
        db = database("sqlite:///" + str(Path(directory) / "benchmark.db"))
        Base.metadata.create_all(db)
        seed(db)
        enrich(db)
        seed_nlp(db)
        from app.taxonomy_seed import seed_taxonomy

        seed_taxonomy(db)
        with Session(db) as session:
            engine = RTCNLPEngine(session)
            request = NLPRequest(
                text="Next bus to Guntur and ticket fare",
                station_context="DEMO0",
                language="en",
                debug=True,
            )
            engine.process(request, now, persist=False)
            for _ in range(args.iterations):
                start = perf_counter()
                result = engine.process(request, now, persist=False)
                metrics["end_to_end_ms"].append((perf_counter() - start) * 1000)
                for key in (
                    "intent_inference_ms",
                    "entity_extraction_ms",
                    "database_lookup_ms",
                ):
                    metrics[key].append(result.debug["timings_ms"][key])
            runtime_model = engine.english_model.predict("When is the next bus?")
        db.dispose()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory = {"python_traced_current_bytes": current, "python_traced_peak_bytes": peak}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                *[
                    (n, ctypes.c_size_t)
                    for n in (
                        "PeakWorkingSetSize",
                        "WorkingSetSize",
                        "QuotaPeakPagedPoolUsage",
                        "QuotaPagedPoolUsage",
                        "QuotaPeakNonPagedPoolUsage",
                        "QuotaNonPagedPoolUsage",
                        "PagefileUsage",
                        "PeakPagefileUsage",
                    )
                ],
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            memory.update(
                working_set_bytes=counters.WorkingSetSize,
                peak_working_set_bytes=counters.PeakWorkingSetSize,
            )
    report = {
        "source": "temporary DEMO SQLite fixtures",
        "python": sys.version,
        "network": "Python socket egress blocked; not OS isolation",
        "mode": "warm deterministic runtime; debug enabled; tracemalloc enabled",
        "runtime_model": runtime_model,
        "metrics": {k: summary(v) for k, v in metrics.items()},
        "memory": memory,
        "notes": [
            "Database metric includes typed enquiry, formatting labels and ORM queries; excludes connection initialization.",
            "Intent metric includes registry mapping and fallback check.",
            "This is latency measurement, not independent intent-accuracy validation.",
        ],
    }
    output = ROOT / "docs/text-benchmark.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
