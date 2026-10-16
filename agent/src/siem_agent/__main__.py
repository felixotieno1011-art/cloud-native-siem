"""Agent entrypoint: collect metrics, sockets, and auth events."""

import json
import time

from siem_agent.metrics import get_system_metrics
from siem_agent.ports import collect_sockets, listening_ports
from siem_agent.authlog import AuthLogTailer

INTERVAL_SECONDS = 10


def emit(event_type: str, payload: dict) -> None:
    """Print a structured event as one JSON line."""
    print(json.dumps({"type": event_type, **payload}), flush=True)


def main() -> None:
    print("Cloud-Native SIEM Agent starting...", flush=True)
    tailer = AuthLogTailer()
    known_listeners: set[int] = set()

    while True:
        emit("metrics", get_system_metrics().to_dict())

        listeners = set(listening_ports())
        for port in sorted(listeners - known_listeners):
            emit("port_opened", {"port": port})
        for port in sorted(known_listeners - listeners):
            emit("port_closed", {"port": port})
        known_listeners = listeners

        for entry in collect_sockets():
            if entry.state == "ESTABLISHED":
                emit("connection", entry.to_dict())

        for auth_event in tailer.tail():
            emit("auth", auth_event.to_dict())

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
