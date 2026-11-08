"""Extend existing trip projection, audit envelope and scoped grants."""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"


def upgrade():
    tables = {
        "trips": [
            sa.Column(
                "operational_version", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("operational_state", sa.JSON()),
        ],
        "admin_user_roles": [sa.Column("station_id", sa.String())],
        "audit_logs": [
            sa.Column("idempotency_key", sa.String()),
            sa.Column("station_id", sa.String()),
            sa.Column("source_id", sa.String()),
            sa.Column("occurred_at", sa.DateTime(timezone=True)),
        ],
        "service_disruptions": [
            sa.Column("disruption_type", sa.String()),
            sa.Column("severity", sa.String()),
            sa.Column("details", sa.JSON()),
            sa.Column("approved_by", sa.String()),
        ],
    }
    for table, columns in tables.items():
        present = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in present:
                op.add_column(table, column)
    for table, mappings in {
        "admin_user_roles": {"station_id": "bus_stations"},
        "audit_logs": {"station_id": "bus_stations", "source_id": "data_sources"},
    }.items():
        inspector = sa.inspect(op.get_bind())
        existing = {
            tuple(f["constrained_columns"]) for f in inspector.get_foreign_keys(table)
        }
        with op.batch_alter_table(table) as batch:
            for column, target in mappings.items():
                if (column,) not in existing:
                    batch.create_foreign_key(
                        f"fk_{table}_{column}", target, [column], ["id"]
                    )
    inspector = sa.inspect(op.get_bind())
    if not any(
        "idempotency_key" in c["column_names"]
        for c in inspector.get_unique_constraints("audit_logs")
    ):
        with op.batch_alter_table("audit_logs") as batch:
            batch.create_unique_constraint(
                "uq_audit_idempotency_key", ["idempotency_key"]
            )


def downgrade():
    pass  # Preserve dispatcher history and projection data.
