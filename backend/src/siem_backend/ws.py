"""WebSocket ingest endpoint: parse NDJSON, persist to PG, mirror to Redis."""

import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from siem_backend.db import insert_event
from siem_backend.redis_client import get_redis, push_event


log = logging.getLogger("siem.ws")


async def ingest(websocket: WebSocket) -> None:
    """Accept an agent, parse NDJSON frames, persist each event."""
    await websocket.accept()
    agent_id = websocket.headers.get("x-agent-id", "unknown")
    log.info("agent connected: %s", agent_id)

    redis_client = None
    try:
        redis_client = await get_redis()
    except Exception as exc:
        log.warning("redis unavailable: %s", exc)

    pg_ok = pg_fail = redis_ok = redis_fail = 0

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
                    log.warning("bad json from %s: %r", agent_id, line[:80])
                    continue

                event_type = event.get("type", "unknown")
                try:
                    await insert_event(agent_id, event_type, event)
                    pg_ok += 1
                except Exception as exc:
                    log.warning("pg insert failed: %s", exc)
                    pg_fail += 1

                if redis_client is not None:
                    try:
                        await push_event(redis_client, {**event, "_agent_id": agent_id})
                        redis_ok += 1
                    except Exception as exc:
                        log.warning("redis push failed: %s", exc)
                        redis_fail += 1

            log.info(
                "agent %s: pg_ok=%d pg_fail=%d redis_ok=%d redis_fail=%d",
                agent_id, pg_ok, pg_fail, redis_ok, redis_fail,
            )
    except WebSocketDisconnect:
        log.info("agent disconnected: %s", agent_id)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
