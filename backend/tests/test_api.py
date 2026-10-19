"""Tests for GET /api/events."""

from starlette.testclient import TestClient

from siem_backend.__main__ import create_app
from siem_backend.db import insert_event


def _client():
    return TestClient(create_app())


def test_empty_events():
    client = _client()
    r = client.get("/api/events")
    assert r.status_code == 200
    data = r.json()
    assert data["events"] == []
    assert data["count"] == 0


def test_returns_inserted_event():
    import asyncio
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        insert_event("agent-x", "metrics", {"cpu": 1})
    )
    client = _client()
    r = client.get("/api/events")
    data = r.json()
    assert data["count"] == 1
    assert data["events"][0]["agent_id"] == "agent-x"


def test_limit_invalid_returns_400():
    client = _client()
    r = client.get("/api/events?limit=abc")
    assert r.status_code == 400
    assert "error" in r.json()


def test_limit_clamped():
    client = _client()
    r = client.get("/api/events?limit=99999")
    assert r.status_code == 200
    assert r.json()["limit"] == 500


def test_agent_filter():
    client = _client()
    r = client.get("/api/events?agent_id=nobody")
    data = r.json()
    assert data["count"] == 0
