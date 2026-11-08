import os

from alembic import context
from app.domain import Base
from sqlalchemy import create_engine

config = context.config
url = os.getenv('DATABASE_URL', config.get_main_option('sqlalchemy.url'))
with create_engine(url).connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
