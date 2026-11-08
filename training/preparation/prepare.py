"""Finalize family/parent/near-duplicate grouped synthetic snapshots."""

import hashlib
import json
import stat
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from training.validation.validate_phase2b import normalize, validate


def prepare(source, output):
    if output.exists():
        raise ValueError("Dataset version already exists; refusing to overwrite")
    rows = [
        json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()
    ]
    registry = json.loads((ROOT / "training/config/intent_registry.yaml").read_text())
    vocabulary = json.loads(
        (source.parent / "vocabulary.json").read_text(encoding="utf-8")
    )
    audit = validate(rows, registry, vocabulary)
    if audit["schema_errors"]:
        raise ValueError("Dataset schema errors must be resolved first")
    parents = {r["example_id"]: r["example_id"] for r in rows}

    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)

    families = {}
    sources = {}
    for row in rows:
        identifier = row["example_id"]
        family = row["template_family"]
        if family in families:
            union(identifier, families[family])
        families[family] = identifier
        if row["parent_example_id"]:
            union(identifier, row["parent_example_id"])
        key = row["provenance"].get("source_example_sha256")
        if key:
            if key in sources:
                union(identifier, sources[key])
            sources[key] = identifier
    normalized = [normalize(r["text"]) for r in rows]
    for i, left in enumerate(rows):
        for j in range(i + 1, len(rows)):
            if SequenceMatcher(None, normalized[i], normalized[j]).ratio() >= 0.9:
                union(left["example_id"], rows[j]["example_id"])
    groups = defaultdict(list)
    for row in rows:
        groups[find(row["example_id"])].append(row)
    splits = defaultdict(list)
    for identifier, group in sorted(groups.items()):
        indexes = [
            int(r["template_family"].rsplit(":", 1)[1])
            for r in group
            if r["dataset_type"] in ("SINGLE_INTENT", "ASR_STYLE")
        ]
        if (
            any(r["dataset_type"] not in ("SINGLE_INTENT", "ASR_STYLE") for r in group)
            or 4 in indexes
        ):
            split = "synthetic_challenge"
        elif 3 in indexes:
            split = "validation"
        else:
            split = "train"
        for row in group:
            splits[split].append({**row, "split": split, "leakage_group": identifier})
    output.mkdir(parents=True)
    files = {}
    for split in ("train", "validation", "synthetic_challenge"):
        path = output / (split + ".jsonl")
        payload = (
            "\n".join(
                json.dumps(r, sort_keys=True, ensure_ascii=False)
                for r in sorted(splits[split], key=lambda r: r["example_id"])
            )
            + "\n"
        )
        path.write_text(payload, encoding="utf-8")
        path.chmod(stat.S_IREAD)
        files[split] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "records": len(splits[split]),
            "intent_distribution": dict(
                Counter(i for r in splits[split] for i in r["intent_codes"])
            ),
        }
    manifest = {
        "version": output.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_records": len(rows),
        "files": files,
        "independent_test": None,
        "independent_test_records": 0,
        "source_type_distribution": dict(Counter(r["source_type"] for r in rows)),
        "generation_versions": sorted({r["generator_version"] for r in rows}),
        "split_seed": 42,
        "split_strategy": "authored-family-index 0/1/2 train, 3 validation, 4 challenge; transitive near-duplicate/parent groups take strongest holdout",
        "leakage_groups": len(groups),
        "validation_rules": [
            "canonical labels",
            "exact spans",
            "real master IDs",
            "parent links",
            "all normalized near-duplicates >=0.9 remain grouped",
        ],
        "limitations": [
            "All data synthetic/unreviewed",
            "Only five authored phrases per intent",
            "No independent real-world test set",
            "Read-only file attribute plus checksum enforcement is not tamper-proof storage",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    manifest = prepare(
        ROOT / "training/datasets/generated/2b-v1/all.jsonl",
        ROOT / "training/datasets/splits/2c-v1",
    )
    print(
        json.dumps(
            {
                "counts": {k: v["records"] for k, v in manifest["files"].items()},
                "independent_test": 0,
                "groups": manifest["leakage_groups"],
            },
            indent=2,
        )
    )
