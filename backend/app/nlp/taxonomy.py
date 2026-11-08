"""Read taxonomy from DB; seed manifests are not runtime configuration."""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from ..catalog import EntityType, Intent
from ..local_intents import enrich_definition


class IntentDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")
    code: str
    intent_group: str
    definition: str
    required_slots: list[str]
    optional_slots: list[str]
    capability: str
    examples: list[str]
    backend_code: str | None = None


class IntentRegistry:
    def __init__(self, session):
        self.session = session

    def resolve(self, code):
        row = self.session.scalar(
            select(Intent).where(Intent.code == code.upper(), Intent.active.is_(True))
        )
        if row and row.canonical_id:
            row = self.session.get(Intent, row.canonical_id)
        return row if row and row.active and row.registry_kind == "ENQUIRY" else None

    def get(self, code):
        row = self.resolve(code)
        return (
            IntentDefinition.model_validate(enrich_definition(row.taxonomy))
            if row and row.taxonomy
            else None
        )

    def list(self, limit=60, offset=0):
        rows = self.session.scalars(
            select(Intent)
            .where(Intent.registry_kind == "ENQUIRY", Intent.active.is_(True))
            .order_by(Intent.code)
            .offset(offset)
            .limit(limit)
        )
        return [
            IntentDefinition.model_validate(enrich_definition(r.taxonomy))
            for r in rows
            if r.taxonomy
        ]

    def entities(self):
        rows = self.session.scalars(
            select(EntityType)
            .where(EntityType.active.is_(True), EntityType.specification.is_not(None))
            .order_by(EntityType.code)
        )
        return [r.specification for r in rows]
