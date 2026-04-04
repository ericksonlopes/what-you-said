import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_event_bus


@pytest.mark.NotificationRouter
class TestNotificationRouter:
    @pytest.fixture
    def mock_event_bus(self):
        mock = MagicMock()
        app.dependency_overrides[get_event_bus] = lambda: mock
        yield mock
        app.dependency_overrides.pop(get_event_bus, None)

    def test_events_stream(self, mock_event_bus):
        # Mock pubsub object
        mock_pubsub = MagicMock()
        mock_event_bus.get_pubsub.return_value = mock_pubsub

        # Configure get_message to return a few messages then trigger an exit
        mock_pubsub.get_message.side_effect = [
            {
                "type": "message",
                "data": json.dumps({"job_id": "1", "status": "processing"}),
            },
            {
                "type": "message",
                "data": json.dumps({"job_id": "1", "status": "completed"}),
            },
            # Throw exception to break the loop safely
            Exception("End of stream"),
        ]

        client = TestClient(app)

        with client.stream("GET", "/rest/notifications/events") as response:
            assert response.status_code == 200
            lines = []
            try:
                # Use a counter to avoid infinite loops if exception isn't caught
                count = 0
                for line in response.iter_lines():
                    if line:
                        lines.append(line)
                    count += 1
                    if count > 10:
                        break
            except Exception:
                pass

            # SSE usually formats as "event: ...\ndata: ..."
            # We just need to check if our keywords appear in the combined output
            all_content = "".join(lines)
            assert "connected" in all_content
            # At least one of our messages should have made it before the exception
            assert "processing" in all_content or "completed" in all_content
            assert "End of stream" in all_content

    def test_events_stream_exception(self, mock_event_bus):
        # Trigger exception in setup
        mock_event_bus.get_pubsub.side_effect = Exception("Redis connection error")

        client = TestClient(app)
        with client.stream("GET", "/rest/notifications/events") as response:
            assert response.status_code == 200
            lines = list(response.iter_lines())
            assert any("error" in line for line in lines)
            assert any("Redis connection error" in line for line in lines)
