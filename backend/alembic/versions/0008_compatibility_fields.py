"""Add nullable compatibility fields without replacing existing records."""

from alembic import op
from app.domain import Base
from sqlalchemy import Column, inspect

revision = "0008"
down_revision = "0007"


def upgrade():
    bind = op.get_bind()
    for table in Base.metadata.sorted_tables:
        existing = {c["name"] for c in inspect(bind).get_columns(table.name)}
        missing = [c for c in table.columns if c.name not in existing]
        if missing:
            with op.batch_alter_table(table.name) as batch:
                for column in missing:
                    # Append nullable columns, then explicitly named foreign keys.
                    batch.add_column(Column(column.name, column.type, nullable=True))
                    for fk in column.foreign_keys:
                        batch.create_foreign_key(
                            "fk_" + table.name + "_" + column.name,
                            fk.column.table.name,
                            [column.name],
                            [fk.column.name],
                        )
                    if column.index:
                        batch.create_index(
                            "ix_" + table.name + "_" + column.name, [column.name]
                        )


def downgrade():
    # Non-destructive compatibility revision; columns retained to avoid losing values.
    pass
