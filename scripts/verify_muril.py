import json
import platform
import time
from pathlib import Path

from offline_guard import enforce_offline

enforce_offline()
import psutil
import torch
from transformers import AutoModel, AutoTokenizer

root = Path(__file__).resolve().parents[1]
path = root / "models/muril-base"
start = time.perf_counter()
tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
model = AutoModel.from_pretrained(path, local_files_only=True).eval()
loading = time.perf_counter() - start
texts = [
    "తిరుపతికి నెక్స్ట్ బస్సు ఎప్పుడు?",
    "Nellore ki fare entha?",
    "Vizag last bus eppudu?",
    "AC sleeper available aa?",
    "Guntur nunchi Tirumala ki bus unda?",
]
start = time.perf_counter()
inputs = tokenizer(texts, padding=True, return_tensors="pt")
with torch.inference_mode():
    output = model(**inputs)
assert torch.isfinite(output.last_hidden_state).all()
report = {
    "status": "passed",
    "network_guard": "Python socket audit hooks; OS firewall isolation not verified",
    "model_load_seconds": loading,
    "forward_seconds": time.perf_counter() - start,
    "shape": list(output.last_hidden_state.shape),
    "texts": texts,
    "token_counts": inputs["attention_mask"].sum(dim=1).tolist(),
    "peak_memory_bytes": psutil.Process().memory_info().peak_wset,
    "torch": torch.__version__,
    "python": platform.python_version(),
    "cuda": torch.cuda.is_available(),
    "note": "Encoder forward test only; no RTC intent classifier exists.",
}
(root / "models/benchmarks/muril-verification.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps({k: v for k, v in report.items() if k != "texts"}, indent=2))
