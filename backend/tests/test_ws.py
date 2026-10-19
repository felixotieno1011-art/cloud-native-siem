"""WebSocket ingest tests: PG persistence + ack protocol."""

import asyncio
import json

from starlette.testclient import TestClient

from siem_backend.__main__ import create_app
from siem_backend.db import recent_events


def _send_and_ack(frame: str, agent_id: str) -> dict:
    client = TestClient(create_app())
    with client.websocket_connect(
        "/ws/ingest", headers={"x-agent-id": agent_id}
    ) as ws:
        ws.send_text(frame)
        return ws.receive_json()


def test_ingest_single_event():
    ack = _send_and_ack(json.dumps({"type": "metrics", "cpu": 10}), "test-1")
    assert ack["ack"] == 1
    assert ack["failed"] == 0
    rows = asyncio.run(recent_events(limit=10, agent_id="test-1"))
    assert len(rows) == 1
    assert rows[0]["payload"]["cpu"] == 10


def test_ingest_ndjson_batch():
    payload = "\n".join([
        json.dumps({"type": "metrics"}),
        json.dumps({"type": "port_opened", "port": 22}),
        "",
        json.dumps({"type": "auth", "line": "x"}),
    ])
    ack = _send_and_ack(payload, "test-2")
    assert ack["ack"] == 3
    rows = asyncio.run(recent_events(limit=10, agent_id="test-2"))
    assert len(rows) == 3
    types = {r["event_type"] for r in rows}
    assert types == {"metrics", "port_opened", "auth"}


def test_ingest_skips_bad_json():
    frame = "not json\n" + json.dumps({"type": "metrics"})
    ack = _send_and_ack(frame, "test-3")
    assert ack["ack"] == 1
    rows = asyncio.run(recent_events(limit=10, agent_id="test-3"))
    assert len(rows) == 1
