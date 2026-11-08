"""Real loopback concurrency benchmark; never trains or publishes operational facts."""

import argparse
import json
import math
import os
import platform
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
import psutil


def percentile(values, fraction):
    return (
        sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]
        if values
        else None
    )


def run(url, pid):
    process = psutil.Process(pid)
    report = {
        "hardware": {
            "os": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": psutil.cpu_count(),
            "physical_cpus": psutil.cpu_count(logical=False),
            "ram_bytes": psutil.virtual_memory().total,
        },
        "target": url,
        "dataset": "LABELLED DEMO local installation",
        "model": "Measured configured runtime; no approved model assumed",
        "runs": [],
    }
    # Fail before timing a meaningless empty-selection workload.
    with httpx.Client(base_url=url, trust_env=False, timeout=90) as probe:
        owner = uuid4().hex + uuid4().hex
        first = probe.post(
            "/api/v1/conversation/message",
            json={
                "text": "Next bus to Nellore tomorrow?",
                "station_context": "Vijayawada",
                "owner_token": owner,
            },
        ).json()
        if not first.get("result_set"):
            raise ValueError(
                "Benchmark fixture has no Nellore services; publish labelled future DEMO data first"
            )
        selected = probe.post(
            "/api/v1/conversation/message",
            json={"text": "1", "owner_token": owner, "session_id": first["session_id"]},
        ).json()
        if not selected.get("selected_journey"):
            raise ValueError("Benchmark selection probe failed")
    for concurrency in (1, 5, 10, 25, 50):
        samples, errors, phases = [], [], []
        rss = []
        stop = threading.Event()

        def monitor(stop=stop, rss=rss):
            while not stop.wait(0.1):
                rss.append(process.memory_info().rss)

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        cpu_before = process.cpu_times()
        started = perf_counter()

        def kiosk(_):
            session = None
            owner = uuid4().hex + uuid4().hex
            local = []
            with httpx.Client(base_url=url, trust_env=False, timeout=180) as client:
                for question in (
                    "Next bus to Nellore tomorrow?",
                    "1",
                    "What is the fare?",
                    "What are the stops?",
                    "Connecting buses to Tirupati tomorrow?",
                    "How long does it take?",
                ):
                    body = {
                        "text": question,
                        "language": "en",
                        "owner_token": owner,
                        "station_context": "Vijayawada",
                        "debug": True,
                    }
                    if session:
                        body["session_id"] = session
                    t = perf_counter()
                    try:
                        response = client.post(
                            "/api/v1/conversation/message",
                            json=body,
                            headers={
                                "Authorization": "Bearer "
                                + os.environ["RTC_ADMIN_TOKEN"]
                            },
                        )
                        data = response.json()
                        session = data.get("session_id", session)
                        local.append(
                            (
                                (perf_counter() - t) * 1000,
                                response.status_code,
                                data.get("debug", {}).get("timings_ms", {}),
                            )
                        )
                    except (httpx.HTTPError, ValueError):
                        local.append(((perf_counter() - t) * 1000, 0, {}))
            return local

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for result in pool.map(kiosk, range(concurrency)):
                for duration, status, timing in result:
                    samples.append(duration)
                    if not 200 <= status < 300:
                        errors.append(status)
                    phases.append(timing)
        elapsed = perf_counter() - started
        stop.set()
        watcher.join()
        cpu_after = process.cpu_times()
        report["runs"].append(
            {
                "concurrent_kiosks": concurrency,
                "requests": len(samples),
                "elapsed_seconds": elapsed,
                "p50_ms": percentile(samples, 0.5),
                "p95_ms": percentile(samples, 0.95),
                "p99_ms": percentile(samples, 0.99),
                "requests_per_second": len(samples) / elapsed,
                "error_count": len(errors),
                "error_statuses": errors,
                "error_rate": len(errors) / len(samples),
                "process_cpu_percent": (
                    (cpu_after.user + cpu_after.system)
                    - (cpu_before.user + cpu_before.system)
                )
                / elapsed
                * 100,
                "peak_sampled_rss_bytes": max(rss)
                if rss
                else process.memory_info().rss,
                "phase_timings": phases,
            }
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--server-pid", type=int, required=True)
    a = parser.parse_args()
    data = run(a.url, a.server_pid)
    Path("docs/phase5e-benchmark.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            [
                {k: v for k, v in r.items() if k != "phase_timings"}
                for r in data["runs"]
            ],
            indent=2,
        )
    )
