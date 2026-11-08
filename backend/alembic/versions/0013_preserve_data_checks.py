"""Restore deterministic named checks after legacy SQLite table rebuilds."""

from alembic import op
from sqlalchemy import inspect

revision = "0013"
down_revision = "0012"


def upgrade():
    required = {
        "services": [
            (
                "ck_services_phase5a_valid",
                "departure_minutes >= 0 AND departure_minutes < 1440 AND valid_to >= valid_from",
            )
        ],
        "fare_rules": [
            ("ck_fare_rules_phase5a_min", "per_km >= 0 AND minimum >= 0"),
            (
                "ck_fare_rule_effective_components",
                "flat_surcharge >= 0 AND percent_surcharge >= 0 AND (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)",
            ),
        ],
    }

    def normalize(expression):
        return "".join(expression.lower().replace('"', "").split())

    for table, rules in required.items():
        existing = inspect(op.get_bind()).get_check_constraints(table)
        present = {normalize(c["sqltext"]) for c in existing}
        names = {c["name"] for c in existing}
        missing = [
            (name, rule)
            for name, rule in rules
            if name not in names and normalize(rule) not in present
        ]
        if missing:
            with op.batch_alter_table(table) as batch:
                for name, rule in missing:
                    batch.create_check_constraint(name, rule)


def downgrade():
    pass  # Integrity protection is retained along with publication audit history.
