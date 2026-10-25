"""Simple API key authentication."""

import logging
import os
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse


log = logging.getLogger("siem.auth")


def api_key() -> str:
    """Return the configured API key (or dev default)."""
    return os.environ.get("SIEM_API_KEY", "dev-key-change-me")


def _extract(request_or_ws) -> Optional[str]:
    """Extract key from header or query param."""
    key = request_or_ws.headers.get("x-api-key")
    if key:
        return key
    return request_or_ws.query_params.get("api_key")


async def require_api_key(request: Request):
    """Starlette middleware: reject unauthenticated HTTP requests."""
    if _extract(request) != api_key():
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return None


def check_ws_key(websocket) -> bool:
    """Validate the API key for a WebSocket connection."""
    return _extract(websocket) == api_key()
