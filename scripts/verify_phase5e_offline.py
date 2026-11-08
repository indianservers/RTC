"""Real dispatcher/passenger acceptance against a private DB with socket/DNS egress denied."""

import asyncio
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from offline_guard import enforce_offline

    with TemporaryDirectory(prefix="rtc-5e-offline-") as temporary:
        target = Path(temporary) / "offline.db"
        with (
            closing(sqlite3.connect(ROOT / "rtc.db")) as source,
            closing(sqlite3.connect(target)) as copy,
        ):
            source.backup(copy)
        os.environ.update(
            DATABASE_URL="sqlite:///" + target.as_posix(),
            RTC_MANAGED_RUNTIME="0",
            RTC_REQUESTS_PER_MINUTE="100000",
            RTC_LIVE_REPORT_PATH="docs/phase5e-offline-operations.json",
        )
        loop = asyncio.new_event_loop()
        enforce_offline()
        import httpx
        import verify_dispatcher_live
        from app.main import app, engine
        from fastapi.testclient import TestClient

        original = httpx.Client

        def local_client(*args, **kwargs):
            return TestClient(
                app,
                base_url="http://offline/api/v1",
                backend_options={"loop_factory": lambda: loop},
            )

        httpx.Client = local_client
        try:
            verify_dispatcher_live.run()
        finally:
            httpx.Client = original
            engine.dispose()
            loop.close()


if __name__ == "__main__":
    main()
