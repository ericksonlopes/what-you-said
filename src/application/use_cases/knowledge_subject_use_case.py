from uuid import UUID
from src.config.logger import Logger
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.application.use_cases.content_source_use_case import ContentSourceUseCase

logger = Logger()


class KnowledgeSubjectUseCase:
    """
    Orchestrates the deletion of a KnowledgeSubject and all its related artifacts:
    1. Chunks from Vector Store (batch delete by subject_id)
    2. All ContentSources belonging to it (via ContentSourceUseCase to ensure SQL cleanup)
    3. The primary KnowledgeSubject record
    """

    def __init__(
        self,
        ks_service: KnowledgeSubjectService,
        cs_use_case: ContentSourceUseCase,
        vector_repo: IVectorRepository,
    ) -> None:
        self.ks_service = ks_service
        self.cs_use_case = cs_use_case
        self.vector_repo = vector_repo

    def delete_knowledge(self, subject_id: UUID) -> bool:
        logger.info(
            "Starting deletion of knowledge subject",
            context={"subject_id": str(subject_id)},
        )

        # 1. Verify existence
        subject = self.ks_service.get_subject_by_id(subject_id)
        if not subject:
            logger.warning(
                "Knowledge subject not found for deletion",
                context={"subject_id": str(subject_id)},
            )
            return False

        try:
            # 2. Delete from Vector Store (Batch for the whole subject)
            filters = {"subject_id": str(subject_id)}
            vector_deleted = self.vector_repo.delete(filters=filters)
            logger.debug(
                "Deleted chunks from vector store for subject",
                context={
                    "subject_id": str(subject_id),
                    "count": vector_deleted,
                },
            )

            # 3. Delete all ContentSources (includes SQL chunks, jobs, and the source itself)
            # Fetch all sources for this subject
            # We use cs_use_case.cs_service since it's already available
            sources = self.cs_use_case.cs_service.list_by_subject(subject_id)

            for source in sources:
                # We already cleaned the vector store for the whole subject,
                # but ContentSourceUseCase.delete also tries to delete from vector store.
                # This is fine (safe redundancy) as it ensures everything is gone.
                self.cs_use_case.delete(source.id)

            # 4. Finally, delete the KnowledgeSubject record
            # Note: At this point, content_sources should already be gone if not for the
            # direct SQL delete in the repository. But we call it anyway to be thorough.
            success = self.ks_service.delete_subject(subject_id)

            logger.info(
                "Knowledge subject and all related data deleted successfully",
                context={
                    "subject_id": str(subject_id),
                    "vector_deleted": vector_deleted,
                    "sources_count": len(sources),
                },
            )
            return bool(success)

        except Exception as e:
            logger.error(
                "Failed to delete knowledge subject",
                context={"subject_id": str(subject_id), "error": str(e)},
            )
            raise e
