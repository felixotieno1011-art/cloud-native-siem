# Cloud-Native SIEM & Distributed Network Monitor

[![CI](https://github.com/felixotieno1011-art/cloud-native-siem/actions/workflows/ci.yml/badge.svg)](https://github.com/felixotieno1011-art/cloud-native-siem/actions/workflows/ci.yml)
[![Security](https://github.com/felixotieno1011-art/cloud-native-siem/actions/workflows/security.yml/badge.svg)](https://github.com/felixotieno1011-art/cloud-native-siem/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight, end-to-end Security Information and Event Management (SIEM) system designed to run entirely from a mobile device (Termux).

Collects system metrics, open ports, and auth logs, streams them over WebSockets to a central backend, runs real-time detection rules, and visualizes alerts on a gold-themed React dashboard.

## Architecture


    [ Agent (Termux) ]  ->  WebSocket (NDJSON)
      metrics.py     CPU, Memory, Disk
      ports.py       Connect-scan + /proc fallback
      authlog.py     SSH/Auth log tailer
      client.py      Reconnect + Buffer

    [ Backend (Starlette) ]
      ws.py           Ingest -> Ack -> Detect
      db.py           PostgreSQL: events, alerts
      redis_client.py Live-tail queues
      detections/     Rule engine + 5 rules

    [ Dashboard (React) ]
      Vite + Polling  Alerts, Events, Ack Triage

## Quick Start

Requires: Termux (Android), PostgreSQL, Redis, Node.js.

    git clone https://github.com/felixotieno1011-art/cloud-native-siem.git
    cd cloud-native-siem
    ./dev.sh

    # In a new Termux session (Dashboard):
    cd dashboard
    npm install
    npm run dev -- --host 127.0.0.1 --port 5173

    # In a third Termux session (Agent):
    cd agent
    source .venv/bin/activate
    python -m siem_agent --url ws://127.0.0.1:8080/ws/ingest

Open http://127.0.0.1:5173 on your phone.

## Features

- **Android/Termux native:** bypasses SELinux restrictions on /proc/net/tcp with an active connect-scan fallback.
- **Resilient agent:** WebSocket client with exponential backoff and in-memory buffer for offline events.
- **Dual-path ingest:** events persist to PostgreSQL and mirror to Redis for live-tail streaming.
- **Built-in detections:**
  - auth_fail_spike — more than 5 failed auths in 5 minutes (cooldown enforced)
  - new_listening_port — baselines expected ports; alerts on new ones
  - high_cpu_sustained — CPU above 85% for 3 consecutive cycles
  - port_scan — more than 10 new ports in 30 seconds
  - unusual_outbound — connections to non-private IPs
- **Interactive dashboard:** gold-themed React UI with live polling and alert acknowledgment.

## Testing

    cd agent && source .venv/bin/activate && pytest tests/ -v
    cd backend && source .venv/bin/activate && pytest tests/ -v

25 backend tests + 8 agent tests = 33 total, run on every push via GitHub Actions.

## Documentation

- [Security & Threat Model](SECURITY.md)
- [Architecture Details](docs/architecture.md)
- [API Reference](docs/api.md)

## License

MIT — see [LICENSE](LICENSE).
