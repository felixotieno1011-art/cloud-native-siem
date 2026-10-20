# Architecture & Design Decisions

## 1. The Termux Constraints
Building a SIEM on Android required solving several platform-specific problems:
- **No `psutil`:** Android blocks standard `psutil` builds. We parse `/proc/meminfo`, `/proc/loadavg`, and `os.statvfs` directly.
- **No `/proc/net/tcp`:** SELinux hides TCP tables from unprivileged apps. The agent falls back to a localized `socket.connect()` scan on common ports.
- **No Docker:** The backend and PostgreSQL run as native Termux processes orchestrated by `dev.sh`.

## 2. Data Flow & Storage
- **Source of Truth:** PostgreSQL stores all `events` and `alerts`.
- **Live-Tail:** Redis `RPUSH` is used for ephemeral queues (`siem:events:queue`, `siem:alerts:queue`) to decouple ingest from detection and allow future dashboard websockets.
- **Sync/Async Bridge:** `pg8000` is synchronous. To avoid blocking the Starlette event loop, all DB operations are wrapped in `asyncio.to_thread()`.

## 3. Detection Engine
Rules implement a `Rule` protocol (`evaluate(event, agent_id, context)`). 
The `RuleContext` keeps mutable state per agent (sliding windows, baselines). 
This state currently lives in-process memory; a future upgrade will move it to Redis to support multiple backend replicas.

## 4. WebSocket Ack Protocol
When an agent sends a batch (NDJSON), the server replies with an `ack` containing `pg_ok` and `alerts_fired`. This ensures the agent (and tests) know exactly when a frame has been fully processed.
