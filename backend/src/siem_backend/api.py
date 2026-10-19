"""HTTP API endpoints."""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from siem_backend.db import recent_events


log = logging.getLogger("siem.api")


async def list_events(request: Request) -> JSONResponse:
    """GET /api/events?limit=50&agent_id=...

    Returns the most recent events, newest first.
    """
    try:
        limit = int(request.query_params.get("limit", "50"))
    except ValueError:
        return JSONResponse({"error": "limit must be an integer"}, status_code=400)
    limit = max(1, min(limit, 500))

    agent_id = request.query_params.get("agent_id") or None
    if agent_id is not None and len(agent_id) > 128:
        return JSONResponse({"error": "agent_id too long"}, status_code=400)

    try:
        rows = await recent_events(limit=limit, agent_id=agent_id)
    except Exception as exc:
        log.error("recent_events failed: %s", exc)
        return JSONResponse({"error": "query failed"}, status_code=500)

    return JSONResponse({"events": rows, "count": len(rows), "limit": limit})


async def list_alerts(request: Request) -> JSONResponse:
    """GET /api/alerts?limit=50&agent_id=...

    Returns the most recent alerts, newest first.
    """
    try:
        limit = int(request.query_params.get("limit", "50"))
    except ValueError:
        return JSONResponse({"error": "limit must be an integer"}, status_code=400)
    limit = max(1, min(limit, 500))

    agent_id = request.query_params.get("agent_id") or None
    if agent_id is not None and len(agent_id) > 128:
        return JSONResponse({"error": "agent_id too long"}, status_code=400)

    try:
        from siem_backend.db import recent_alerts
        rows = await recent_alerts(limit=limit, agent_id=agent_id)
    except Exception as exc:
        log.error("recent_alerts failed: %s", exc)
        return JSONResponse({"error": "query failed"}, status_code=500)

    return JSONResponse({"alerts": rows, "count": len(rows), "limit": limit})


async def ack_alert_endpoint(request: Request) -> JSONResponse:
    """POST /api/alerts/{id}/ack"""
    try:
        alert_id = int(request.path_params["alert_id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "invalid alert id"}, status_code=400)

    from siem_backend.db import ack_alert
    try:
        ok = await ack_alert(alert_id)
    except Exception as exc:
        log.error("ack failed: %s", exc)
        return JSONResponse({"error": "ack failed"}, status_code=500)

    if not ok:
        return JSONResponse({"error": "not found or already acked"}, status_code=404)
    return JSONResponse({"ok": True, "id": alert_id})
