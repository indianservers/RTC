"""Verified local backup/restore and private-data-free standalone snapshots.

Never restores over an existing database. Operators reconcile conflicts explicitly.
PostgreSQL tools use libpq environment variables, never password-bearing command lines.
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
PRIVATE = {
    "admin_roles",
    "admin_users",
    "admin_user_roles",
    "conversation_sessions",
    "conversation_messages",
    "conversation_context",
    "enquiry_execution_logs",
    "booking_references",
    "nlp_utterances",
    "nlp_entity_annotations",
    "audit_logs",
    "data_import_batches",
    "data_quality_issues",
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sqlite_check(path):
    with closing(
        sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    ) as db:
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("SQLite integrity/foreign-key verification failed")


def pg_env(url):
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    env = dict(os.environ)
    env.update(
        PGHOST=parsed.host or "localhost",
        PGPORT=str(parsed.port or 5432),
        PGDATABASE=parsed.database or "",
        PGUSER=parsed.username or "",
        PGCONNECT_TIMEOUT="5",
    )
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    return env


def pg_tool(name):
    folder = os.getenv("RTC_PG_BIN")
    return (
        str(Path(folder) / (name + (".exe" if os.name == "nt" else "")))
        if folder
        else name
    )


def create(directory, snapshot=False, environment="demo", valid_hours=24):
    from app.domain import Base
    from app.main import engine
    from sqlalchemy import create_engine, select, text

    destination = Path(directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stage = destination / (".pending-" + uuid4().hex)
    stage.mkdir(mode=0o700)
    try:
        kind = "snapshot" if snapshot else "backup"
        if snapshot and environment == "production" and not os.getenv("RTC_SITE_ID"):
            raise ValueError(
                "Production snapshots require a configured authoritative RTC_SITE_ID"
            )
        now = datetime.now(UTC)
        manifest = {
            "format": 1,
            "kind": kind,
            "version": uuid4().hex,
            "created_at": now.isoformat(),
            "valid_until": (now + timedelta(hours=valid_hours)).isoformat()
            if snapshot
            else None,
            "source": os.getenv("RTC_SITE_ID", "local-unidentified"),
            "environment": environment,
            "schema": None,
            "provenance": [],
            "files": {},
        }
        with engine.connect() as db:
            manifest["schema"] = db.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        if snapshot:
            # New isolated DB; private sessions, credentials, feedback and raw import payloads never leave source.
            target = create_engine(
                "sqlite:///" + (stage / "database.sqlite").as_posix()
            )
            Base.metadata.create_all(target)
            source = engine.connect().execution_options(
                isolation_level="SERIALIZABLE"
                if engine.dialect.name == "sqlite"
                else "REPEATABLE READ"
            )
            try:
                with source.begin(), target.begin() as out:
                    for table in Base.metadata.sorted_tables:
                        if table.name in PRIVATE:
                            continue
                        query = select(table)
                        if "verified" in table.c:
                            query = query.where(table.c.verified.is_(True))
                        rows = [dict(r) for r in source.execute(query).mappings()]
                        if (
                            environment == "production"
                            and "dataset_source" in table.c
                            and any(r["dataset_source"] == "DEMO" for r in rows)
                        ):
                            raise ValueError(
                                "Production snapshot refused: DEMO rows must be separated at the source"
                            )
                        if rows:
                            out.execute(table.insert(), rows)
                    from app.catalog import ImportBatch

                    for row in source.execute(select(ImportBatch.__table__)).mappings():
                        manifest["provenance"].append(
                            {
                                k: row[k]
                                for k in (
                                    "id",
                                    "dataset_source",
                                    "source_id",
                                    "source_checksum",
                                    "workflow_state",
                                    "revision",
                                )
                                if k in row
                            }
                        )
                    out.execute(
                        text(
                            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                        )
                    )
                    out.execute(
                        text("INSERT INTO alembic_version VALUES (:v)"),
                        {"v": manifest["schema"]},
                    )
            finally:
                source.close()
                target.dispose()
            sqlite_check(stage / "database.sqlite")
        elif engine.dialect.name == "sqlite":
            with (
                closing(sqlite3.connect(engine.url.database)) as source,
                closing(sqlite3.connect(stage / "database.sqlite")) as out,
            ):
                source.backup(out)
            sqlite_check(stage / "database.sqlite")
        else:
            subprocess.run(
                [
                    pg_tool("pg_dump"),
                    "--format=custom",
                    "--file",
                    str(stage / "database.dump"),
                ],
                env=pg_env(engine.url.render_as_string(hide_password=False)),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [pg_tool("pg_restore"), "--list", str(stage / "database.dump")],
                check=True,
                capture_output=True,
            )
        if not snapshot:
            registry = ROOT / "config/model_registry.yaml"
            if registry.exists():
                shutil.copyfile(registry, stage / "model_registry.json")
            config = {
                k: os.environ[k]
                for k in (
                    "RTC_SITE_ID",
                    "RTC_DEPLOYMENT_MODE",
                    "RTC_BIND_HOST",
                    "RTC_PORT",
                    "RTC_TRUSTED_HOSTS",
                    "RTC_FEEDBACK_RETENTION_DAYS",
                )
                if k in os.environ
            }
            (stage / "runtime-public.json").write_text(
                json.dumps(config, indent=2), encoding="utf-8"
            )
        manifest["files"] = {p.name: digest(p) for p in stage.iterdir() if p.is_file()}
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        final = destination / (
            kind + "-" + now.strftime("%Y%m%dT%H%M%S") + "-" + manifest["version"][:8]
        )
        os.replace(stage, final)
        return final
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    finally:
        engine.dispose()


def verify(directory, expected_manifest=None):
    folder = Path(directory).resolve()
    path = folder / "manifest.json"
    if expected_manifest and digest(path) != expected_manifest:
        raise ValueError("Manifest differs from trusted transfer checksum")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("kind") not in {
        "backup",
        "snapshot",
    }:
        raise ValueError("Unsupported package")
    for name, checksum in manifest["files"].items():
        if (
            Path(name).name != name
            or not (folder / name).resolve().is_relative_to(folder)
            or digest(folder / name) != checksum
        ):
            raise ValueError("Package checksum/path verification failed")
    if manifest["kind"] == "snapshot" and datetime.fromisoformat(
        manifest["valid_until"]
    ) <= datetime.now(UTC):
        raise ValueError("Snapshot expired; obtain a new authoritative snapshot")
    if "database.sqlite" in manifest["files"]:
        sqlite_check(folder / "database.sqlite")
        with closing(sqlite3.connect(folder / "database.sqlite")) as db:
            if (
                db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                != manifest["schema"]
            ):
                raise ValueError("Schema manifest differs from database payload")
    elif "database.dump" in manifest["files"]:
        subprocess.run(
            [pg_tool("pg_restore"), "--list", str(folder / "database.dump")],
            check=True,
            capture_output=True,
        )
    else:
        raise ValueError("Database payload absent")
    return manifest


def restore(directory, target, expected_manifest=None):
    folder = Path(directory).resolve()
    manifest = verify(folder, expected_manifest)
    if manifest["kind"] == "snapshot" and not expected_manifest:
        raise ValueError(
            "Snapshot import requires a separately trusted manifest SHA256"
        )
    destination = Path(target).resolve()
    if destination.exists():
        raise ValueError(
            "CONFLICT: target exists; restore to a new isolated path and reconcile explicitly"
        )
    if "database.sqlite" not in manifest["files"]:
        raise ValueError("Use restore-postgres with a new empty PostgreSQL database")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".restore-") as temp:
        staged = Path(temp) / "database.sqlite"
        shutil.copyfile(folder / "database.sqlite", staged)
        sqlite_check(staged)
        # Exclusive create prevents a concurrent restore from overwriting another target.
        os.link(staged, destination)
    return {"restored": str(destination), "version": manifest["version"]}


def content_fingerprint(db):
    """Logical database fingerprint includes WAL-visible rows and private session state."""
    h = hashlib.sha256()
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for (name,) in tables:
        safe = name.replace('"', '""')
        rows = db.execute('SELECT * FROM "' + safe + '"').fetchall()
        h.update(
            json.dumps(
                [name, sorted(rows, key=repr)], default=str, sort_keys=True
            ).encode()
        )
    return h.hexdigest()


def reconcile(directory, target, manifest_sha, expected_current):
    """Explicit offline transactional replacement of central masters, preserving private data.

    Local operational divergence fails closed instead of choosing a last writer.
    CLI holds the application instance lock; callers must stop their server first.
    """
    manifest = verify(directory, manifest_sha)
    if not target or not Path(target).is_file():
        raise ValueError("Reconciliation target must be an existing stopped kiosk database")
    if manifest["kind"] != "snapshot" or not manifest_sha or not expected_current:
        raise ValueError(
            "Reconciliation requires a trusted snapshot and current database fingerprint"
        )
    import app.main  # noqa: F401 - register all existing tables
    from app.domain import Base

    with (
        closing(sqlite3.connect(target)) as db,
        closing(sqlite3.connect(Path(directory) / "database.sqlite")) as incoming,
    ):
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            key = "snapshot:" + manifest["version"]
            if db.execute(
                "SELECT id FROM audit_logs WHERE idempotency_key=?", (key,)
            ).fetchone():
                db.rollback()
                return {
                    "previously_applied": True,
                    "version": manifest["version"],
                    "reapplied": False,
                }
            previous = db.execute(
                "SELECT new_values FROM audit_logs WHERE entity_type='snapshot_import' ORDER BY recorded_at DESC LIMIT 1"
            ).fetchone()
            if previous:
                prior = json.loads(previous[0])
                if prior.get("source") != manifest["source"] or (
                    prior.get("created_at")
                    and prior["created_at"] >= manifest["created_at"]
                ):
                    raise ValueError(
                        "CONFLICT: older snapshot or changed authoritative source"
                    )
            if content_fingerprint(db) != expected_current:
                raise ValueError(
                    "CONFLICT: local database changed; administrator review required"
                )
            if (
                db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                != manifest["schema"]
            ):
                raise ValueError("CONFLICT: schema differs")
            # Never replace a locally observed/approved operational projection with another version silently.
            local_trips = {
                r[0]: r[1:]
                for r in db.execute("SELECT id,status,operational_state FROM trips")
            }
            central_trips = {
                r[0]: r[1:]
                for r in incoming.execute(
                    "SELECT id,status,operational_state FROM trips"
                )
            }
            for key, values in local_trips.items():
                if (
                    values[0] != "scheduled" or values[1] not in (None, "null", "{}")
                ) and central_trips.get(key) != values:
                    raise ValueError(
                        "CONFLICT: local operational evidence differs; dispatcher/admin review required"
                    )
            tables = [t for t in Base.metadata.sorted_tables if t.name not in PRIVATE]
            db.execute("PRAGMA defer_foreign_keys=ON")
            for table in reversed(tables):
                db.execute('DELETE FROM "' + table.name + '"')
            for table in tables:
                cursor = incoming.execute('SELECT * FROM "' + table.name + '"')
                names = ",".join('"' + c[0] + '"' for c in cursor.description)
                placeholders = ",".join("?" for _ in cursor.description)
                db.executemany(
                    'INSERT INTO "'
                    + table.name
                    + '" ('
                    + names
                    + ") VALUES ("
                    + placeholders
                    + ")",
                    cursor.fetchall(),
                )
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError(
                    "CONFLICT: snapshot would orphan local/private references"
                )
            db.execute(
                "INSERT INTO audit_logs (id,dataset_source,active,actor,entity_type,entity_id,operation,recorded_at,idempotency_key,version,new_values) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    "LOCAL",
                    1,
                    "offline-administrator",
                    "snapshot_import",
                    manifest["version"],
                    "SNAPSHOT_IMPORT",
                    datetime.now(UTC).isoformat(),
                    key,
                    1,
                    json.dumps(
                        {
                            "source": manifest["source"],
                            "version": manifest["version"],
                            "manifest_sha256": manifest_sha,
                            "created_at": manifest["created_at"],
                        }
                    ),
                ),
            )
            db.commit()
            return {
                "applied": True,
                "version": manifest["version"],
                "fingerprint": content_fingerprint(db),
                "sessions": "PRESERVED_LOCAL",
            }
        except BaseException:
            db.rollback()
            raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "action",
        choices=[
            "backup",
            "snapshot",
            "verify",
            "restore",
            "restore-postgres",
            "prune",
            "apply-snapshot",
            "fingerprint",
        ],
    )
    p.add_argument("--directory", required=True)
    p.add_argument("--target")
    p.add_argument("--manifest-sha256")
    p.add_argument("--expected-current")
    p.add_argument("--environment", choices=["demo", "production"], default="demo")
    p.add_argument("--valid-hours", type=int, default=24)
    p.add_argument("--retain", type=int, default=14)
    a = p.parse_args()
    if a.action in {"backup", "snapshot"}:
        if not 1 <= a.valid_hours <= 168:
            p.error("valid-hours must be 1..168")
        print(
            json.dumps(
                {
                    "directory": str(
                        create(
                            a.directory,
                            a.action == "snapshot",
                            a.environment,
                            a.valid_hours,
                        )
                    )
                }
            )
        )
    elif a.action == "verify":
        print(json.dumps(verify(a.directory, a.manifest_sha256)))
    elif a.action == "restore":
        print(json.dumps(restore(a.directory, a.target, a.manifest_sha256)))
    elif a.action == "fingerprint":
        with closing(sqlite3.connect(a.target)) as db:
            print(json.dumps({"fingerprint": content_fingerprint(db)}))
    elif a.action == "apply-snapshot":
        from serve_rtc import InstanceLock

        with InstanceLock(ROOT / "data/runtime/server.lock"):
            print(
                json.dumps(
                    reconcile(
                        a.directory, a.target, a.manifest_sha256, a.expected_current
                    )
                )
            )
    elif a.action == "restore-postgres":
        from sqlalchemy import create_engine, inspect

        verify(a.directory, a.manifest_sha256)
        target = os.environ["RTC_RESTORE_DATABASE_URL"]
        engine = create_engine(target)
        try:
            if inspect(engine).get_table_names():
                raise ValueError("Restore requires a NEW EMPTY PostgreSQL database")
            subprocess.run(
                [
                    pg_tool("pg_restore"),
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--dbname",
                    pg_env(target)["PGDATABASE"],
                    str(Path(a.directory) / "database.dump"),
                ],
                env=pg_env(target),
                check=True,
                capture_output=True,
            )
            print(json.dumps({"restored": True, "isolated": True}))
        finally:
            engine.dispose()
    else:
        if a.retain < 1:
            p.error("retain must be positive")
        packages = sorted(Path(a.directory).glob("backup-*"), reverse=True)
        for old in packages[a.retain :]:
            verify(old)
            shutil.rmtree(old)
        print(json.dumps({"removed": max(0, len(packages) - a.retain)}))


if __name__ == "__main__":
    main()
