"""Local deployment preflight and bounded, evidence-based process health."""

import os
import shutil
import threading
from collections import deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
SAMPLES: deque = deque(maxlen=1000)
LOCK = threading.Lock()
STATE = {"cleanup": "NOT_STARTED", "last_cleanup": None, "model": "NOT_CHECKED"}


def observe(duration, status):
    with LOCK:
        SAMPLES.append((duration, status))


def configuration(strict=False):
    mode = os.getenv("RTC_DEPLOYMENT_MODE", "standalone")
    url = os.getenv("DATABASE_URL", "sqlite:///rtc.db")
    if mode not in {"standalone", "lan"}:
        raise ValueError("RTC_DEPLOYMENT_MODE must be standalone or lan")
    if mode == "lan" and not url.startswith("postgresql"):
        raise ValueError("LAN mode requires PostgreSQL; no SQLite failover is allowed")
    if mode == "standalone" and not url.startswith("sqlite"):
        raise ValueError("Standalone mode requires SQLite")
    if strict and len(os.getenv("RTC_ADMIN_TOKEN", "")) < 32:
        raise ValueError("Set a private RTC_ADMIN_TOKEN with at least 32 characters")
    if strict and mode == "standalone":
        from sqlalchemy.engine import make_url

        path = make_url(url).database
        if not path or not Path(path).is_file():
            raise ValueError(
                "SQLite database missing; initialize explicitly before startup"
            )
    if strict and mode == "lan" and not os.getenv("RTC_TRUSTED_HOSTS"):
        raise ValueError(
            "LAN mode requires RTC_TRUSTED_HOSTS (comma-separated local hosts)"
        )
    return mode


def preflight(engine, strict=True):
    from .nlp.english_model import EnglishIntentModel

    mode = configuration(strict)
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise ValueError("Production frontend missing; build it during installation")
    with engine.connect() as db:
        db.execute(text("SELECT 1"))
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "backend/alembic"))
        if current != ScriptDirectory.from_config(cfg).get_current_head():
            raise ValueError(
                "Schema revision mismatch; run the controlled migration procedure"
            )
    try:
        model = EnglishIntentModel(ROOT)
        prediction = model.predict("Next bus?")
        STATE["model"] = (
            "READY"
            if model.model is not None
            and prediction["status"]
            in {"KNOWN", "CLARIFICATION_REQUIRED", "OUT_OF_SCOPE"}
            else prediction["status"]
        )
        STATE["model_version"] = model.version
    except Exception as exc:  # noqa: BLE001 - optional local model must not restart-loop the server
        STATE["model"] = "LOAD_FAILED:" + type(exc).__name__
    return {"mode": mode, "model": STATE["model"], "schema": current}


def details(engine):
    from .catalog import Context
    from .records import Audit

    result = {
        "database": "UNAVAILABLE",
        "active_sessions": None,
        "last_publication": None,
    }
    try:
        with Session(engine) as db:
            db.execute(text("SELECT 1"))
            result["database"] = "READY"
            result["active_sessions"] = db.scalar(
                select(func.count())
                .select_from(Context)
                .where(
                    Context.values["expires_at"].as_string()
                    > datetime.now(UTC).isoformat()
                )
            )
            stamp = db.scalar(
                select(func.max(Audit.recorded_at)).where(
                    Audit.operation.in_(["PUBLISH", "publish"])
                )
            )
            result["last_publication"] = stamp.isoformat() if stamp else None
            publication = db.execute(
                select(Audit.id, Audit.dataset_source)
                .where(Audit.operation.in_(["PUBLISH", "publish"]))
                .order_by(Audit.recorded_at.desc())
                .limit(1)
            ).first()
            STATE["dataset_version"] = publication[0] if publication else None
            STATE["data_source"] = publication[1] if publication else None
            result["dataset_version"] = STATE["dataset_version"]
            result["event_revision"] = event_revision(db)
    except Exception as exc:  # noqa: BLE001 - no credentials in health responses
        result["database_error"] = type(exc).__name__
    disk = shutil.disk_usage(ROOT)
    with LOCK:
        samples = list(SAMPLES)
    result.update(
        mode=os.getenv("RTC_DEPLOYMENT_MODE", "standalone"),
        model=STATE["model"],
        background=dict(STATE),
        disk_free_bytes=disk.free,
        disk_warning=disk.free
        < int(os.getenv("RTC_DISK_MIN_FREE_BYTES", "1073741824")),
        sampled_requests=len(samples),
        error_rate=sum(s >= 500 for _, s in samples) / len(samples)
        if samples
        else None,
        mean_latency_ms=sum(t for t, _ in samples) / len(samples) if samples else None,
        event_delivery="INVALIDATION_WITH_RECONNECT_REFETCH; not per-client acknowledgements",
    )
    try:
        import psutil

        result["process_rss_bytes"] = psutil.Process().memory_info().rss
    except ImportError:
        result["process_rss_bytes"] = None
    return result


def event_revision(session):
    from .records import Audit

    return (
        session.scalar(
            select(func.count())
            .select_from(Audit)
            .where(~Audit.entity_type.like("NLP_%"))
        )
        or 0
    )


def health_router(get_engine, admin):
    router = APIRouter()

    @router.get("/health/live")
    def live():
        return {"status": "LIVE"}

    @router.get("/health/ready")
    def ready():
        try:
            with get_engine().connect() as db:
                db.execute(text("SELECT 1"))
            return {
                "status": "READY" if STATE["model"] == "READY" else "DEGRADED",
                "deterministic_enquiries": True,
            }
        except Exception:  # noqa: BLE001
            return JSONResponse(
                {"status": "NOT_READY", "code": "DATABASE_UNAVAILABLE"}, status_code=503
            )

    @router.get("/health/dependencies")
    def dependencies(_=Depends(admin)):  # noqa: B008
        return {"data": details(get_engine())}

    return router


def install_maintenance(app, get_engine):
    stop = threading.Event()

    def work():
        from .catalog import Context
        from .nlp.pipeline import ConversationManager

        cursor = ""
        while not stop.is_set():
            started = monotonic()
            try:
                with Session(get_engine()) as db, db.begin():
                    rows = list(
                        db.scalars(
                            select(Context)
                            .where(Context.id > cursor)
                            .order_by(Context.id)
                            .limit(100)
                        )
                    )
                    for row in rows:
                        expiry = row.values.get("expires_at")
                        if expiry and datetime.fromisoformat(expiry) <= datetime.now(
                            UTC
                        ):
                            ConversationManager(db).expire(row)
                    cursor = rows[-1].id if len(rows) == 100 else ""
                STATE.update(
                    cleanup="READY",
                    last_cleanup=datetime.now(UTC).isoformat(),
                    cleanup_ms=(monotonic() - started) * 1000,
                )
            except Exception as exc:  # noqa: BLE001
                STATE["cleanup"] = "FAILED:" + type(exc).__name__
            stop.wait(max(5, int(os.getenv("RTC_CLEANUP_SECONDS", "60"))))

    thread = threading.Thread(target=work, name="rtc-session-cleanup", daemon=True)

    def start():
        if os.getenv("RTC_MANAGED_RUNTIME") == "1":
            try:
                details(get_engine())
            except OSError:
                STATE["cleanup"] = "DISK_CHECK_UNAVAILABLE"
            thread.start()

    def shutdown():
        if os.getenv("RTC_MANAGED_RUNTIME") != "1":
            return
        stop.set()
        if thread.is_alive():
            thread.join(timeout=20)
        get_engine().dispose()

    previous = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with previous(application):
            start()
            try:
                yield
            finally:
                shutdown()

    app.router.lifespan_context = lifespan
