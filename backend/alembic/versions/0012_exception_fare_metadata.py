"""Date-specific approved exceptions and dated fare-rule components."""

from alembic import op
from sqlalchemy import JSON, Column, Date, Numeric, String, inspect

revision = "0012"
down_revision = "0011"


def upgrade():
    fields = {
        "services": [
            Column("depot_id", String(36)),
            Column("service_type", String(), nullable=False, server_default="REGULAR"),
        ],
        "service_calendar_exceptions": [
            Column("exception_type", String()),
            Column("reason", String()),
            Column("details", JSON()),
        ],
        "fare_rules": [
            Column("valid_from", Date()),
            Column("valid_to", Date()),
            Column("flat_surcharge", Numeric(), nullable=False, server_default="0"),
            Column("percent_surcharge", Numeric(), nullable=False, server_default="0"),
        ],
    }
    for table, columns in fields.items():
        existing = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
        with op.batch_alter_table(table) as batch:
            for column in columns:
                if column.name not in existing:
                    batch.add_column(column)
    if "ck_fare_rule_effective_components" not in {
        c["name"] for c in inspect(op.get_bind()).get_check_constraints("fare_rules")
    }:
        with op.batch_alter_table("fare_rules") as batch:
            batch.create_check_constraint(
                "ck_fare_rule_effective_components",
                "flat_surcharge >= 0 AND percent_surcharge >= 0 AND (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)",
            )
    existing = {
        tuple(f["constrained_columns"])
        for f in inspect(op.get_bind()).get_foreign_keys("services")
    }
    if ("depot_id",) not in existing:
        with op.batch_alter_table("services") as batch:
            batch.create_foreign_key("fk_service_depot", "depots", ["depot_id"], ["id"])


def downgrade():
    pass  # Approved operational history is retained.
