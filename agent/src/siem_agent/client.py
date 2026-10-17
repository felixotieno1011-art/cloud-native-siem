"""Resilient WebSocket client for the SIEM backend.

Features:
- auto-reconnect with exponential backoff
- bounded in-memory buffer of unsent events (drops oldest if full)
- sends newline-delimited JSON (NDJSON) frames
"""

import asyncio
import json
import time
from collections import deque
from typing import Any

import websockets


MAX_BUFFER = 1000
RECONNECT_BASE = 1.0
RECONNECT_MAX = 30.0


class AgentClient:
    """Async WebSocket client for shipping events to the backend."""

    def __init__(self, url: str, agent_id: str, token: str = "") -> None:
        self.url = url
        self.agent_id = agent_id
        self.token = token
        self.buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFER)
        self._stop = asyncio.Event()

    def enqueue(self, event: dict[str, Any]) -> None:
        """Add an event to the buffer (thread-safe enough for our loop)."""
        self.buffer.append(event)


    def _headers(self) -> dict[str, str]:
        headers = {"X-Agent-Id": self.agent_id}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _drain(self, ws) -> None:
        """Send all buffered events as one NDJSON frame."""
        if not self.buffer:
            return
        batch = list(self.buffer)
        payload = "\n".join(json.dumps(e) for e in batch)
        await ws.send(payload)
        # only clear after send succeeds
        for _ in range(len(batch)):
            self.buffer.popleft()

    async def run(self) -> None:
        """Main loop: connect, drain, reconnect on failure."""
        backoff = RECONNECT_BASE
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.url,
                    additional_headers=self._headers(),
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    backoff = RECONNECT_BASE
                    while not self._stop.is_set():
                        await self._drain(ws)
                        await asyncio.sleep(1.0)
            except (OSError, websockets.WebSocketException):
                await asyncio.sleep(backoff)
                backoff = min(RECONNECT_MAX, backoff * 2)

    def stop(self) -> None:
        self._stop.set()
