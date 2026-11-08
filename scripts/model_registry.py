"""Compute immutable file hashes and record actual artifact presence."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def files(folder):
    result = []
    for p in sorted((root / folder).glob("*")):
        if not p.is_file():
            continue
        digest = hashlib.sha256()
        with p.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        result.append(
            {
                "path": p.relative_to(root).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    return result


source = json.loads((root / "models/benchmarks/muril-source.json").read_text())
entries = [
    {
        "name": "MuRIL Base Cased",
        "version": source["sha"],
        "source_repository": "https://huggingface.co/google/muril-base-cased",
        "revision": source["sha"],
        "local_path": "models/muril-base",
        "model_type": "masked_language_model_encoder",
        "framework": "PyTorch/Transformers",
        "languages": [
            "as",
            "bn",
            "en",
            "gu",
            "hi",
            "kn",
            "ks",
            "ml",
            "mr",
            "ne",
            "or",
            "pa",
            "sa",
            "sd",
            "ta",
            "te",
            "ur",
        ],
        "license": {
            "identifier": "Apache-2.0",
            "source": "https://huggingface.co/google/muril-base-cased",
        },
        "download_status": "pending",
        "load_verification_status": "pending",
        "files": files("models/muril-base"),
    },
    {
        "name": "IndicConformer Telugu",
        "version": "official-monolingual-hybrid-large",
        "source_repository": "https://github.com/AI4Bharat/IndicConformerASR",
        "revision": "checkpoint sha256 recorded per file; runtime 8dce88cf8e94963e2033c3137f7b9993b51db88a",
        "local_path": "models/indicconformer-telugu",
        "model_type": "hybrid_ctc_rnnt_asr",
        "framework": "AI4Bharat NeMo nemo-v2/PyTorch",
        "languages": ["te"],
        "license": {
            "identifier": "MIT",
            "source": "https://github.com/AI4Bharat/IndicConformerASR",
            "access": "HF repository gated; official public objectstore URL used",
        },
        "download_status": "incomplete",
        "expected_checkpoint_bytes": 523192320,
        "load_verification_status": "blocked: official NeMo requires triton, unavailable for this Windows/Python environment; reference audio absent",
        "files": files("models/indicconformer-telugu"),
    },
]
for entry in entries:
    if entry["name"].startswith("MuRIL"):
        required = {
            "config.json",
            "pytorch_model.bin",
            "tokenizer_config.json",
            "vocab.txt",
            "special_tokens_map.json",
        }
        entry["download_status"] = (
            "complete"
            if required.issubset({Path(x["path"]).name for x in entry["files"]})
            else "incomplete"
        )
        report = root / "models/benchmarks/muril-verification.json"
        if report.exists():
            entry["load_verification_status"] = json.loads(
                report.read_text(encoding="utf-8")
            )["status"]
        elif entry["download_status"] != "complete":
            entry["load_verification_status"] = "blocked: incomplete pytorch_model.bin"
# Preserve separately registered models and workflow decisions.
registry_path = root / "config/model_registry.yaml"
if registry_path.exists():
    previous = json.loads(registry_path.read_text(encoding="utf-8")).get("models", [])
    by_name = {e["name"]: e for e in entries}
    for old in previous:
        if old["name"] in by_name and "workflow_status" in old:
            by_name[old["name"]]["workflow_status"] = old["workflow_status"]
        elif old["name"] not in by_name:
            entries.append(old)
# JSON is valid YAML 1.2, avoiding a dependency in this inventory tool.
(root / "config/model_registry.yaml").write_text(
    json.dumps({"schema_version": 1, "models": entries}, indent=2), encoding="utf-8"
)
