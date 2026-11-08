from alembic import op
from app import catalog, links, operations, records  # noqa: F401
from app.domain import Base

revision = "0006"
down_revision = "0005"


def upgrade():
    Base.metadata.create_all(op.get_bind())


def downgrade():
    pass  # Repairs missing tables only; retain existing data on downgrade.
