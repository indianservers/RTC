#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
rtc_python="${RTC_PYTHON:-.venv/bin/python}"
if [[ ! -x "$rtc_python" ]]; then rtc_python="python3"; fi
exec "$rtc_python" scripts/serve_rtc.py "$@"
