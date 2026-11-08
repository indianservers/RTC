"""Small single-process local UI request limits; not a distributed gateway."""

import os
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def install_ui_security(app: FastAPI) -> None:
    capacity = max(1, int(os.getenv("RTC_REQUESTS_PER_MINUTE", "300")))
    windows: dict[str, deque] = {}
    lock = Lock()

    @app.middleware("http")
    async def limits(request, call_next):
        if request.url.path.startswith("/api/") and request.method in {
            "POST",
            "PUT",
            "DELETE",
        }:
            size = request.headers.get("content-length", "0")
            if size.isdigit() and int(size) > (
                14500000
                if request.url.path.startswith("/api/v1/admin/imports/files/")
                else 2200000
            ):
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "BODY_TOO_LARGE",
                            "message": "Request exceeds the local import limit.",
                        }
                    },
                )
            key = (request.client.host if request.client else "local") + (
                "admin" if "/admin/" in request.url.path else "passenger"
            )
            with lock:
                now = monotonic()
                if key not in windows and len(windows) >= 1024:
                    del windows[next(iter(windows))]
                window = windows.setdefault(key, deque())
                while window and window[0] <= now - 60:
                    window.popleft()
                if len(window) >= capacity:
                    return JSONResponse(
                        status_code=429,
                        headers={"Retry-After": "60"},
                        content={
                            "error": {
                                "code": "RATE_LIMIT",
                                "message": "Too many requests. Wait a minute and retry.",
                            }
                        },
                    )
                window.append(now)
        response = await call_next(request)
        if request.url.path.startswith(("/api/v1/conversation/", "/api/v1/admin/nlp/")):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response
