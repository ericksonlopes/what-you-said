import os
import sys
from unittest.mock import MagicMock

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Mock out dependencies before importing workers
sys.modules['src.presentation.api.dependencies'] = MagicMock()
mock_job_service = MagicMock()

class MockContext:
    def __init__(self, job_svc):
        self.job_service = job_svc

import src.presentation.api.dependencies as deps  # noqa: E402

deps.resolve_ingestion_context = MagicMock(return_value=MockContext(mock_job_service))

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand  # noqa: E402
from src.application.dtos.enums.youtube_data_type import YoutubeDataType  # noqa: E402
from src.application.workers import run_youtube_dispatcher_worker  # noqa: E402


def test_dispatcher():
    # Setup mock app state
    mock_app = MagicMock()
    mock_app.state.task_queue = MagicMock()
    
    # Patch _get_app to return our mock
    import src.application.workers as workers  # noqa: E402
    workers._get_app = MagicMock(return_value=mock_app)
    
    # Create command for a small playlist (or the user's one)
    # Using a known small playlist to speed up test if possible
    # But user's URL is fine since we are testing logic
    url = "https://www.youtube.com/watch?v=dlQG02mwTD0&list=PLG47XsLEf0LdvYtX_zU7E_y_C1TgjgU59"
    cmd = IngestYoutubeCommand(
        video_url=url,
        data_type=YoutubeDataType.PLAYLIST,
        ingestion_job_id="test-job-uuid",
        subject_id="test-subject"
    )
    
    print(f"Testing dispatcher with URL: {url}")
    run_youtube_dispatcher_worker(cmd)
    
    # Assertions
    print("\nVerifying Job Service calls:")
    for call in mock_job_service.update_job_status.call_args_list:
        print(f"  - Status update: {call[1]}")
        
    print("\nVerifying Task Queue calls:")
    enqueue_calls = mock_app.state.task_queue.enqueue.call_args_list
    print(f"  - Tasks enqueued: {len(enqueue_calls)}")
    if len(enqueue_calls) > 0:
        print(f"  - First task URL: {enqueue_calls[0][0][1].video_url}")

if __name__ == "__main__":
    test_dispatcher()
