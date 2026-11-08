import json
import time
from pathlib import Path

from offline_guard import enforce_offline

enforce_offline()
from transformers import BertTokenizer

root = Path(__file__).resolve().parents[1]
texts = [
    "తిరుపతికి నెక్స్ట్ బస్సు ఎప్పుడు?",
    "Nellore ki fare entha?",
    "Vizag last bus eppudu?",
    "AC sleeper available aa?",
    "Guntur nunchi Tirumala ki bus unda?",
]
start = time.perf_counter()
tokenizer = BertTokenizer.from_pretrained(
    root / "models/muril-base", local_files_only=True
)
rows = [
    {
        "text": text,
        "tokens": tokenizer.tokenize(text),
        "token_ids": tokenizer.encode(text),
    }
    for text in texts
]
assert all(row["token_ids"] for row in rows)
report = {
    "status": "passed",
    "elapsed_seconds": time.perf_counter() - start,
    "network_guard": "Python socket audit hook",
    "forward_inference": "NOT_RUN_WEIGHTS_INCOMPLETE",
    "samples": rows,
}
(root / "models/benchmarks/muril-tokenization.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("All five tokenization samples passed under Python network guard")
