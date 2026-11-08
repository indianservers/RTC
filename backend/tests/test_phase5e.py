"""Real database, private snapshot, recovery and local deployment checks."""

import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest
from app import main
from app.nlp.feedback import record
from app.runtime import configuration, details, event_revision
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_data_management import ROOT
from test_data_management import managed as _managed

managed = _managed
ROOT_PATH = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "rtc_storage", ROOT_PATH / "scripts/rtc_storage.py"
)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


@pytest.mark.parametrize(
    "mode,url,allowed",
    [
        ("lan", "sqlite:///wrong.db", False),
        ("standalone", "postgresql+psycopg://localhost/wrong", False),
        ("lan", "postgresql+psycopg://localhost/rtc", True),
        ("standalone", "sqlite:///rtc.db", True),
        ("unknown", "sqlite:///rtc.db", False),
    ],
)
def test_explicit_mode_never_falls_back(monkeypatch, mode, url, allowed):
    monkeypatch.setenv("RTC_DEPLOYMENT_MODE", mode)
    monkeypatch.setenv("DATABASE_URL", url)
    if allowed:
        assert configuration() == mode
    else:
        with pytest.raises(ValueError):
            configuration()


def test_real_pool_health_scoping_and_publication_invalidation(managed, monkeypatch):
    client, engine, _ = managed
    assert client.get("/health/live").json()["status"] == "LIVE"
    assert client.get("/health/dependencies").status_code == 401
    assert client.get("/health/dependencies", headers=ROOT).status_code == 200
    with engine.connect() as db:
        if engine.dialect.name == "sqlite":
            assert db.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert db.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert db.exec_driver_sql("PRAGMA busy_timeout").scalar() == 15000
        else:
            assert db.exec_driver_sql("SHOW statement_timeout").scalar() == "15s"
    with Session(engine) as db, db.begin():
        previous = event_revision(db)
        record(db, "NLP_FEEDBACK", {"text": None})
        assert event_revision(db) == previous
        record(db, "timetable", {"published": True})
        assert event_revision(db) == previous + 1
    monkeypatch.setenv("RTC_DISK_MIN_FREE_BYTES", str(10**30))
    assert details(engine)["disk_warning"] is True
    engine.dispose()
    with engine.connect() as db:
        assert db.execute(text("SELECT 1")).scalar() == 1


def test_snapshot_backup_restore_privacy_conflicts_and_interruption(
    managed, tmp_path, monkeypatch
):
    _, engine, _ = managed
    with engine.begin() as db:
        db.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        )
        db.execute(text("INSERT INTO alembic_version VALUES ('0016')"))
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setenv("RTC_SITE_ID", "DEMO-test-authority")
    # snapshot exports work from both actual dialects to a standalone SQLite DB.
    snapshot = storage.create(tmp_path / "snapshots", snapshot=True)
    manifest = storage.verify(snapshot)
    assert manifest["kind"] == "snapshot"
    with sqlite3.connect(snapshot / "database.sqlite") as db:
        for private in storage.PRIVATE:
            assert (
                db.execute('SELECT COUNT(*) FROM "' + private + '"').fetchone()[0] == 0
            )
        assert db.execute("SELECT COUNT(*) FROM bus_stations").fetchone()[0] > 0
    checksum = storage.digest(snapshot / "manifest.json")
    target = tmp_path / "restored.db"
    with pytest.raises(ValueError, match="trusted"):
        storage.restore(snapshot, target)
    result = storage.restore(snapshot, target, checksum)
    assert result["version"] == manifest["version"]
    storage.sqlite_check(target)
    with sqlite3.connect(target) as restored:
        fingerprint = storage.content_fingerprint(restored)
    applied = storage.reconcile(snapshot, target, checksum, fingerprint)
    assert applied["applied"] is True
    assert (
        storage.reconcile(snapshot, target, checksum, fingerprint)["previously_applied"]
        is True
    )
    conflict_target = tmp_path / "conflict.db"
    storage.restore(snapshot, conflict_target, checksum)
    with pytest.raises(ValueError, match="CONFLICT"):
        storage.reconcile(snapshot, conflict_target, checksum, "outdated-version")
    with sqlite3.connect(conflict_target) as interrupted_db:
        interrupted_db.execute(
            "CREATE TRIGGER fail_snapshot BEFORE INSERT ON bus_stations BEGIN SELECT RAISE(ABORT, 'simulated interruption'); END"
        )
        before = storage.content_fingerprint(interrupted_db)
    with pytest.raises(sqlite3.IntegrityError):
        storage.reconcile(snapshot, conflict_target, checksum, before)
    with sqlite3.connect(conflict_target) as interrupted_db:
        assert storage.content_fingerprint(interrupted_db) == before
    with pytest.raises(ValueError, match="CONFLICT"):
        storage.restore(snapshot, target, checksum)
    with pytest.raises(ValueError, match="DEMO"):
        storage.create(tmp_path / "official", snapshot=True, environment="production")
    original_link = os.link

    def interrupted(*args, **kwargs):
        raise OSError("TEST interrupted before publication")

    monkeypatch.setattr(os, "link", interrupted)
    interrupted_target = tmp_path / "interrupted.db"
    with pytest.raises(OSError):
        storage.restore(snapshot, interrupted_target, checksum)
    assert not interrupted_target.exists()
    monkeypatch.setattr(os, "link", original_link)
    metadata = json.loads((snapshot / "manifest.json").read_text())
    metadata["files"]["database.sqlite"] = "invalid"
    (snapshot / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="checksum"):
        storage.verify(snapshot)


def test_failed_backup_is_not_published(tmp_path, monkeypatch):
    def failure(*args, **kwargs):
        raise ValueError("TEST database verification failed")

    monkeypatch.setattr(storage, "sqlite_check", failure)
    with pytest.raises(ValueError):
        storage.create(tmp_path)
    assert not list(tmp_path.iterdir())
