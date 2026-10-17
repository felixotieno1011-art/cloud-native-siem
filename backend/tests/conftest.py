"""Fake Redis fixture for deterministic ingest tests."""

import pytest


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
