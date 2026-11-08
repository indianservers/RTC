from alembic import op
from sqlalchemy import JSON, Column, String, inspect

revision = "0010"
down_revision = "0009"


def upgrade():
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns("nlp_intents")}
    with op.batch_alter_table("nlp_intents") as batch:
        for name in ["registry_kind", "intent_group", "capability", "canonical_id"]:
            if name not in existing:
                batch.add_column(
                    Column(
                        name,
                        String(36) if name == "canonical_id" else String(),
                        nullable=True,
                    )
                )
        if "taxonomy" not in existing:
            batch.add_column(Column("taxonomy", JSON(), nullable=True))
        if "canonical_id" not in existing:
            batch.create_foreign_key(
                "fk_nlp_intent_canonical", "nlp_intents", ["canonical_id"], ["id"]
            )
    if "specification" not in {
        c["name"] for c in inspect(bind).get_columns("nlp_entity_types")
    }:
        op.add_column(
            "nlp_entity_types", Column("specification", JSON(), nullable=True)
        )


def downgrade():
    pass  # Additive metadata retained to preserve taxonomy edits and legacy references.
