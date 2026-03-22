import uuid
import time
from unittest.mock import MagicMock
from types import SimpleNamespace

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.use_cases.youtube_ingestion_use_case import YoutubeIngestionUseCase
from src.application.dtos.enums.youtube_data_type import YoutubeDataType


class DummyDoc:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


def make_use_case_mocks():
    ks = MagicMock()
    ks.get_by_name.return_value = SimpleNamespace(id=uuid.uuid4(), name="s")
    ks.get_subject_by_id.return_value = SimpleNamespace(id=uuid.uuid4(), name="s")

    cs = MagicMock()
    cs.get_by_source_info.return_value = None
    cs._repo = MagicMock()

    isvc = MagicMock()
    isvc.create_job.return_value = SimpleNamespace(id=uuid.uuid4())
    isvc.get_by_id.return_value = None

    model_loader = SimpleNamespace(model_name="test")
    embedding = MagicMock()
    chunk_svc = MagicMock()
    vec_svc = MagicMock()
    event_bus = MagicMock()

    return YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc, "weaviate", event_bus
    )


def test_throttling_logic(monkeypatch):
    use_case = make_use_case_mocks()

    # Mock settings
    from src.config.settings import settings

    monkeypatch.setattr(settings.youtube, "throttle_batch_size", 2)
    monkeypatch.setattr(settings.youtube, "throttle_wait_seconds", 0.1)

    # Mock video processing methods to avoid actual extraction
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: url)
    monkeypatch.setattr(
        use_case,
        "_process_single_video",
        lambda *args: {"video_url": "url", "created_chunks": 1},
    )
    monkeypatch.setattr(
        use_case,
        "_resolve_subject",
        lambda *args: SimpleNamespace(id=uuid.uuid4(), name="s"),
    )

    # Mock extract_playlist_videos to return 5 videos
    from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

    monkeypatch.setattr(
        YoutubeExtractor,
        "extract_playlist_videos",
        lambda url: ["v1", "v2", "v3", "v4", "v5"],
    )

    # Spy on time.sleep
    sleep_calls = []

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", mock_sleep)
    import random
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)

    cmd = IngestYoutubeCommand(        video_url="https://youtube.com/playlist?list=PL123",
        subject_name="s",
        data_type=YoutubeDataType.PLAYLIST,
    )

    result = use_case.execute(cmd)

    # 5 videos, batch size 2 -> 3 batches
    # Batch 1: v1, v2 -> sleep
    # Batch 2: v3, v4 -> sleep
    # Batch 3: v5 -> no sleep

    assert len(result.video_results) == 5
    assert len(sleep_calls) == 2
    assert sleep_calls == [0.1, 0.1]
