"""Tests for the resilient WebSocket client."""

import asyncio
import json

import pytest
import websockets

from siem_agent.client import AgentClient


@pytest.mark.asyncio
async def test_buffer_holds_events_when_disconnected():
    client = AgentClient("ws://127.0.0.1:1", agent_id="test")
    for i in range(5):
        client.enqueue({"type": "metrics", "i": i})
    assert len(client.buffer) == 5


@pytest.mark.asyncio
async def test_buffer_drops_oldest_when_full():
    from siem_agent.client import MAX_BUFFER
    client = AgentClient("ws://127.0.0.1:1", agent_id="test")
    for i in range(MAX_BUFFER + 10):
        client.enqueue({"i": i})
    assert len(client.buffer) == MAX_BUFFER
    assert client.buffer[0]["i"] == 10  # oldest 10 dropped


@pytest.mark.asyncio
async def test_sends_ndjson_batch():
    received: list[str] = []

    async def handler(ws):
        async for msg in ws:
            received.append(msg)
            break  # one batch then close

    async with websockets.serve(handler, "127.0.0.1", 18765):
        client = AgentClient("ws://127.0.0.1:18765", agent_id="test")
        client.enqueue({"type": "a"})
        client.enqueue({"type": "b"})

        task = asyncio.create_task(client.run())
        await asyncio.sleep(2.0)
        client.stop()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    assert len(received) >= 1
    lines = received[0].split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["type"] == "a"
    assert json.loads(lines[1])["type"] == "b"
