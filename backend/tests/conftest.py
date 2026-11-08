"""Load all model registries before factory schema creation."""

# Existing regression fixtures explicitly exercise the legacy demo/testing write contract.
# Phase 5A publication tests disable this setting and assert strict runtime behavior.
import os

from app import catalog, links, operations, records  # noqa: F401

os.environ.setdefault("RTC_ALLOW_DEMO_DIRECT_WRITES", "1")
