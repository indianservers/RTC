"""Bounded local request diagnostics. Never record bodies, queries or credentials."""

import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def install_diagnostics(app: FastAPI) -> None:
    logger = logging.getLogger("rtc.local.requests")
    if not logger.handlers:
        path = Path(os.getenv("RTC_REQUEST_LOG", "data/runtime/requests.jsonl"))
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    @app.middleware("http")
    async def correlate(request, call_next):
        correlation = uuid4().hex
        started = perf_counter()
        exception_type = None
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 - boundary logs category without exposing exception text
            exception_type = type(exc).__name__
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Local request failed. Retry or check the local diagnostic log.",
                        "correlation_id": correlation,
                    }
                },
            )
        elapsed = round((perf_counter() - started) * 1000, 3)
        response.headers["X-Request-ID"] = correlation
        response.headers["Server-Timing"] = f"app;dur={elapsed}"
        if request.url.path.startswith("/api/"):
            route = request.scope.get("route")
            # An unmatched raw URL may contain arbitrary passenger input.
            endpoint = getattr(route, "path", "UNMATCHED_API")
            status = response.status_code
            logger.info(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "correlation_id": correlation,
                        "endpoint": endpoint,
                        "method": request.method,
                        "status": status,
                        "duration_ms": elapsed,
                        "severity": "ERROR"
                        if status >= 500
                        else "WARNING"
                        if status >= 400
                        else "INFO",
                        "category": exception_type
                        or (
                            "SERVER_ERROR"
                            if status >= 500
                            else "REQUEST_REJECTED"
                            if status >= 400
                            else "SUCCESS"
                        ),
                    }
                )
            )
        return response
