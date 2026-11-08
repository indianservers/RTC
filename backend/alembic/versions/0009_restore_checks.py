"""Restore legacy unnamed checks after SQLite batch field additions."""
from alembic import op
from app.domain import Base
from sqlalchemy import CheckConstraint, inspect

revision='0009'
down_revision='0008'
def upgrade():
    bind=op.get_bind()
    for table in Base.metadata.sorted_tables:
        expected=[c for c in table.constraints if isinstance(c,CheckConstraint)]
        existing={str(c['sqltext']) for c in inspect(bind).get_check_constraints(table.name)}
        missing=[c for c in expected if str(c.sqltext) not in existing]
        if missing:
            with op.batch_alter_table(table.name,copy_from=table) as batch:
                for i,c in enumerate(missing):
                    batch.create_check_constraint('ck_'+table.name+'_phase1a_'+str(i),str(c.sqltext))
def downgrade():
    pass  # Retain integrity constraints.
