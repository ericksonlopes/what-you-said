from uuid import uuid4, UUID

import pytest

from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)
from src.infrastructure.repositories.sql.ingestion_job_repository import (
    IngestionJobSQLRepository,
)
from src.infrastructure.repositories.sql.knowledge_subject_repository import (
    KnowledgeSubjectSQLRepository,
)
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)


@pytest.mark.usefixtures("sqlite_memory")
def test_more_sql_paths():
    # setup repos/services
    ks_repo = KnowledgeSubjectSQLRepository()
    cs_repo = ContentSourceSQLRepository()
    job_repo = IngestionJobSQLRepository()
    chunk_repo = ChunkIndexSQLRepository()

    # create a subject and exercise get_by_external_ref, list, get_by_name
    ks_id = ks_repo.create_subject(
        name="KS_extra", external_ref="external-extra", description="d"
    )
    found_by_ext = ks_repo.get_by_external_ref("external-extra")
    assert found_by_ext is not None

    listed = ks_repo.list(limit=10)
    assert isinstance(listed, list)

    by_name = ks_repo.get_by_name("KS_extra")
    assert by_name is not None

    # update subject
    ks_repo.update(ks_id, name="KS_extra2", description="d2", external_ref="external2")
    updated = ks_repo.get_by_id(ks_id)
    assert updated.name == "KS_extra2"

    # delete subject
    deleted = ks_repo.delete(ks_id)
    assert deleted == 1
    assert ks_repo.get_by_id(ks_id) is None

    # ContentSource: create and test list_by_subject and get_by_source_info
    ks_id2 = ks_repo.create_subject(name="KS_for_cs")
    cs_id = cs_repo.create(
        subject_id=ks_id2,
        source_type=SourceType.YOUTUBE.value,
        external_source="v_extra",
        title="t",
        language="en",
    )
    by_source = cs_repo.get_by_source_info(
        source_type=SourceType.YOUTUBE.value, external_source="v_extra"
    )
    assert isinstance(by_source, list) and len(by_source) >= 1

    by_subject = cs_repo.list_by_subject(ks_id2)
    assert isinstance(by_subject, list) and len(by_subject) >= 1

    # call update_status for non-existing id to hit warning branch
    cs_repo.update_status(UUID(int=0), "processing")

    # finish_ingestion for non-existing id too
    cs_repo.finish_ingestion(UUID(int=0), embedding_model="m", dimensions=1, chunks=1)

    # create ingestion job and list_by_content_source
    job_id = job_repo.create_job(
        content_source_id=cs_id, status=IngestionJobStatus.STARTED.value
    )
    jobs = job_repo.list_by_content_source(cs_id)
    assert isinstance(jobs, list)

    # update non-existent job to hit not-found branch
    job_repo.update_job(
        UUID(int=0), status=IngestionJobStatus.FAILED.value, error_message="err"
    )

    # chunk_index: create and search with filters
    chunk_id = uuid4()
    created = chunk_repo.create_chunks(
        [
            {
                "id": chunk_id,
                "content_source_id": cs_id,
                "job_id": job_id,
                "chunk_id": "filter-chunk",
                "chars": 1,
            }
        ]
    )
    assert len(created) == 1

    # Search using a filter on the joined ContentSource column (external_source)
    res = chunk_repo.search(query=None, filters={"external_source": "v_extra"})
    assert isinstance(res, list)
    assert len(res) >= 1

    # cleanup delete
    deleted_chunks = chunk_repo.delete_by_content_source(cs_id)
    assert isinstance(deleted_chunks, int)


@pytest.mark.usefixtures("sqlite_memory")
def test_services_paths():
    ks_service = KnowledgeSubjectService(KnowledgeSubjectSQLRepository())
    cs_service = ContentSourceService(ContentSourceSQLRepository())
    ingestion_service = IngestionJobService(IngestionJobSQLRepository())
    chunk_service = ChunkIndexService(ChunkIndexSQLRepository())

    # create subject via service and get_or_create behavior
    subj = ks_service.create_subject(name="svc-ks", external_ref="svc-ex")
    assert subj.name == "svc-ks"

    same = ks_service.get_or_create_by_external_ref("svc-ex")
    assert same.id == subj.id

    # list subjects
    subs = ks_service.list_subjects(limit=5)
    assert isinstance(subs, list)

    # update/delete via service
    ks_service.update_subject(subj.id, name="svc-upd")
    ks_service.delete_subject(subj.id)

    # create content source via service and use other methods
    cs = cs_service.create_source(
        subject_id=None,
        source_type=SourceType.YOUTUBE,
        external_source="svc-video",
        status=ContentSourceStatus.ACTIVE,
    )
    got = cs_service.get_by_source_info(SourceType.YOUTUBE, "svc-video")
    assert got is not None
    _ = cs_service.get_by_id(cs.id)

    lst = cs_service.list_by_subject(cs.subject_id) if cs.subject_id else []
    assert isinstance(lst, list)

    cs_service.update_processing_status(cs.id, ContentSourceStatus.PROCESSING)
    cs_service.finish_ingestion(cs.id, embedding_model="m", dimensions=10, chunks=2)

    # ingestion service update and get
    job = ingestion_service.create_job(content_source_id=cs.id)
    ingestion_service.update_job(job.id, IngestionJobStatus.FINISHED)
    got_job = ingestion_service.get_by_id(job.id)
    assert got_job is not None

    # chunk service create and search
    from src.domain.entities.chunk_entity import ChunkEntity

    chunk_entity = ChunkEntity(
        job_id=job.id,
        content_source_id=cs.id,
        source_type=SourceType.YOUTUBE,
        external_source="svc-video",
        subject_id=None,
        content=None,
    )
    created_ids = chunk_service.create_chunks([chunk_entity])
    assert isinstance(created_ids, list)

    search_res = chunk_service.search(query="svc-video")
    assert isinstance(search_res, list)
