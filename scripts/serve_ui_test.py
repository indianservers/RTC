"""Isolated actual DB/API server for production browser tests; never touches rtc.db."""

import os
import socket
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def run(port=8020, strict=False):
    with tempfile.TemporaryDirectory(prefix="rtc-ui-") as tmp:
        path = Path(tmp) / "ui.db"
        os.environ["DATABASE_URL"] = "sqlite:///" + path.as_posix()
        os.environ["RTC_ALLOW_DEMO_DIRECT_WRITES"] = "0" if strict else "1"
        os.environ["RTC_REQUESTS_PER_MINUTE"] = "5000"
        os.environ["RTC_ADMIN_TOKEN"] = "ui-test-only-token-never-for-deployment"
        os.environ["RTC_REQUEST_LOG"] = str(
            Path(__file__).resolve().parents[1]
            / f"data/runtime/ui-{port}-requests.jsonl"
        )
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from app import catalog, links, operations, records, schema1a  # noqa: F401
        from app.demo import enrich
        from app.domain import (
            Base,
            Category,
            Fare,
            Operator,
            Route,
            Service,
            Station,
            Stop,
            database,
        )
        from app.nlp_seed import seed_nlp
        from app.seed import seed
        from app.taxonomy_seed import seed_taxonomy
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        engine = database()
        Base.metadata.create_all(engine)
        seed(engine)
        enrich(engine)
        seed_nlp(engine)
        seed_taxonomy(engine)
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        with Session(engine) as s, s.begin():
            op = s.scalar(select(Operator).where(Operator.code == "DEMO"))
            cat = s.scalar(select(Category).where(Category.operator_id == op.id))
            origin = s.scalar(select(Station).where(Station.code == "DEMO0"))
            for code, destination_code, amount in (
                ("UI-DEMO-NELLORE", "DEMO4", 125),
                ("UI-DEMO-UNKNOWN", "DEMO2", None),
                ("UI-DEMO-NELLORE-CHEAP", "DEMO4", 95),
                ("UI-DEMO-NELLORE-UNKNOWN", "DEMO4", None),
            ):
                destination = s.scalar(
                    select(Station).where(Station.code == destination_code)
                )
                s.add(Route(id=code, code=code, operator_id=op.id))
                s.flush()
                departure = now + timedelta(
                    hours=2
                    if code.endswith("CHEAP") or code == "UI-DEMO-NELLORE-UNKNOWN"
                    else 1
                )
                s.add(
                    Service(
                        id=code,
                        operator_id=op.id,
                        category_id=cat.id,
                        route_id=code,
                        number=code,
                        departure_minutes=departure.hour * 60 + departure.minute,
                        valid_from=now.date() - timedelta(days=5),
                        valid_to=now.date() + timedelta(days=90),
                        dataset_source="DEMO",
                    )
                )
                s.add_all(
                    [
                        Stop(
                            route_id=code,
                            station_id=origin.id,
                            sequence=0,
                            offset_minutes=0,
                            distance_km=0,
                        ),
                        Stop(
                            route_id=code,
                            station_id=destination.id,
                            sequence=1,
                            offset_minutes=180,
                            distance_km=150,
                        ),
                    ]
                )
                s.flush()
                if amount is not None:
                    s.add(
                        Fare(
                            service_id=code,
                            origin_id=origin.id,
                            destination_id=destination.id,
                            amount=amount,
                            valid_from=now.date() - timedelta(days=5),
                            valid_to=now.date() + timedelta(days=90),
                        )
                    )
        # Explicitly fictional vehicle facts make category-filter acceptance meaningful.
        from app.catalog import Layout, Vehicle, VehicleType
        from app.links import ServiceVehicle

        with Session(engine) as s, s.begin():
            op = s.scalar(select(Operator).where(Operator.code == "DEMO"))
            s.add(
                VehicleType(
                    id="ui-ac-type",
                    name="DEMO AC seater",
                    ac=True,
                    sleeper=False,
                    wheelchair=True,
                )
            )
            s.add(
                Layout(
                    id="ui-layout",
                    name="DEMO layout",
                    seating_capacity=40,
                    berth_capacity=0,
                )
            )
            s.flush()
            s.add(
                Vehicle(
                    id="ui-ac-vehicle",
                    operator_id=op.id,
                    type_id="ui-ac-type",
                    layout_id="ui-layout",
                    registration="DEMO-UI-AC",
                )
            )
            s.flush()
            s.add(
                ServiceVehicle(
                    service_id="UI-DEMO-NELLORE-CHEAP", vehicle_id="ui-ac-vehicle"
                )
            )
            s.add_all(
                [
                    Station(id="ui-central-a", code="UI-CENTRAL-A", name="Central"),
                    Station(id="ui-central-b", code="UI-CENTRAL-B", name="Central"),
                ]
            )
        from app.operations import DataSource, Trip
        from app.records import DelayEvent

        with Session(engine) as s, s.begin():
            origin = s.scalar(select(Station).where(Station.code == "DEMO0"))
            s.add(
                DataSource(
                    id="ui-expiry-source",
                    code="UI-EXPIRY",
                    name="DEMO verified-update fixture",
                )
            )
            s.add(
                Trip(
                    id="ui-expiry-trip",
                    service_id="UI-DEMO-NELLORE",
                    service_date=(now + timedelta(hours=1)).date(),
                    status="scheduled",
                )
            )
            s.flush()
            s.add(
                DelayEvent(
                    id="ui-expiry-delay",
                    trip_id="ui-expiry-trip",
                    station_id=origin.id,
                    source_id="ui-expiry-source",
                    verified=True,
                    delay_minutes=12,
                    effective_at=now - timedelta(minutes=1),
                    expires_at=now + timedelta(days=1),
                )
            )
        with Session(engine) as s, s.begin():
            s.add_all(
                [
                    Station(
                        id=f"ui-quality-{i}",
                        code=f"UI-QUALITY-{i}",
                        name=f"Quality station {i}",
                    )
                    for i in range(7)
                ]
            )
            s.add(Route(id="UI-QUALITY-ROUTE", code="UI-QUALITY-ROUTE"))
        engine.dispose()
        original = socket.socket.connect

        def deny_external(sock, address):
            if isinstance(address, tuple) and address[0] in (
                "127.0.0.1",
                "::1",
                "localhost",
            ):
                return original(sock, address)
            raise RuntimeError("External networking forbidden in UI backend test")

        socket.socket.connect = deny_external
        socket.socket.connect_ex = deny_external
        import uvicorn
        from app.main import app

        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    run(args.port, args.strict)
