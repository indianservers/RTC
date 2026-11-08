"""Validate versioned taxonomy manifests without network or model dependencies."""

import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = root / "training/config"
intents = json.loads((config / "intent_registry.yaml").read_text())
entities = json.loads((config / "entity_registry.yaml").read_text())["entities"]
acts = json.loads((config / "dialogue_acts.yaml").read_text())
records = intents["intents"]
codes = {r["code"] for r in records}
assert len(records) == len(codes) == 60
assert len({r["definition"] for r in records}) == 60
assert len(entities) == len({e["code"] for e in entities}) == 32
assert len(acts["dialogue_acts"]) == 14
assert not codes.intersection(a["code"] for a in acts["dialogue_acts"])
assert set(intents["legacy_aliases"].values()) <= codes
for r in records:
    assert r["required_slots"] or r["required_slot_alternatives"]
    assert r["clarifications"] and len(r["examples"]) >= 5
    assert r["capability"] in ("IMPLEMENTED", "PARTIAL", "UNSUPPORTED")
    assert not set(r["required_slots"]).intersection(r["optional_slots"])
    if r["capability"] == "UNSUPPORTED":
        assert r["backend_code"] is None
for pair in intents["ambiguity_matrix"]:
    assert pair["left"] in codes and pair["right"] in codes
for c in acts["compositions"]:
    assert set(c["intents"]) <= codes
examples = [
    json.loads(s)
    for s in (root / "training/datasets/phase2a_seed_examples.jsonl")
    .read_text()
    .splitlines()
]
assert len(examples) == len({r["text"].casefold() for r in examples}) == 300
assert Counter(r["intent"] for r in examples) == Counter({code: 5 for code in codes})
print(
    json.dumps(
        {
            "canonical_intents": len(codes),
            "groups": dict(Counter(r["intent_group"] for r in records)),
            "capabilities": dict(Counter(r["capability"] for r in records)),
            "entities": len(entities),
            "dialogue_acts": len(acts["dialogue_acts"]),
            "examples": len(examples),
            "human_reviewed_examples": 0,
            "ambiguous_pairs": len(intents["ambiguity_matrix"]),
        },
        indent=2,
    )
)
