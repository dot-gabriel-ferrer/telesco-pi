"""WebSocket event stream."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from apps.backend.app.core.container import AppContainer

router = APIRouter(tags=["events"])


@router.websocket("/ws/events")
async def events_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    container: AppContainer = websocket.app.state.container
    queue = container.event_bus.subscribe()
    try:
        for event in container.event_bus.recent():
            await websocket.send_json(event.model_dump(mode="json"))
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            await websocket.send_json(event.model_dump(mode="json"))
    except (WebSocketDisconnect, TimeoutError):
        pass
    finally:
        container.event_bus.unsubscribe(queue)

