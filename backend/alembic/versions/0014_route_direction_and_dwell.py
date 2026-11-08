"""Optional route direction and separate elapsed arrival/departure defaults."""

from alembic import op
from sqlalchemy import Column, Integer, String, inspect

revision = "0014"
down_revision = "0013"


def upgrade():
    for table, columns in {
        "routes": [Column("direction", String(), nullable=True)],
        "route_stops": [
            Column("arrival_offset_minutes", Integer(), nullable=True),
            Column("departure_offset_minutes", Integer(), nullable=True),
        ],
    }.items():
        present = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in present:
                op.add_column(table, column)


def downgrade():
    pass  # Preserve approved route metadata and legacy-compatible timing defaults.
