"""Test fixtures: fake Redis + real test_siem DB."""

import asyncio
import os

import pytest

# IMPORTANT: point the DB layer at test_siem before any imports touch db.py.
os.environ["PGDATABASE"] = "test_siem"


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
    """Create schema in test_siem once per session."""
    from siem_backend.db import init_schema
    asyncio.run(init_schema())
    yield


@pytest.fixture(autouse=True)
def clean_events(init_test_schema):
    """Truncate events table before each test."""
    import pg8000.native

    def _truncate():
        conn = pg8000.native.Connection(
            user=os.environ.get("PGUSER", "u0_a333"),
            host="127.0.0.1",
            port=5432,
            database="test_siem",
        )
        try:
            conn.run("TRUNCATE events RESTART IDENTITY")
        finally:
            conn.close()

    _truncate()
    yield
