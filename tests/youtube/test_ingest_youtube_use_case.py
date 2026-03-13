import uuid
from types import SimpleNamespace

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.use_cases.ingest_youtube_use_case import IngestYoutubeUseCase


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

        def get_by_source_info(self, source_type, external_source):
            return SimpleNamespace(id=uuid.uuid4()) if existing else None

        def create_source(self, subject_id, source_type, external_source, title, language, status):
            # ensure source_type is a value the use case can handle
            val = source_type.value if hasattr(source_type, "value") else str(source_type)
            src = SimpleNamespace(id=uuid.uuid4(), source_type=val, external_source=external_source)
            self.created = src
            return src

        def update_processing_status(self, content_source_id, status):
            # noop for tests
            return None

        def finish_ingestion(self, content_source_id, embedding_model, dimensions, chunks):
            # noop for tests
            return None


    return CS()


def make_ingestion_service():
    class IS:
        def create_job(self, content_source_id, status, embedding_model, pipeline_version):
            return SimpleNamespace(id=uuid.uuid4())

        def update_job(self, job_id, status):
            # noop for tests
            return None


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

    use_case = IngestYoutubeUseCase(ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc)

    docs = [DummyDoc("chunk1", {"start": 0, "end": 10}), DummyDoc("chunk2", {"start": 10, "end": 20})]
    # patch instance methods
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "dQw4w9WgXcQ")
    monkeypatch.setattr(use_case, "_extract_and_split", lambda cmd, video_id: docs)

    cmd = IngestYoutubeCommand(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", subject_name="s",
                               send_transcript=False)
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
    use_case = IngestYoutubeUseCase(ks, cs, isvc, model_loader, embedding, chunk_svc, vec_svc)
    monkeypatch.setattr(use_case, "_extract_video_id_from_url", lambda url: "dQw4w9WgXcQ")
    cmd = IngestYoutubeCommand(video_url="dQw4w9WgXcQ", subject_name="s")
    result = use_case.execute(cmd)
    assert result.video_results[0]["skipped"] is True
    assert result.video_results[0]["reason"] == "source_exists"
    assert chunk_svc.chunks_created is None
