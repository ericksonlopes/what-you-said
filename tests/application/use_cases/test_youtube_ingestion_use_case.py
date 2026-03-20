import pytest
import uuid
from types import SimpleNamespace

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.use_cases.youtube_ingestion_use_case import YoutubeIngestionUseCase


class DummyDoc:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


def make_ks_service():
    class KS:
        def get_by_name(self, name: str):
            return SimpleNamespace(id=uuid.uuid4(), name=name)

        def get_subject_by_id(self, id: uuid.UUID):
            return SimpleNamespace(id=id, name="subject")

    return KS()


def make_cs_service(existing: bool = False):
    class CS:
        def __init__(self):
            self.created = None
            self._repo = SimpleNamespace(update_title=lambda **kwargs: None)

        def get_by_source_info(self, source_type, external_source, **kwargs):
            return (
                SimpleNamespace(
                    id=uuid.uuid4(),
                    processing_status="done",
                    source_type="youtube",
                    external_source=external_source,
                )
                if existing
                else None
            )

        def get_by_id(self, id):
            return SimpleNamespace(id=id, processing_status="done")

        def create_source(
            self,
            subject_id,
            source_type,
            external_source,
            title,
            language,
            status,
            processing_status=None,
        ):
            # ensure source_type is a value the use case can handle
            val = (
                source_type.value if hasattr(source_type, "value") else str(source_type)
            )
            src = SimpleNamespace(
                id=uuid.uuid4(),
                source_type=val,
                external_source=external_source,
                processing_status=processing_status or "pending",
            )
            self.created = src
            return src

        def update_processing_status(self, content_source_id, status):
            # noop for tests
            return None

        def finish_ingestion(
            self, content_source_id, embedding_model, dimensions, chunks, **kwargs
        ):
            # noop for tests
            return None

    return CS()


def make_ingestion_service():
    class IS:
        def create_job(
            self, content_source_id, status, embedding_model, pipeline_version, **kwargs
        ):
            return SimpleNamespace(id=uuid.uuid4(), content_source_id=content_source_id)

        def update_job(self, job_id, status, error_message=None, **kwargs):
            # noop for tests
            return None

        def link_job_to_source(self, job_id, content_source_id, ingestion_type=None):
            # noop for tests
            return None

        def get_by_id(self, id):
            return SimpleNamespace(id=id, content_source_id=None)

    return IS()


def make_model_loader():
    return SimpleNamespace(model_name="test-model", dimensions=768)


def make_chunk_service():
    class ChunkSvc:
        def __init__(self):
            self.chunks_created = None

        def create_chunks(self, chunks):
            self.chunks_created = chunks

    return ChunkSvc()


def make_vector_service():
    class VecSvc:
        def index_documents(self, chunks):
            return [str(uuid.uuid4()) for _ in chunks]

    return VecSvc()


def test_ingest_single_url_processes_chunks(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service(existing=False)
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    embedding = None
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()

    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc, "weaviate"
    )

    docs = [
        DummyDoc("chunk1", {"start": 0, "end": 10}),
        DummyDoc("chunk2", {"start": 10, "end": 20}),
    ]
    # patch instance methods
    monkeypatch.setattr(
        use_case, "_extract_video_id_from_url", lambda url: "dQw4w9WgXcQ"
    )
    monkeypatch.setattr(
        use_case, "_extract_and_split", lambda cmd, video_id, yt_extractor=None: docs
    )

    cmd = IngestYoutubeCommand(
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        subject_name="s",
        send_transcript=False,
    )
    result = use_case.execute(cmd)

    assert len(result.video_results) == 1
    assert result.created_chunks == 2
    assert len(result.vector_ids) == 2
    assert chunk_svc.chunks_created is not None
    assert chunk_svc.chunks_created[0].content == "chunk1"


def test_ingest_skips_existing_source(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service(existing=True)
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    embedding = None
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc, "weaviate"
    )
    monkeypatch.setattr(
        use_case, "_extract_video_id_from_url", lambda url: "dQw4w9WgXcQ"
    )
    cmd = IngestYoutubeCommand(video_url="dQw4w9WgXcQ", subject_name="s")
    result = use_case.execute(cmd)
    assert result.video_results[0]["skipped"] is True
    assert result.video_results[0]["reason"] == "source_exists_and_done"
    assert chunk_svc.chunks_created is None


def test_ingest_multi_video_one_fails_others_continue(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    embedding = None
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc, "weaviate"
    )

    def mock_extract_id(url):
        if "fail" in url:
            return None
        return "valid_id_" + url[-5:]

    monkeypatch.setattr(use_case, "_extract_video_id_from_url", mock_extract_id)
    monkeypatch.setattr(
        use_case, "_extract_and_split", lambda *args, **kwargs: [DummyDoc("content")]
    )

    cmd = IngestYoutubeCommand(
        video_urls=[
            "https://youtube.com/watch?v=fail1",
            "https://youtube.com/watch?v=work1",
        ],
        subject_name="s",
    )
    result = use_case.execute(cmd)

    assert len(result.video_results) == 2
    assert "error" in result.video_results[0]
    assert result.video_results[1]["video_id"] == "valid_id_work1"
    assert result.created_chunks == 1


def test_ingest_playlist(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    embedding = None
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc, "weaviate"
    )

    from src.application.dtos.enums.youtube_data_type import YoutubeDataType
    from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

    monkeypatch.setattr(
        YoutubeExtractor, "extract_playlist_videos", lambda url: ["url1", "url2"]
    )
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: url)
    monkeypatch.setattr(
        use_case, "_extract_and_split", lambda *args, **kwargs: [DummyDoc("content")]
    )

    cmd = IngestYoutubeCommand(
        video_url="https://youtube.com/playlist?list=PL123",
        subject_name="s",
        data_type=YoutubeDataType.PLAYLIST,
    )
    result = use_case.execute(cmd)

    assert len(result.video_results) == 2
    assert result.created_chunks == 2


def test_ingest_playlist_empty_raises(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, None, None, None, "weaviate"
    )

    from src.application.dtos.enums.youtube_data_type import YoutubeDataType
    from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

    monkeypatch.setattr(YoutubeExtractor, "extract_playlist_videos", lambda url: [])

    cmd = IngestYoutubeCommand(
        video_url="https://youtube.com/playlist?list=empty",
        subject_name="s",
        data_type=YoutubeDataType.PLAYLIST,
    )
    with pytest.raises(ValueError, match="No videos found in playlist"):
        use_case.execute(cmd)


def test_url_extraction_logic():
    from src.application.use_cases.youtube_ingestion_use_case import (
        YoutubeIngestionUseCase,
    )

    extract = YoutubeIngestionUseCase._extract_video_id_from_url

    assert extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract("https://www.youtube.com/v/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract(None) is None
    assert extract("") is None


def test_resolve_subject_errors(monkeypatch):
    ks = make_ks_service()
    # Mock KS to return None for unknown
    monkeypatch.setattr(ks, "get_by_name", lambda name: None)
    monkeypatch.setattr(ks, "get_subject_by_id", lambda id: None)

    use_case = YoutubeIngestionUseCase(
        ks, None, None, None, None, None, None, "weaviate"
    )

    cmd_name = IngestYoutubeCommand(video_url="v", subject_name="unknown")
    with pytest.raises(
        ValueError, match="KnowledgeSubject with name 'unknown' not found"
    ):
        use_case.execute(cmd_name)

    cmd_id = IngestYoutubeCommand(video_url="v", subject_id=uuid.uuid4())
    with pytest.raises(ValueError, match="KnowledgeSubject with id .* not found"):
        use_case.execute(cmd_id)

    cmd_none = IngestYoutubeCommand(video_url="v")
    with pytest.raises(
        ValueError, match="Either subject_id or subject_name must be provided"
    ):
        use_case.execute(cmd_none)


def test_ingest_fails_to_create_job(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    monkeypatch.setattr(isvc, "create_job", lambda **kwargs: None)

    model_loader = make_model_loader()
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, None, chunk_svc, vec_svc, "weaviate"
    )
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "vid")

    cmd = IngestYoutubeCommand(video_url="vid", subject_name="s")
    with pytest.raises(ValueError, match="Failed to create or retrieve ingestion job"):
        use_case.execute(cmd)


def test_ingest_fails_no_transcript(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    model_loader = make_model_loader()
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, None, chunk_svc, vec_svc, "weaviate"
    )

    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "vid")
    monkeypatch.setattr(use_case, "_extract_and_split", lambda *args, **kwargs: [])

    cmd = IngestYoutubeCommand(video_url="vid", subject_name="s")
    with pytest.raises(ValueError, match="No transcript chunks generated"):
        use_case.execute(cmd)


def test_ingest_with_pre_created_job(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()
    job_id = uuid.uuid4()

    # Mock IS to return a pre-created job
    monkeypatch.setattr(
        isvc, "get_by_id", lambda id: SimpleNamespace(id=id, content_source_id=None)
    )

    model_loader = make_model_loader()
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, None, chunk_svc, vec_svc, "weaviate"
    )
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "vid")
    monkeypatch.setattr(
        use_case, "_extract_and_split", lambda *args, **kwargs: [DummyDoc("content")]
    )

    cmd = IngestYoutubeCommand(
        video_url="vid", subject_name="s", ingestion_job_id=str(job_id)
    )
    result = use_case.execute(cmd)
    assert len(result.video_results) == 1
    assert result.video_results[0].get("skipped") is not True


def test_resolve_subject_by_id(monkeypatch):
    ks = make_ks_service()
    subject_id = uuid.uuid4()
    subject = SimpleNamespace(id=subject_id, name="subject_by_id")
    monkeypatch.setattr(
        ks, "get_subject_by_id", lambda id: subject if id == subject_id else None
    )

    use_case = YoutubeIngestionUseCase(
        ks, None, None, None, None, None, None, "weaviate"
    )

    # Test valid UUID object
    cmd = IngestYoutubeCommand(video_url="v", subject_id=subject_id)
    resolved = use_case._resolve_subject(cmd)
    assert resolved.id == subject_id

    # Test valid UUID string
    cmd_str = IngestYoutubeCommand(video_url="v", subject_id=str(subject_id))
    resolved_str = use_case._resolve_subject(cmd_str)
    assert resolved_str.id == subject_id


def test_execute_exception_recovery(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()

    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    # Mock recovery
    monkeypatch.setattr(
        isvc,
        "get_by_id",
        lambda id: SimpleNamespace(id=id, content_source_id=source_id),
    )

    use_case = YoutubeIngestionUseCase(ks, cs, isvc, None, None, None, None, "weaviate")

    # Force error in _resolve_subject
    def mock_error(*args, **kwargs):
        raise ValueError("Subject error")

    monkeypatch.setattr(use_case, "_resolve_subject", mock_error)

    cmd = IngestYoutubeCommand(video_url="v", subject_name="s", ingestion_job_id=job_id)
    with pytest.raises(ValueError, match="Subject error"):
        use_case.execute(cmd)


def test_process_single_video_with_existing_but_not_done_source(monkeypatch):
    ks = make_ks_service()
    cs = make_cs_service()
    isvc = make_ingestion_service()

    # Mock existing source that is NOT done
    existing_source = SimpleNamespace(
        id=uuid.uuid4(),
        processing_status="failed",
        source_type="youtube",
        external_source="vid",
    )
    monkeypatch.setattr(cs, "get_by_source_info", lambda **kwargs: existing_source)

    model_loader = make_model_loader()
    chunk_svc = make_chunk_service()
    vec_svc = make_vector_service()
    use_case = YoutubeIngestionUseCase(
        ks, cs, isvc, model_loader, None, chunk_svc, vec_svc, "weaviate"
    )

    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "vid")
    monkeypatch.setattr(
        use_case, "_extract_and_split", lambda *args, **kwargs: [DummyDoc("content")]
    )

    cmd = IngestYoutubeCommand(video_url="vid", subject_name="s")
    result = use_case.execute(cmd)
    assert result.video_results[0].get("skipped") is not True
    assert result.video_results[0]["source_id"] == existing_source.id


def test_url_extraction_edge_cases():
    from src.application.use_cases.youtube_ingestion_use_case import (
        YoutubeIngestionUseCase,
    )

    extract = YoutubeIngestionUseCase._extract_video_id_from_url

    # Test regex fallback for 11 chars
    assert extract("Some random text with dQw4w9WgXcQ inside") == "dQw4w9WgXcQ"
    # Test youtube.com path parts
    assert extract("https://youtube.com/v/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # Test no match
    assert extract("too_short") is None
