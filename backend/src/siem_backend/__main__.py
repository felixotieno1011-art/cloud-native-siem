"""Starlette app: WebSocket ingest + health endpoint."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from siem_backend import __version__
from siem_backend.ws import ingest


async def health(request):
    return JSONResponse({"status": "ok", "version": __version__})


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/health", health),
            WebSocketRoute("/ws/ingest", ingest),
        ]
    )


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_config=None)


if __name__ == "__main__":
    main()
