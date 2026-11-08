"""Add dated trips and sourced operational observations without altering v1."""

from alembic import op
from app import operations  # noqa: F401
from app.domain import Base
from sqlalchemy import inspect

revision = "0002"
down_revision = "0001"
TABLES = [
    "data_sources",
    "trips",
    "station_bays",
    "seat_availability_snapshots",
    "platform_assignments",
]


def upgrade():
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()
    for name in TABLES:
        if name not in existing:
            Base.metadata.tables[name].create(bind)


def downgrade():
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(op.get_bind())
