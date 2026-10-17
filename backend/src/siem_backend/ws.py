"""WebSocket ingest endpoint for agent events."""

import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from siem_backend.redis_client import get_redis, push_event


log = logging.getLogger("siem.ws")


async def _safe_push(client, event: dict[str, Any]) -> bool:
    """Push to Redis; on failure, log and return False (don't crash)."""
    try:
        await push_event(client, event)
        return True
    except Exception as exc:
        log.warning("redis push failed: %s", exc)
        return False


async def ingest(websocket: WebSocket) -> None:
    """Accept an agent, parse NDJSON frames, push each event to Redis."""
    await websocket.accept()
    agent_id = websocket.headers.get("x-agent-id", "unknown")
    log.info("agent connected: %s", agent_id)

    client = None
    try:
        client = await get_redis()
    except Exception as exc:
        log.error("redis unavailable: %s", exc)

    ok = fail = 0
    try:
        while True:
            payload = await websocket.receive_text()
            for line in payload.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    event: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("bad json from %s: %r", agent_id, line[:100])
                    continue
                event["_agent_id"] = agent_id
                if client and await _safe_push(client, event):
                    ok += 1
                else:
                    fail += 1
            log.info("agent %s: ingested=%d dropped=%d", agent_id, ok, fail)
    except WebSocketDisconnect:
        log.info("agent disconnected: %s", agent_id)
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                pass
