"""Phase 1A additive relationships. Retain all existing application tables."""

from alembic import op
from app import catalog, links, operations, records, schema1a  # noqa: F401
from app.domain import Base

revision = "0007"
down_revision = "0006"
NAMES = [
    "operator_service_areas",
    "operator_station_access",
    "amenities",
    "station_contact_points",
    "nlp_entity_annotations",
    "admin_users",
    "admin_roles",
    "admin_user_roles",
]


def upgrade():
    bind = op.get_bind()
    for table in Base.metadata.sorted_tables:
        if table.name in NAMES:
            table.create(bind, checkfirst=True)


def downgrade():
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in NAMES:
            table.drop(op.get_bind(), checkfirst=True)
