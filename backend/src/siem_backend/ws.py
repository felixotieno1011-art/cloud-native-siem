"""WebSocket ingest endpoint: parse NDJSON, persist to PG, mirror to Redis."""

import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from siem_backend.db import insert_event
from siem_backend.redis_client import get_redis, push_event


log = logging.getLogger("siem.ws")


async def _process_line(
    line: str, agent_id: str, redis_client, counters: dict[str, int]
) -> None:
    try:
        event: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError:
        log.warning("bad json from %s: %r", agent_id, line[:80])
        return

    event_type = event.get("type", "unknown")
    try:
        await insert_event(agent_id, event_type, event)
        counters["pg_ok"] += 1
    except Exception as exc:
        log.warning("pg insert failed: %s", exc)
        counters["pg_fail"] += 1

    if redis_client is not None:
        try:
            await push_event(redis_client, {**event, "_agent_id": agent_id})
            counters["redis_ok"] += 1
        except Exception as exc:
            log.warning("redis push failed: %s", exc)
            counters["redis_fail"] += 1


async def ingest(websocket: WebSocket) -> None:
    """Accept an agent, parse NDJSON frames, persist each event, ack."""
    await websocket.accept()
    agent_id = websocket.headers.get("x-agent-id", "unknown")
    log.info("agent connected: %s", agent_id)

    redis_client = None
    try:
        redis_client = await get_redis()
    except Exception as exc:
        log.warning("redis unavailable: %s", exc)

    counters = {"pg_ok": 0, "pg_fail": 0, "redis_ok": 0, "redis_fail": 0}

    try:
        while True:
            payload = await websocket.receive_text()
            batch_ok = batch_fail = 0
            for line in payload.split("\n"):
                line = line.strip()
                if not line:
                    continue
                before = counters["pg_ok"] + counters["pg_fail"]
                await _process_line(line, agent_id, redis_client, counters)
                after = counters["pg_ok"] + counters["pg_fail"]
                if after > before:
                    batch_ok += 1
                else:
                    batch_fail += 1
            try:
                await websocket.send_json(
                    {"ack": batch_ok, "failed": batch_fail, **counters}
                )
            except Exception:
                pass
            log.info("agent %s: %s", agent_id, counters)
    except WebSocketDisconnect:
        log.info("agent disconnected: %s", agent_id)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
