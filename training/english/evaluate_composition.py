"""Evaluate compositional intent parsing on the held-out synthetic multi-intent set."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain import database
from app.nlp.components import IntentClassifier, LanguageNormalizer
from app.nlp.content import NLPContentRepository
from app.nlp.taxonomy import IntentRegistry
from app.nlp.text_support import classify_extra
from sqlalchemy.orm import Session

manifest = json.loads(
    (ROOT / "training/datasets/splits/2c-v1/manifest.json").read_text()
)
rows = [
    json.loads(x)
    for x in (ROOT / manifest["files"]["synthetic_challenge"]["path"])
    .read_text(encoding="utf-8")
    .splitlines()
]
records = []
with Session(database()) as session:
    rules = IntentClassifier(NLPContentRepository(session).rules())
    taxonomy = IntentRegistry(session)
    for row in rows:
        if row["dataset_type"] != "MULTI_INTENT":
            continue
        text = LanguageNormalizer().normalize(row["text"])
        predictions = classify_extra(text, rules.classify(text), session)
        canonical = {spec.code if (spec := taxonomy.get(i)) else i for i in predictions}
        records.append(
            {
                "example_id": row["example_id"],
                "expected": row["intent_codes"],
                "predicted": sorted(canonical),
                "exact": canonical == set(row["intent_codes"]),
            }
        )
report = {
    "scope": "SYNTHETIC_UNREVIEWED_COMPOSITION_ONLY_NOT_DATABASE_ANSWER_ACCURACY",
    "records": len(records),
    "exact_match_accuracy": sum(r["exact"] for r in records) / len(records),
    "cases": records,
}
(ROOT / "models/benchmarks/phase2-final-composition.json").write_text(
    json.dumps(report, indent=2)
)
print({k: v for k, v in report.items() if k != "cases"})
