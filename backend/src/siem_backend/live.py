"""Live dashboard WebSocket feed."""

import asyncio
import json
from starlette.websockets import WebSocket, WebSocketDisconnect
from siem_backend.redis_client import get_redis, EVENT_QUEUE_KEY, ALERT_QUEUE_KEY

async def live_feed(websocket: WebSocket) -> None:
    await websocket.accept()
    client = await get_redis()
    
    try:
        while True:
            # BLPOP blocks until an event/alert arrives in Redis
            res = await client.blpop([EVENT_QUEUE_KEY, ALERT_QUEUE_KEY], timeout=1)
            if res:
                queue_name, data = res
                payload = json.loads(data)
                await websocket.send_json({"queue": queue_name, "data": payload})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await client.aclose()
