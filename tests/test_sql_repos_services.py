from uuid import uuid4, UUID

import pytest

from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.content_source_status_enum import ContentSourceStatus
from src.domain.entities.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
from src.infrastructure.repositories.sql.knowledge_subject_repository import KnowledgeSubjectSQLRepository
from src.infrastructure.repositories.sql.query_log_repository import QueryLogSQLRepository
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService


@pytest.mark.usefixtures("sqlite_memory")
def test_sql_repositories_and_services():
    # KnowledgeSubject repository CRUD
    ks_repo = KnowledgeSubjectSQLRepository()
    ks_id = ks_repo.create_subject(name="KS1", external_ref="ext-ks1", description="desc1")
    assert isinstance(ks_id, UUID)

    ks_model = ks_repo.get_by_id(ks_id)
    assert ks_model is not None
    assert ks_model.name == "KS1"

    # ContentSource repository
    cs_repo = ContentSourceSQLRepository()
    cs_id = cs_repo.create(subject_id=ks_id, source_type=SourceType.YOUTUBE.value, external_source="video1",
                           title="Video 1", language="en", status="active", chunks=0)
    assert isinstance(cs_id, UUID)

    cs_model = cs_repo.get_by_id(cs_id)
    assert cs_model is not None
    assert cs_model.external_source == "video1"

    cs_repo.update_status(cs_id, "processing")
    cs_updated = cs_repo.get_by_id(cs_id)
    assert cs_updated.processing_status == "processing"

    cs_repo.finish_ingestion(cs_id, embedding_model="m", dimensions=384, chunks=10)
    cs_finished = cs_repo.get_by_id(cs_id)
    assert cs_finished.embedding_model == "m"
    assert cs_finished.dimensions == 384
    assert cs_finished.chunks == 10
    assert cs_finished.processing_status == ContentSourceStatus.DONE.value

    # IngestionJob repository
    job_repo = IngestionJobSQLRepository()
    job_id = job_repo.create_job(content_source_id=cs_id, status=IngestionJobStatus.STARTED.value, embedding_model="m",
                                 pipeline_version="v1")
    assert isinstance(job_id, UUID)

    job_model = job_repo.get_by_id(job_id)
    assert job_model is not None
    assert job_model.content_source_id == cs_id

    # ChunkIndex repository
    chunk_repo = ChunkIndexSQLRepository()
    chunk_id = uuid4()
    created_ids = chunk_repo.create_chunks([
        {"id": chunk_id, "content_source_id": cs_id, "job_id": job_id, "chunk_id": "chunk-1", "chars": 50,
         "language": "en", "version_number": 1}
    ])
    assert len(created_ids) == 1

    listed = chunk_repo.list_by_content_source(cs_id)
    assert len(listed) == 1

    search_res = chunk_repo.search(query="video1")
    assert len(search_res) == 1

    deleted_count = chunk_repo.delete_by_content_source(cs_id)
    assert deleted_count == 1
    assert len(chunk_repo.list_by_content_source(cs_id)) == 0

    # QueryLog repository
    q_repo = QueryLogSQLRepository()
    qid = q_repo.create_log(subject_id=ks_id, query_text="find", top_k=5, latency_ms=20)
    assert isinstance(qid, UUID)

    # Services
    ks_service = KnowledgeSubjectService(KnowledgeSubjectSQLRepository())
    entity = ks_service.create_subject(name="KS2")
    assert entity.name == "KS2"

    cs_service = ContentSourceService(ContentSourceSQLRepository())
    cs_entity = cs_service.create_source(subject_id=entity.id, source_type=SourceType.YOUTUBE, external_source="video2",
                                         status=ContentSourceStatus.ACTIVE)
    assert cs_entity.external_source == "video2"

    ingestion_service = IngestionJobService(IngestionJobSQLRepository())
    job_entity = ingestion_service.create_job(content_source_id=cs_entity.id)
    assert job_entity.content_source_id == cs_entity.id

    chunk_service = ChunkIndexService(ChunkIndexSQLRepository())
    chunk_entity = ChunkEntity(job_id=job_entity.id, content_source_id=cs_entity.id, source_type=SourceType.YOUTUBE,
                               external_source="video2", subject_id=entity.id, content="hello")
    created = chunk_service.create_chunks([chunk_entity])
    assert len(created) == 1

    lst = chunk_service.list_by_content_source(cs_entity.id)
    assert isinstance(lst, list)
    # content for chunk index rows is stored in the vector store; SQL mapper leaves content as None
    assert all(c.content is None for c in lst)
