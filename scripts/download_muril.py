import json
from pathlib import Path

from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parents[1]
info = json.loads((root / "models/benchmarks/muril-source.json").read_text())
snapshot_download(
    "google/muril-base-cased",
    revision=info["sha"],
    local_dir=root / "models/muril-base",
    allow_patterns=[
        "config.json",
        "pytorch_model.bin",
        "tokenizer_config.json",
        "vocab.txt",
        "special_tokens_map.json",
        "README.md",
    ],
)
print("MuRIL download complete", flush=True)
