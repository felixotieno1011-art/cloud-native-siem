"""Starlette app: WebSocket ingest + HTTP API + health."""

import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from siem_backend import __version__
from siem_backend.api import ack_alert_endpoint, list_alerts, list_events
from siem_backend.db import ensure_ack_column, init_alerts_schema, init_schema
from siem_backend.detections import rules  # noqa: F401
from siem_backend.ws import ingest
from siem_backend.live import live_feed


log = logging.getLogger("siem.app")


@asynccontextmanager
async def lifespan(app):
    log.info("startup: initializing schemas")
    try:
        await init_schema()
        await init_alerts_schema()
        await ensure_ack_column()
        log.info("startup: schemas ready")
    except Exception as exc:
        log.error("startup: schema init failed: %s", exc)
        raise
    yield
    log.info("shutdown")


async def health(request):
    return JSONResponse({"status": "ok", "version": __version__})


def create_app() -> Starlette:
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        ),
    ]
    return Starlette(
        routes=[
            Route("/health", health),
            Route("/api/events", list_events, methods=["GET"]),
            Route("/api/alerts", list_alerts, methods=["GET"]),
            Route("/api/alerts/{alert_id:int}/ack", ack_alert_endpoint, methods=["POST"]),
            WebSocketRoute("/ws/ingest", ingest),
            WebSocketRoute("/ws/live", live_feed),
        ],
        middleware=middleware,
        lifespan=lifespan,
    )


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_config=None)


if __name__ == "__main__":
    main()
