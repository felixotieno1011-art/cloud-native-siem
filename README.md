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

```text
[ Agent (Termux) ]
  ├── metrics.py       (CPU, Memory, Disk)
  ├── ports.py         (Connect-scan + /proc fallback)
  ├── authlog.py       (SSH/Auth log tailer)
  └── client.py        (WebSocket + NDJSON)
         │
         ▼ ws://127.0.0.1:8080/ws/ingest
[ Backend (Starlette) ]
  ├── ws.py            (Ingest, Ack, Detection Dispatch)
  ├── db.py            (PostgreSQL: events, alerts)
  ├── redis_client.py  (Live-tail queues)
  └── detections/      (Rule engine + 5 rules)
         │
         ▼ HTTP API
[ Dashboard (React) ]
  └── Vite + Polling    (Alerts, Events, Ack Triage)
