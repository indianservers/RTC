from alembic import op
from app import catalog, links, operations, records  # noqa: F401
from app.domain import Base
from sqlalchemy import inspect

revision = "0003"
down_revision = "0002"
NAMES = [
    "states",
    "districts",
    "cities",
    "operator_divisions",
    "depots",
    "city_aliases",
    "vehicle_types",
    "vehicle_seat_layouts",
    "vehicle_seats",
    "vehicles",
    "vehicle_amenities",
    "bus_type_aliases",
    "route_variants",
    "service_calendars",
    "fare_concessions",
    "fare_concession_eligibility",
    "station_facilities",
    "data_import_batches",
    "nlp_intents",
    "nlp_utterances",
    "nlp_entity_types",
    "nlp_entity_aliases",
    "nlp_response_templates",
    "conversation_sessions",
    "conversation_messages",
    "conversation_context",
    "enquiry_execution_logs",
]


def upgrade():
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()
    for table in Base.metadata.sorted_tables:
        if table.name in NAMES and table.name not in existing:
            table.create(bind)


def downgrade():
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in NAMES:
            table.drop(op.get_bind())
