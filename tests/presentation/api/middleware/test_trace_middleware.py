import anyio
import pytest
from starlette.responses import Response
from src.presentation.api.middleware.trace_middleware import TraceMiddleware


@pytest.mark.anyio
async def test_trace_middleware_adds_headers():
    # Arrange
    app_called = False

    async def mock_app(scope, receive, send):
        nonlocal app_called
        app_called = True
        response = Response("ok")
        await response(scope, receive, send)

    middleware = TraceMiddleware(mock_app)

    scope = {
        "type": "http",
        "headers": [],
        "method": "GET",
        "path": "/",
    }

    async def receive():
        await anyio.lowlevel.checkpoint()
        return {"type": "http.request"}

    async def send(message):
        await anyio.lowlevel.checkpoint()
        if message["type"] == "http.response.start":
            # In Starlette, headers are list of tuples (bytes, bytes)
            header_keys = [k.decode("utf-8").lower() for k, v in message["headers"]]
            assert "x-correlation-id" in header_keys

    # Act
    await middleware(scope, receive, send)

    # Assert
    assert app_called
