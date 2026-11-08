"""Distinguish an observed boarding platform from dispatcher confirmation."""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"


def upgrade():
    if "assignment_kind" not in {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("platform_assignments")
    }:
        op.add_column(
            "platform_assignments",
            sa.Column("assignment_kind", sa.String(), nullable=True),
        )


def downgrade():
    pass
