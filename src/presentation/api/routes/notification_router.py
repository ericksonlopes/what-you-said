import json
from typing import AsyncGenerator, Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from src.domain.interfaces.services.i_event_bus import IEventBus
from src.presentation.api.dependencies import get_event_bus

router = APIRouter()


@router.get("/events")
async def events(
    request: Request,
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
) -> EventSourceResponse:
    """
    Server-Sent Events (SSE) endpoint that streams ingestion status updates.
    """

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Subscribe to Redis ingestion_status channel
        # Note: subscribe() is a generator that blocks. We use a separate thread or
        # async-friendly subscription if available.
        # For a simple implementation, we'll use the blocking subscribe in a separate executor
        # but modern redis-py has async support.

        # In a real async environment, we should use async redis.
        # But since our RedisEventBus is currently synchronous, we adapt it.
        # For this demonstration, we'll yield a simple started message.

        yield {
            "event": "connected",
            "data": json.dumps({"message": "SSE connection established"}),
        }

        try:
            # This is a simplified listener. In production, use redis.asyncio
            for message in event_bus.subscribe("ingestion_status"):
                if await request.is_disconnected():
                    break

                yield {"event": "message", "data": json.dumps(message)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
