"""Starlette app: WebSocket ingest + HTTP API + health."""

import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from siem_backend import __version__
from siem_backend.api import list_alerts, list_events
from siem_backend.db import init_alerts_schema, init_schema
from siem_backend.detections import rules  # noqa: F401
from siem_backend.ws import ingest


log = logging.getLogger("siem.app")


@asynccontextmanager
async def lifespan(app):
    log.info("startup: initializing schemas")
    try:
        await init_schema()
        await init_alerts_schema()
        log.info("startup: schemas ready")
    except Exception as exc:
        log.error("startup: schema init failed: %s", exc)
        raise
    yield
    log.info("shutdown")


async def health(request):
    return JSONResponse({"status": "ok", "version": __version__})


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/health", health),
            Route("/api/events", list_events, methods=["GET"]),
            Route("/api/alerts", list_alerts, methods=["GET"]),
            WebSocketRoute("/ws/ingest", ingest),
        ],
        lifespan=lifespan,
    )


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_config=None)


if __name__ == "__main__":
    main()
