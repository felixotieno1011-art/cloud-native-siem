"""Agent entrypoint: collect events and ship via stdout or WebSocket."""

import argparse
import asyncio
import json
import os
import socket
import uuid

from siem_agent.authlog import AuthLogTailer
from siem_agent.client import AgentClient
from siem_agent.metrics import get_system_metrics
from siem_agent.ports import collect_sockets, listening_ports


INTERVAL_SECONDS = 10


def agent_id() -> str:
    """Stable per-install agent identifier."""
    path = os.path.expanduser("~/.siem_agent_id")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    new_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    with open(path, "w") as f:
        f.write(new_id)
    return new_id


def build_events(tailer: AuthLogTailer, known: set[int]) -> tuple[list[dict], set[int]]:
    events: list[dict] = [{"type": "metrics", **get_system_metrics().to_dict()}]

    listeners = set(listening_ports())
    for port in sorted(listeners - known):
        events.append({"type": "port_opened", "port": port})
    for port in sorted(known - listeners):
        events.append({"type": "port_closed", "port": port})

    for entry in collect_sockets():
        if entry.state == "ESTABLISHED":
            events.append({"type": "connection", **entry.to_dict()})

    for auth_event in tailer.tail():
        events.append({"type": "auth", **auth_event.to_dict()})

    return events, listeners


async def run_agent(url: str | None, dry_run: bool) -> None:
    tailer = AuthLogTailer()
    known: set[int] = set()
    client = AgentClient(url, agent_id=agent_id()) if url else None
    if client:
        asyncio.create_task(client.run())

    print(f"agent_id={agent_id()} url={url or 'stdout'} dry_run={dry_run}", flush=True)
    while True:
        events, known = build_events(tailer, known)
        for event in events:
            if client is None or dry_run:
                print(json.dumps(event), flush=True)
            else:
                client.enqueue(event)
        await asyncio.sleep(INTERVAL_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="WebSocket URL of the SIEM backend")
    parser.add_argument("--dry-run", action="store_true", help="print to stdout only")
    args = parser.parse_args()
    try:
        asyncio.run(run_agent(args.url, args.dry_run))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
