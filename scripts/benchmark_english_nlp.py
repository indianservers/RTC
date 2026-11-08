"""Benchmark explicit local candidate artifacts with Python socket egress denied."""

import json
import statistics
import time
from pathlib import Path

from offline_guard import enforce_offline

enforce_offline()
import joblib
import psutil
import tensorflow as tf

root = Path(__file__).resolve().parents[1]
folder = root / "models/english/nlp/pilot-v2"
labels = json.loads((folder / "label_map.json").read_text())
samples = [
    "When is the next bus to Nellore?",
    "No AC buses",
    "What is the fare?",
    "Which platform should I stand at?",
]
report = {}
for name, file in [("svm", "svm.joblib"), ("textcnn", "textcnn.keras")]:
    start = time.perf_counter()
    model = (
        joblib.load(folder / file)
        if name == "svm"
        else tf.keras.models.load_model(folder / file)
    )
    load = time.perf_counter() - start

    def infer(text, name=name, model=model):
        if name == "svm":
            return str(model.predict([text])[0])
        return labels[
            int(model(tf.constant([text]), training=False).numpy().argmax(axis=1)[0])
        ]

    infer(samples[0])
    timings = []
    predictions = []
    for text in samples * 10:
        start = time.perf_counter()
        predictions.append(infer(text))
        timings.append((time.perf_counter() - start) * 1000)
    sorted_times = sorted(timings)
    report[name] = {
        "load_seconds": load,
        "median_ms": statistics.median(timings),
        "p95_ms": sorted_times[int(len(timings) * 0.95) - 1],
        "model_bytes": (folder / file).stat().st_size,
        "peak_process_memory_bytes": psutil.Process().memory_info().peak_wset,
        "predictions_first_four": predictions[:4],
        "quality": "UNREVIEWED_PILOT_NOT_FOR_DEPLOYMENT",
        "network_guard": "Python socket audit hook; OS isolation not verified",
    }
(root / "models/benchmarks/phase2-pilot-inference.json").write_text(
    json.dumps(report, indent=2)
)
print(json.dumps(report, indent=2))
