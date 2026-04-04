from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_diarization_command import IngestDiarizationCommand
from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.diarization_repository import DiarizationRepository
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.chunk_vector_service import ChunkVectorService
from src.infrastructure.services.text_splitter_service import TextSplitterService
from src.domain.interfaces.services.i_event_bus import IEventBus

logger = Logger()


class DiarizationIngestionUseCase:
    """Orchestrates ingestion of diarization results directly from the database."""

    def __init__(
        self,
        diarization_repo: DiarizationRepository,
        ks_service: KnowledgeSubjectService,
        cs_service: ContentSourceService,
        ingestion_service: IngestionJobService,
        model_loader_service: ModelLoaderService,
        embedding_service: EmbeddingService,
        chunk_service: ChunkIndexService,
        vector_service: ChunkVectorService,
        vector_store_type: str,
        event_bus: IEventBus,
    ) -> None:
        self.diarization_repo = diarization_repo
        self.ks_service = ks_service
        self.cs_service = cs_service
        self.ingestion_service = ingestion_service
        self.model_loader_service = model_loader_service
        self.embedding_service = embedding_service
        self.chunk_service = chunk_service
        self.vector_service = vector_service
        self.vector_store_type = vector_store_type
        self.event_bus = event_bus

    def execute(self, cmd: IngestDiarizationCommand) -> Dict[str, Any]:
        self.event_bus.publish(
            "ingestion_status",
            {
                "job_id": str(cmd.ingestion_job_id) if cmd.ingestion_job_id else "new",
                "status": "started",
                "diarization_id": str(cmd.diarization_id),
            },
        )
        logger.info(
            "Starting Diarization ingestion",
            context={
                "diarization_id": str(cmd.diarization_id),
                "subject_id": str(cmd.subject_id),
            },
        )

        ingestion = None
        source = None

        try:
            # 1. Fetch Diarization Record
            record = self.diarization_repo.get_by_id(str(cmd.diarization_id))
            if not record:
                raise ValueError(f"Diarization record not found: {cmd.diarization_id}")

            subject = self.ks_service.get_subject_by_id(cmd.subject_id)
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_id}")

            # 2. Determine Source Info
            # If it's a YouTube video, the external_source should be the URL
            # If it was an upload, it might be an S3 path or filename
            source_type_val = record.source_type
            if source_type_val == "upload":
                # Map 'upload' to 'audio' or 'video' if appropriate, or keep as is if supported
                source_type = SourceType.AUDIO 
            else:
                try:
                    source_type = SourceType(source_type_val.lower())
                except ValueError:
                    source_type = SourceType.OTHER

            external_source = record.external_source
            # Prefer original URL from metadata if available (for YouTube)
            if record.source_metadata and isinstance(record.source_metadata, dict):
                external_source = record.source_metadata.get("original_url") or external_source

            # 3. Create or retrieve Ingestion Job
            if cmd.ingestion_job_id:
                ingestion = self.ingestion_service.get_by_id(cmd.ingestion_job_id)

            if ingestion is None:
                ingestion = self.ingestion_service.create_job(
                    content_source_id=None,
                    status=IngestionJobStatus.STARTED,
                    embedding_model=self.model_loader_service.model_name,
                    pipeline_version="1.0",
                    ingestion_type=f"diarization_{source_type.value}",
                    vector_store_type=self.vector_store_type,
                    external_source=external_source,
                    subject_id=subject.id,
                )

            # 4. Format Transcript
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Formatting transcript from diarization...",
                current_step=1,
                total_steps=4,
            )

            full_text = self._format_transcript(record.segments, record.recognition_results)
            if not full_text:
                raise ValueError("No segments found in diarization record")

            # 5. Create or Get Source
            source = self.cs_service.get_by_source_info(
                source_type=source_type,
                external_source=external_source,
                subject_id=subject.id,
            )

            display_title = cmd.title or record.title or "Transcrição"

            if not source:
                source = self.cs_service.create_source(
                    subject_id=subject.id,
                    source_type=source_type,
                    external_source=external_source,
                    status=ContentSourceStatus.PROCESSING,
                    title=display_title,
                    language=cmd.language,
                    source_metadata=record.source_metadata,
                )
            else:
                # Update status
                self.cs_service.update_processing_status(
                    source.id, ContentSourceStatus.PROCESSING
                )

                # Reprocessing cleanup if requested
                if cmd.reprocess:
                    self.chunk_service.delete_by_content_source(source.id)
                    self.vector_service.delete(filters={"content_source_id": str(source.id)})

            # 6. Generate chunks and Embeddings
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Generating embeddings...",
                current_step=2,
                total_steps=4,
                content_source_id=source.id,
            )

            tokenizer = (
                self.model_loader_service.model.tokenizer
                if hasattr(self.model_loader_service, "model")
                and hasattr(self.model_loader_service.model, "tokenizer")
                else None
            )

            base_metadata = {
                "source": external_source,
                "title": display_title,
                "source_type": source_type.value,
                "diarization_id": str(cmd.diarization_id),
            }
            if record.source_metadata:
                base_metadata.update(record.source_metadata)

            if tokenizer:
                splitter_service = TextSplitterService(tokenizer=tokenizer)
                split_docs = splitter_service.split_text(
                    text=full_text,
                    tokens_per_chunk=cmd.tokens_per_chunk,
                    tokens_overlap=cmd.tokens_overlap,
                    metadata=base_metadata,
                )
            else:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                langchain_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=cmd.tokens_per_chunk * 4,
                    chunk_overlap=cmd.tokens_overlap * 4,
                )
                full_doc = Document(page_content=full_text, metadata=base_metadata)
                split_docs = langchain_splitter.split_documents([full_doc])

            # 7. Build and Persist Chunks
            chunks = self._build_chunk_entities(
                split_docs, source, subject, cmd, ingestion.id
            )
            self.chunk_service.create_chunks(chunks)

            # 8. Index in Vector Store
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Indexing in vector store...",
                current_step=3,
                total_steps=4,
            )
            
            self.vector_service.index_documents(chunks)

            # 9. Finalize
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.FINISHED,
                status_message="Ingestion complete",
                current_step=4,
                total_steps=4,
                chunks_count=len(chunks),
            )
            
            total_tokens = sum(c.tokens_count for c in chunks if c.tokens_count is not None)
            dims = getattr(self.model_loader_service, "dimensions", 0)
            
            self.cs_service.finish_ingestion(
                content_source_id=source.id,
                embedding_model=self.model_loader_service.model_name,
                dimensions=int(dims) if dims else 0,
                chunks=len(chunks),
                total_tokens=total_tokens,
                max_tokens_per_chunk=cmd.tokens_per_chunk,
                source_metadata=base_metadata,
            )

            return {
                "diarization_id": str(cmd.diarization_id),
                "created_chunks": len(chunks),
                "source_id": source.id,
                "job_id": ingestion.id,
            }

        except Exception as e:
            logger.error(e, context={"action": "diarization_ingestion_execute"})
            if ingestion:
                self.ingestion_service.update_job(
                    job_id=ingestion.id,
                    status=IngestionJobStatus.FAILED,
                    error_message=str(e),
                )
            raise

    def _format_transcript(self, segments: List[Dict[str, Any]], recognition: Optional[Dict[str, Any]]) -> str:
        if not segments:
            return ""
        
        mapping = {}
        if recognition and "mapping" in recognition:
            mapping = recognition["mapping"]
            
        lines = []
        for seg in segments:
            speaker_label = seg.get("speaker", "UNKNOWN")
            speaker_name = mapping.get(speaker_label, speaker_label)
            
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            
            def format_time(seconds: float) -> str:
                m, s = divmod(int(seconds), 60)
                h, m = divmod(m, 60)
                if h > 0:
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"
            
            timestamp = f"[{format_time(start)} - {format_time(end)}]"
            lines.append(f"{timestamp} {speaker_name}: {seg.get('text', '').strip()}")
            
        return "\n".join(lines)

    def _build_chunk_entities(
        self,
        docs: List[Document],
        source: Any,
        subject: Any,
        cmd: IngestDiarizationCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        chunks = []
        for i, doc in enumerate(docs):
            chunk = ChunkEntity(
                content_source_id=source.id,
                job_id=job_id,
                index=i,
                content=doc.page_content,
                tokens_count=doc.metadata.get("tokens_count", 0),
                language=cmd.language,
                source_type=source.source_type,
                subject_id=subject.id,
                external_source=source.external_source,
                extra={
                    **doc.metadata,
                    "vector_store_type": self.vector_store_type,
                },
            )
            chunks.append(chunk)
        return chunks
