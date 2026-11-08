from alembic import op
from app import catalog, links, operations, records  # noqa: F401
from app.domain import Base
from sqlalchemy import inspect

revision = "0004"
down_revision = "0003"
NAMES = [
    "trip_delay_events",
    "trip_stop_times",
    "trip_status_history",
    "vehicle_locations",
    "service_disruptions",
    "operational_alerts",
    "data_quality_issues",
    "audit_logs",
    "service_stop_times",
    "route_aliases",
    "route_distance_data",
    "extra_services",
    "fare_tables",
    "fare_rules",
    "trip_fare_overrides",
    "fare_history",
    "trip_inventory",
    "reservation_channels",
    "booking_references",
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
