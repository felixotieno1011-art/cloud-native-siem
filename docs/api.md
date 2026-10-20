# API Reference

Base URL: `http://127.0.0.1:8080`

## `GET /health`
Returns system status.
**Response:** `{"status": "ok", "version": "0.1.0"}`

## `GET /api/events`
Fetch recent events.
**Query Params:**
- `limit` (int, default 50, max 500)
- `agent_id` (string, optional)

**Response:**
```json
{
  "events": [
    {"id": 1, "agent_id": "localhost", "event_type": "metrics", "payload": {...}, "received_at": "..."}
  ],
  "count": 1,
  "limit": 50
}
