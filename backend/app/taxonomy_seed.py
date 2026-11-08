"""Idempotent initial registration; retain existing daily metadata edits and IDs."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .catalog import EntityType, Intent, Utterance
from .domain import database


def seed_taxonomy(engine, refresh=False):
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (root / "training/config/intent_registry.yaml").read_text(encoding="utf-8")
    )
    entities = json.loads(
        (root / "training/config/entity_registry.yaml").read_text(encoding="utf-8")
    )
    acts = json.loads(
        (root / "training/config/dialogue_acts.yaml").read_text(encoding="utf-8")
    )
    with Session(engine) as s, s.begin():
        existing = {r.code: r for r in s.scalars(select(Intent))}
        for spec in manifest["intents"]:
            row = existing.get(spec["code"])
            if row is None:
                row = Intent(code=spec["code"], description=spec["definition"])
                s.add(row)
                s.flush()
                existing[row.code] = row
            if row.taxonomy is None or refresh:
                row.registry_kind = "ENQUIRY"
                row.intent_group = spec["intent_group"]
                row.capability = spec["capability"]
                row.taxonomy = spec
                row.required_slots_json = spec["required_slots"]
                row.optional_slots_json = spec["optional_slots"]
                row.display_name = spec["display_name"]
            for text in spec["examples"]:
                if not s.scalar(
                    select(Utterance.id)
                    .where(
                        Utterance.intent_id == row.id,
                        Utterance.text == text,
                        Utterance.source_type == "TAXONOMY_SEED",
                    )
                    .limit(1)
                ):
                    s.add(
                        Utterance(
                            intent_id=row.id,
                            text=text,
                            language="en",
                            source_type="TAXONOMY_SEED",
                            quality_status="PENDING_HUMAN_REVIEW",
                            dataset_split=None,
                        )
                    )
        for alias, canonical in manifest["legacy_aliases"].items():
            row = existing.get(alias)
            if row is None:
                row = Intent(
                    code=alias, description="Compatibility alias for " + canonical
                )
                s.add(row)
                s.flush()
                existing[alias] = row
            row.registry_kind = "LEGACY_ALIAS"
            row.canonical_id = existing[canonical].id
        for act in acts["dialogue_acts"]:
            row = existing.get(act["code"])
            if row is None:
                row = Intent(code=act["code"], description="Dialogue act")
                s.add(row)
                existing[row.code] = row
            if row.registry_kind is None:
                row.registry_kind = "DIALOGUE_ACT"
                row.taxonomy = act
        for spec in entities["entities"]:
            row = s.scalar(select(EntityType).where(EntityType.code == spec["code"]))
            if row is None:
                row = EntityType(code=spec["code"])
                s.add(row)
            if row.specification is None:
                row.specification = spec
        for row in existing.values():
            if row.registry_kind is None:
                row.registry_kind = (
                    "INTERNAL" if row.code == "DIALOGUE_CONTENT" else "LEGACY_UNMAPPED"
                )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Explicitly replace existing canonical metadata from the approved seed manifest",
    )
    seed_taxonomy(database(), refresh=parser.parse_args().refresh)
