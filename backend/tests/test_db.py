"""Tests for the PostgreSQL persistence layer (uses test_siem DB)."""

import pytest

from siem_backend.db import insert_event, recent_events


@pytest.mark.asyncio
async def test_insert_returns_id():
    rid = await insert_event("agent-a", "metrics", {"cpu": 5})
    assert isinstance(rid, int)
    assert rid >= 1


@pytest.mark.asyncio
async def test_insert_stores_payload():
    await insert_event("agent-a", "metrics", {"cpu": 42, "mem": 80})
    rows = await recent_events(limit=10)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "metrics"
    assert rows[0]["payload"]["cpu"] == 42
    assert rows[0]["payload"]["mem"] == 80


@pytest.mark.asyncio
async def test_recent_events_newest_first():
    await insert_event("agent-a", "metrics", {"i": 1})
    await insert_event("agent-a", "metrics", {"i": 2})
    await insert_event("agent-a", "metrics", {"i": 3})
    rows = await recent_events(limit=10)
    assert [r["payload"]["i"] for r in rows] == [3, 2, 1]


@pytest.mark.asyncio
async def test_filter_by_agent():
    await insert_event("agent-a", "metrics", {"who": "a"})
    await insert_event("agent-b", "metrics", {"who": "b"})
    rows = await recent_events(limit=10, agent_id="agent-b")
    assert len(rows) == 1
    assert rows[0]["agent_id"] == "agent-b"


@pytest.mark.asyncio
async def test_limit_respected():
    for i in range(5):
        await insert_event("agent-a", "metrics", {"i": i})
    rows = await recent_events(limit=2)
    assert len(rows) == 2
