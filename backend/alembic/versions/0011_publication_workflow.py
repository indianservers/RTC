"""Extend existing import and audit records; no parallel domain/version tables."""

from alembic import op
from sqlalchemy import JSON, Column, DateTime, Integer, String, inspect

revision = "0011"
down_revision = "0010"


def upgrade():
    bind = op.get_bind()
    fields = {
        "data_import_batches": [
            Column("operator_id", String(36)),
            Column("source_id", String(36)),
            Column(
                "workflow_state", String(), nullable=False, server_default="PUBLISHED"
            ),
            Column("source_filename", String()),
            Column("source_checksum", String()),
            Column("uploaded_by", String()),
            Column("approved_by", String()),
            Column("published_by", String()),
            Column("created_at", DateTime(timezone=True)),
            Column("published_at", DateTime(timezone=True)),
            Column("payload", JSON()),
            Column("validation_report", JSON()),
            Column(
                "validation_error_count", Integer(), nullable=False, server_default="0"
            ),
            Column("revision", Integer(), nullable=False, server_default="1"),
        ],
        "audit_logs": [
            Column("batch_id", String(36)),
            Column("operator_id", String(36)),
            Column("version", Integer()),
            Column("previous_values", JSON()),
            Column("new_values", JSON()),
            Column("changed_fields", JSON()),
            Column("reason", String()),
        ],
    }
    for table, columns in fields.items():
        existing = {c["name"] for c in inspect(bind).get_columns(table)}
        with op.batch_alter_table(table) as batch:
            for column in columns:
                if column.name not in existing:
                    batch.add_column(column)
        references = {
            "data_import_batches": {
                "operator_id": "transport_operators",
                "source_id": "data_sources",
            },
            "audit_logs": {
                "operator_id": "transport_operators",
                "batch_id": "data_import_batches",
            },
        }[table]
        existing_fk = {
            tuple(f["constrained_columns"])
            for f in inspect(bind).get_foreign_keys(table)
        }
        with op.batch_alter_table(table) as batch:
            for name, target in references.items():
                if (name,) not in existing_fk:
                    batch.create_foreign_key(
                        "fk_" + table + "_" + name, target, [name], ["id"]
                    )
        for name in (
            ("operator_id", "workflow_state")
            if table == "data_import_batches"
            else ("batch_id", "operator_id")
        ):
            index = "ix_" + table + "_" + name
            if index not in {i["name"] for i in inspect(bind).get_indexes(table)}:
                op.create_index(index, table, [name])


def downgrade():
    # Retain reversible history rather than deleting operator audit evidence.
    pass
