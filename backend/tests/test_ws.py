"""WebSocket ingest tests."""

import json

from starlette.testclient import TestClient

from siem_backend.__main__ import create_app


def test_ingest_single_event(fake_redis):
    client = TestClient(create_app())
    with client.websocket_connect(
        "/ws/ingest", headers={"x-agent-id": "test-1"}
    ) as ws:
        ws.send_text(json.dumps({"type": "metrics", "cpu": 10}))
    assert len(fake_redis.data) == 1
    assert json.loads(fake_redis.data[0])["_agent_id"] == "test-1"


def test_ingest_ndjson_batch(fake_redis):
    client = TestClient(create_app())
    payload = "\n".join([
        json.dumps({"type": "metrics"}),
        json.dumps({"type": "port_opened", "port": 22}),
        "",
        json.dumps({"type": "auth", "line": "x"}),
    ])
    with client.websocket_connect(
        "/ws/ingest", headers={"x-agent-id": "test-2"}
    ) as ws:
        ws.send_text(payload)
    assert len(fake_redis.data) == 3


def test_ingest_skips_bad_json(fake_redis):
    client = TestClient(create_app())
    with client.websocket_connect(
        "/ws/ingest", headers={"x-agent-id": "test-3"}
    ) as ws:
        ws.send_text("not json\n" + json.dumps({"type": "metrics"}))
    assert len(fake_redis.data) == 1
