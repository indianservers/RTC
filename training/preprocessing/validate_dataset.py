"""Dataset preparation only. This does not initiate fine-tuning."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("dataset")
args = parser.parse_args()
rows = [
    json.loads(x) for x in Path(args.dataset).read_text(encoding="utf-8").splitlines()
]
seen = {}
for n, row in enumerate(rows, 1):
    assert all(row.get(k) for k in ("text", "intent", "language", "split")), (
        f"Invalid row {n}"
    )
    assert row["split"] in ("train", "validation", "test")
    key = row["text"].strip().casefold()
    assert key not in seen or seen[key] == row["split"], "Split leakage"
    seen[key] = row["split"]
print({"rows": len(rows), "labels": sorted({r["intent"] for r in rows})})
