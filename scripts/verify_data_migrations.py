"""Preserve legacy records while applying incremental data-management migrations."""

import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema


def verify(url):
    engine = None
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = (
        url.render_as_string(hide_password=False)
        if hasattr(url, "render_as_string")
        else str(url)
    )
    cfg = Config(str(ROOT / "alembic.ini"))
    try:
        command.upgrade(cfg, "0010")
        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO transport_operators (id,code,name,dataset_source,active) VALUES ('legacy-op','LEGACY','Legacy preserved operator','DEMO',true)"
                )
            )
            # Historical migrations use live metadata during a fresh bootstrap; supply Python-only defaults when already present.
            columns = {
                c["name"]
                for c in inspect(connection).get_columns("data_import_batches")
            }
            extra = (
                ",workflow_state,revision,validation_error_count"
                if "workflow_state" in columns
                else ""
            )
            values = ",'PUBLISHED',1,0" if extra else ""
            connection.execute(
                text(
                    "INSERT INTO data_import_batches (id,resource,digest,row_count,dataset_source,active"
                    + extra
                    + ") VALUES ('legacy-batch','stations','legacy-checksum',0,'DEMO',true"
                    + values
                    + ")"
                )
            )
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            operator = (
                connection.execute(
                    text(
                        "SELECT id,code,name,dataset_source,active FROM transport_operators WHERE id='legacy-op'"
                    )
                )
                .mappings()
                .one()
            )
            batch = (
                connection.execute(
                    text(
                        "SELECT id,digest,workflow_state,validation_error_count,revision FROM data_import_batches WHERE id='legacy-batch'"
                    )
                )
                .mappings()
                .one()
            )
            assert operator["code"] == "LEGACY" and operator["dataset_source"] == "DEMO"
            assert batch["workflow_state"] == "PUBLISHED" and batch["revision"] == 1
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0014"
            )
            if engine.dialect.name == "sqlite":
                assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        checks = inspect(engine).get_check_constraints("fare_rules")
        assert any(c["name"] == "ck_fare_rule_effective_components" for c in checks)
        report = {
            "dialect": engine.dialect.name,
            "head": "0014",
            "legacy_operator_preserved": dict(operator),
            "legacy_batch_preserved": dict(batch),
            "fare_rule_check_present": True,
        }
        engine.dispose()
        return report
    finally:
        if engine is not None:
            engine.dispose()
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old


def run():
    reports = []
    with tempfile.TemporaryDirectory(prefix="rtc-migration-") as tmp:
        reports.append(verify("sqlite:///" + (Path(tmp) / "migration.db").as_posix()))
    postgres = os.getenv("RTC_TEST_POSTGRES_URL")
    if postgres:
        url = make_url(postgres)
        if url.database != "rtc_phase5a_tests":
            raise RuntimeError("Only the dedicated test database is supported")
        schema = "migration_" + uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            reports.append(
                verify(url.update_query_dict({"options": "-csearch_path=" + schema}))
            )
        finally:
            with admin.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            admin.dispose()
    (ROOT / "docs/phase5a-migration-verification.json").write_text(
        json.dumps(reports, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(reports, indent=2, default=str))


if __name__ == "__main__":
    run()
