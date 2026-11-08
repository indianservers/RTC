import os

from alembic import context
from app.domain import Base
from sqlalchemy import create_engine

config = context.config
url = os.getenv('DATABASE_URL', config.get_main_option('sqlalchemy.url'))
migration_engine = create_engine(url)
try:
    with migration_engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
finally:
    migration_engine.dispose()
