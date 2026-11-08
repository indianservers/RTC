"""Local production entry point: no downloads or implicit migrations."""

import argparse
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class InstanceLock:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt

            if not self.file.read(1):
                self.file.write(b"0")
                self.file.flush()
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, *args):
        self.file.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    private = Path(os.getenv("RTC_ENV_FILE", str(ROOT / "config/runtime.private.json")))
    if private.is_file():
        for key, value in json.loads(private.read_text(encoding="utf-8-sig")).items():
            if (key.startswith("RTC_") or key == "DATABASE_URL") and isinstance(
                value, str
            ):
                os.environ.setdefault(key, value)
    os.environ.update(
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", RTC_MANAGED_RUNTIME="1"
    )
    from app.domain import database
    from app.runtime import preflight

    engine = database()
    try:
        report = preflight(engine)
    finally:
        engine.dispose()
    print(json.dumps({"component": "startup", **report}), flush=True)
    if args.check:
        return
    mode = report["mode"]
    host = os.getenv(
        "RTC_BIND_HOST", "127.0.0.1" if mode == "standalone" else "0.0.0.0"
    )
    port = int(os.getenv("RTC_PORT", "8000"))
    with InstanceLock(ROOT / "data/runtime/server.lock"):
        import uvicorn

        print(f"RTC app: http://{host}:{port}", flush=True)
        server = uvicorn.Server(
            uvicorn.Config(
                "app.main:app",
                host=host,
                port=port,
                workers=1,
                proxy_headers=False,
                access_log=False,
                timeout_graceful_shutdown=25,
                limit_concurrency=int(os.getenv("RTC_MAX_CONNECTIONS", "200")),
                ws_max_queue=16,
                ws_max_size=65536,
            )
        )
        request = ROOT / "data/runtime/shutdown.request"
        request.unlink(missing_ok=True)
        stopped = threading.Event()

        def control():
            while not stopped.wait(1):
                if request.exists():
                    server.should_exit = True
                    return

        watcher = threading.Thread(target=control, daemon=True)
        watcher.start()
        try:
            server.run()
        finally:
            stopped.set()
            watcher.join(timeout=2)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print("RTC configuration refused: " + str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - do not print database credentials from dependency errors
        print(
            f"RTC startup refused ({type(exc).__name__}). Check configuration, schema, dependencies and server lock.",
            file=sys.stderr,
        )
        sys.exit(1)
