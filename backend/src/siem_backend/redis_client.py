"""Redis client and event queue helpers."""

import os
from typing import Any

import redis.asyncio as redis


EVENT_QUEUE_KEY = "siem:events:queue"


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")


async def get_redis() -> redis.Redis:
    """Return an async Redis client."""
    return redis.from_url(redis_url(), decode_responses=True)


async def push_event(client: redis.Redis, event: dict[str, Any]) -> None:
    """Append an event to the staging queue."""
    import json
    await client.rpush(EVENT_QUEUE_KEY, json.dumps(event))
