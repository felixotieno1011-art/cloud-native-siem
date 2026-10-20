"""Test fixtures: fake Redis + real test_siem DB."""

import asyncio
import os

import pytest

# IMPORTANT: point the DB layer at test_siem before any imports touch db.py.
os.environ.setdefault("PGDATABASE", "test_siem")


class FakeRedis:
    """Minimal async Redis stub."""

    def __init__(self) -> None:
        self.data: list[str] = []

    async def rpush(self, key: str, value: str) -> None:
        self.data.append(value)

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_redis(monkeypatch):
    stub = FakeRedis()
    import siem_backend.ws as ws_module

    async def _get():
        return stub

    monkeypatch.setattr(ws_module, "get_redis", _get)
    return stub


@pytest.fixture(scope="session", autouse=True)
def init_test_schema():
    """Create schemas in test_siem once per session."""
    from siem_backend.db import (
        init_alerts_schema,
        init_schema,
        ensure_ack_column,
    )

    async def _init():
        await init_schema()
        await init_alerts_schema()
        await ensure_ack_column()

    asyncio.run(_init())
    yield


@pytest.fixture(autouse=True)
def clean_events(init_test_schema):
    """Truncate events and alerts before each test."""
    from siem_backend.db import _conn

    def _truncate():
        conn = _conn()
        try:
            conn.run("TRUNCATE events RESTART IDENTITY")
            conn.run("TRUNCATE alerts RESTART IDENTITY")
        except Exception:
            # Table may not exist if schema init failed — let the test fail
            # with a more useful error rather than here.
            pass
        finally:
            conn.close()

    _truncate()
    yield
