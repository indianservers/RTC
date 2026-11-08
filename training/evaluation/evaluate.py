"""Evaluate explicit reference/prediction pairs without any model calls."""

import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("predictions")
a = p.parse_args()
rows = [
    json.loads(s) for s in Path(a.predictions).read_text(encoding="utf-8").splitlines()
]
assert rows and all("reference_intent" in r and "predicted_intent" in r for r in rows)
labels = sorted(
    {r["reference_intent"] for r in rows} | {r["predicted_intent"] for r in rows}
)
print(
    json.dumps(
        {
            "count": len(rows),
            "accuracy": sum(
                r["reference_intent"] == r["predicted_intent"] for r in rows
            )
            / len(rows),
            "labels": labels,
        }
    )
)
