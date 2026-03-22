import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.infrastructure.loggers.std_logger import (
    set_global_context,
    clear_global_context,
)


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a correlation_id to each request and sets it in the logger's global context.
    """

    async def dispatch(self, request: Request, call_next):
        # Use existing correlation ID if provided, otherwise generate a new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Set correlation_id in the global logging context (contextvars)
        set_global_context({"correlation_id": correlation_id})

        try:
            response = await call_next(request)
            # Ensure the correlation ID is returned in the response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Clear context after request is finished
            clear_global_context()
