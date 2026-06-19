"""Internal in-memory event bus."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone

from apps.backend.app.api.schemas import EventEnvelope
from libs.diagnostics.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """Simple async event bus for state fan-out."""

    def __init__(self, max_backlog: int = 100, subscriber_queue_size: int = 50) -> None:
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()
        self._backlog: deque[EventEnvelope] = deque(maxlen=max_backlog)
        self._subscriber_queue_size = subscriber_queue_size

    def subscribe(self) -> asyncio.Queue[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=self._subscriber_queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[EventEnvelope]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event_type: str, source: str, payload: dict, correlation_id: str | None = None) -> EventEnvelope:
        event = EventEnvelope(
            event_type=event_type,
            source=source,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            payload=payload,
        )
        self._backlog.append(event)
        stale_subscribers: list[asyncio.Queue[EventEnvelope]] = []
        for subscriber in self._subscribers:
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:
                stale_subscribers.append(subscriber)
        for subscriber in stale_subscribers:
            logger.warning("Dropping slow event subscriber")
            self.unsubscribe(subscriber)
        return event

    def recent(self) -> list[EventEnvelope]:
        return list(self._backlog)

