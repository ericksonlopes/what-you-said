from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import desc

from src.config.logger import Logger
from src.infrastructure.connectors.connector_sql import Connector
from src.infrastructure.repositories.sql.models.chunk_duplicate import ChunkDuplicateModel
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
from src.infrastructure.repositories.sql.utils.utils import ensure_uuid

logger = Logger()

class ChunkDuplicateSQLRepository:
    """Repository for managing duplicate chunk records in SQL."""

    def create_duplicate_record(
        self,
        chunk_ids: List[UUID],
        similarity: float,
        status: str = "pending",
        content_source_id: Optional[str] = None
    ) -> ChunkDuplicateModel:
        """Create a new duplicate grouping record."""
        with Connector() as session:
            try:
                record = ChunkDuplicateModel(
                    chunk_ids=[str(cid) for cid in chunk_ids],
                    similarity=similarity,
                    status=status,
                    content_source_id=content_source_id
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error creating duplicate record",
                    context={"error": str(e)}
                )
                raise

    def list_duplicates(
        self,
        status: Optional[str] = None,
        subject_ids: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[ChunkDuplicateModel], int]:
        """List duplicate records with optional status and context filtering."""
        with Connector() as session:
            query = session.query(ChunkDuplicateModel)
            
            if subject_ids:
                # Convert string IDs to UUID objects for safe matching in SQL
                parsed_ids = [UUID(sid) for sid in subject_ids]
                query = query.join(
                    ContentSourceModel,
                    ContentSourceModel.id == ChunkDuplicateModel.content_source_id
                ).filter(ContentSourceModel.subject_id.in_(parsed_ids))
            
            if status:
                query = query.filter(ChunkDuplicateModel.status == status)
            
            total = query.count()
            items = query.order_by(desc(ChunkDuplicateModel.created_at)).limit(limit).offset(offset).all()
            return items, total

    def get_by_id(self, duplicate_id: Any) -> Optional[ChunkDuplicateModel]:
        """Fetch a duplicate record by its UUID."""
        duplicate_id = ensure_uuid(duplicate_id)
        with Connector() as session:
            return session.query(ChunkDuplicateModel).filter_by(id=duplicate_id).first()

    def update_status(self, duplicate_id: Any, status: str) -> bool:
        """Update the status of a duplicate record."""
        duplicate_id = ensure_uuid(duplicate_id)
        with Connector() as session:
            try:
                record = session.query(ChunkDuplicateModel).filter_by(id=duplicate_id).first()
                if record:
                    record.status = status
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error updating duplicate status",
                    context={"duplicate_id": str(duplicate_id), "error": str(e)}
                )
                raise

    def delete_record(self, duplicate_id: Any) -> bool:
        """Delete a duplicate record."""
        duplicate_id = ensure_uuid(duplicate_id)
        with Connector() as session:
            try:
                record = session.query(ChunkDuplicateModel).filter_by(id=duplicate_id).first()
                if record:
                    session.delete(record)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error deleting duplicate record",
                    context={"duplicate_id": str(duplicate_id), "error": str(e)}
                )
                raise
