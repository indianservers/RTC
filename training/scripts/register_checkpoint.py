"""Register an already trained checkpoint immutably; never initiates training."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("checkpoint")
parser.add_argument("version")
args = parser.parse_args()
if not re.fullmatch(r"intent-v[0-9]+\.[0-9]+\.[0-9]+", args.version):
    raise ValueError("Invalid model version")
root = Path(__file__).resolve().parents[2]
source = Path(args.checkpoint).resolve()
required = [
    "config.json",
    "tokenizer_config.json",
    "label_map.json",
    "metrics.json",
    "dataset_checksum.txt",
]
if not all((source / name).is_file() for name in required):
    raise ValueError("Incomplete checkpoint metadata")
target = root / "models/trained" / args.version
if target.exists():
    raise ValueError("Version already exists; versions are immutable")
shutil.copytree(source, target)
checksums = {}
for path in target.rglob("*"):
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        checksums[path.relative_to(target).as_posix()] = digest.hexdigest()
(target / "manifest.json").write_text(
    json.dumps({"version": args.version, "sha256": checksums}, indent=2)
)
