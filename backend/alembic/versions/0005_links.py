from alembic import op
from app import catalog, links, operations, records  # noqa: F401
from app.domain import Base
from sqlalchemy import inspect

revision = "0005"
down_revision = "0004"
NAMES = ["station_geography", "service_vehicles", "route_variant_stops"]


def upgrade():
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()
    for table in Base.metadata.sorted_tables:
        if table.name in NAMES and table.name not in existing:
            table.create(bind)


def downgrade():
    for name in reversed(NAMES):
        Base.metadata.tables[name].drop(op.get_bind())
