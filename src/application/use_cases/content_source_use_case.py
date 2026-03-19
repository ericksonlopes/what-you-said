from uuid import UUID
from src.config.logger import Logger
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService

logger = Logger()


class ContentSourceUseCase:
    """
    Orchestrates the deletion of a ContentSource and all its related artifacts:
    1. Chunks from SQL (chunk_index table)
    2. Embeddings from Vector Store (FAISS, Weaviate, or Chroma)
    3. The primary ContentSource record
    """

    def __init__(
        self,
        cs_service: ContentSourceService,
        chunk_service: ChunkIndexService,
        vector_repo: IVectorRepository,
    ) -> None:
        self.cs_service = cs_service
        self.chunk_service = chunk_service
        self.vector_repo = vector_repo

    def delete(self, content_source_id: UUID) -> bool:
        logger.info(
            "Starting deletion of content source",
            context={"content_source_id": str(content_source_id)},
        )

        # 1. Verify existence
        source = self.cs_service.get_by_id(content_source_id)
        if not source:
            logger.warning(
                "Content source not found for deletion",
                context={"content_source_id": str(content_source_id)},
            )
            return False

        try:
            # 2. Delete Chunks from SQL
            sql_deleted = self.chunk_service.delete_by_content_source(content_source_id)
            logger.debug(
                "Deleted chunks from SQL",
                context={
                    "content_source_id": str(content_source_id),
                    "count": sql_deleted,
                },
            )

            # 3. Delete from Vector Store
            # We use a filter to target only this source's chunks
            filters = {"content_source_id": str(content_source_id)}
            vector_deleted = self.vector_repo.delete(filters=filters)
            logger.debug(
                "Deleted chunks from vector store",
                context={
                    "content_source_id": str(content_source_id),
                    "count": vector_deleted,
                },
            )

            # 4. Delete the Content Source record
            success = self.cs_service.delete_source(content_source_id)

            logger.info(
                "Content source and all related data deleted successfully",
                context={
                    "content_source_id": str(content_source_id),
                    "sql_deleted": sql_deleted,
                    "vector_deleted": vector_deleted,
                },
            )
            return success

        except Exception as e:
            logger.error(
                "Failed to delete content source",
                context={"content_source_id": str(content_source_id), "error": str(e)},
            )
            raise e
