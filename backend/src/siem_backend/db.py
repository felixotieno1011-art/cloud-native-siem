"""PostgreSQL persistence layer (pg8000, sync wrapped in threads)."""

import asyncio
import json
import logging
import os
from typing import Any

import pg8000.native


log = logging.getLogger("siem.db")


def _cfg() -> dict[str, Any]:
    return {
        "user": os.environ.get("PGUSER", "u0_a333"),
        "password": os.environ.get("PGPASSWORD", None),
        "host": os.environ.get("PGHOST", "127.0.0.1"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "database": os.environ.get("PGDATABASE", "siem"),
    }


def _conn() -> pg8000.native.Connection:
    return pg8000.native.Connection(**_cfg())


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_agent_time
    ON events (agent_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time
    ON events (event_type, received_at DESC);
"""


def _init_schema_sync() -> None:
    conn = _conn()
    try:
        for stmt in SCHEMA.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.run(stmt)
        log.info("schema ready")
    finally:
        conn.close()


async def init_schema() -> None:
    """Create tables and indexes if they do not exist."""
    await asyncio.to_thread(_init_schema_sync)


def _insert_event_sync(agent_id: str, event_type: str, payload: dict) -> int:
    conn = _conn()
    try:
        rows = conn.run(
            "INSERT INTO events (agent_id, event_type, payload) "
            "VALUES (:agent_id, :event_type, :payload::jsonb) RETURNING id",
            agent_id=agent_id,
            event_type=event_type,
            payload=json.dumps(payload),
        )
        return int(rows[0][0])
    finally:
        conn.close()


async def insert_event(agent_id: str, event_type: str, payload: dict) -> int:
    """Insert one event, return its row id."""
    return await asyncio.to_thread(_insert_event_sync, agent_id, event_type, payload)


def _recent_events_sync(limit: int, agent_id: str | None) -> list[dict]:
    conn = _conn()
    try:
        if agent_id:
            rows = conn.run(
                "SELECT id, agent_id, event_type, payload, received_at "
                "FROM events WHERE agent_id = :agent_id "
                "ORDER BY id DESC LIMIT :limit",
                agent_id=agent_id, limit=limit,
            )
        else:
            rows = conn.run(
                "SELECT id, agent_id, event_type, payload, received_at "
                "FROM events ORDER BY id DESC LIMIT :limit",
                limit=limit,
            )
        return [
            {
                "id": r[0],
                "agent_id": r[1],
                "event_type": r[2],
                "payload": r[3],
                "received_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


async def recent_events(limit: int = 50, agent_id: str | None = None) -> list[dict]:
    """Return the most recent events, newest first."""
    return await asyncio.to_thread(_recent_events_sync, limit, agent_id)


ALERTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_agent_time
    ON alerts (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_rule_time
    ON alerts (rule_id, created_at DESC);
"""


def _init_alerts_schema_sync() -> None:
    conn = _conn()
    try:
        for stmt in ALERTS_SCHEMA.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.run(stmt)
        log.info("alerts schema ready")
    finally:
        conn.close()


async def init_alerts_schema() -> None:
    """Create alerts table and indexes if missing."""
    await asyncio.to_thread(_init_alerts_schema_sync)


def _insert_alert_sync(
    agent_id: str, rule_id: str, severity: str, title: str, details: dict
) -> int:
    conn = _conn()
    try:
        rows = conn.run(
            "INSERT INTO alerts (agent_id, rule_id, severity, title, details) "
            "VALUES (:agent_id, :rule_id, :severity, :title, :details::jsonb) "
            "RETURNING id",
            agent_id=agent_id, rule_id=rule_id, severity=severity,
            title=title, details=json.dumps(details),
        )
        return int(rows[0][0])
    finally:
        conn.close()


async def insert_alert(
    agent_id: str, rule_id: str, severity: str, title: str, details: dict
) -> int:
    """Insert one alert, return its row id."""
    return await asyncio.to_thread(
        _insert_alert_sync, agent_id, rule_id, severity, title, details
    )


def _recent_alerts_sync(limit: int, agent_id: str | None) -> list[dict]:
    conn = _conn()
    try:
        if agent_id:
            rows = conn.run(
                "SELECT id, agent_id, rule_id, severity, title, details, created_at "
                "FROM alerts WHERE agent_id = :agent_id "
                "ORDER BY id DESC LIMIT :limit",
                agent_id=agent_id, limit=limit,
            )
        else:
            rows = conn.run(
                "SELECT id, agent_id, rule_id, severity, title, details, created_at "
                "FROM alerts ORDER BY id DESC LIMIT :limit",
                limit=limit,
            )
        return [
            {
                "id": r[0],
                "agent_id": r[1],
                "rule_id": r[2],
                "severity": r[3],
                "title": r[4],
                "details": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


async def recent_alerts(limit: int = 50, agent_id: str | None = None) -> list[dict]:
    """Return the most recent alerts, newest first."""
    return await asyncio.to_thread(_recent_alerts_sync, limit, agent_id)
