import asyncio
import json
from typing import Annotated, AsyncGenerator

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
        try:
            yield {
                "event": "connected",
                "data": json.dumps({"message": "SSE connection established"}),
            }

            loop = asyncio.get_event_loop()
            pubsub = event_bus.get_pubsub()
            pubsub.subscribe("ingestion_status")

            try:
                while not await request.is_disconnected():
                    message = await loop.run_in_executor(
                        None, lambda: pubsub.get_message(timeout=1.0)
                    )
                    if message and message["type"] == "message":
                        data = json.loads(message["data"])
                        yield {"event": "message", "data": json.dumps(data)}
            finally:
                pubsub.unsubscribe("ingestion_status")
                pubsub.close()
        except asyncio.CancelledError:
            # Clean exit on cancellation
            pass
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
