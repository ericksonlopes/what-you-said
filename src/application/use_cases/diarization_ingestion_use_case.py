from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_diarization_command import (
    IngestDiarizationCommand,
)
from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.diarization_status_enum import DiarizationStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.chunk_vector_service import ChunkVectorService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.text_splitter_service import TextSplitterService

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
            record = self.diarization_repo.get_by_id(str(cmd.diarization_id))
            if not record:
                raise ValueError(f"Diarization record not found: {cmd.diarization_id}")

            subject = self.ks_service.get_subject_by_id(cmd.subject_id)
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_id}")

            source_type, external_source = self._resolve_source_info(record)

            if cmd.ingestion_job_id:
                ingestion = self.ingestion_service.get_by_id(cmd.ingestion_job_id)

            if ingestion is None:
                ingestion = self._create_ingestion_job(
                    external_source, source_type, subject.id
                )

            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Formatting transcript from diarization...",
                current_step=1,
                total_steps=4,
            )

            full_text = self._format_transcript(
                cast(list, record.segments), cast(dict, record.recognition_results)
            )
            if not full_text:
                raise ValueError("No segments found in diarization record")

            display_name = cmd.name or cast(str, record.name) or "Transcrição"
            source = self._get_or_create_source(
                source_type, external_source, subject.id, display_name, cmd, record
            )

            # Generate chunks and Embeddings
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Generating embeddings...",
                current_step=2,
                total_steps=4,
                content_source_id=source.id,
            )

            split_docs = self._generate_split_docs(
                full_text, display_name, external_source, source_type, cmd, record
            )

            # Persist Chunks
            chunks = self._build_chunk_entities(
                split_docs, source, subject, cmd, ingestion.id
            )
            self.chunk_service.create_chunks(chunks)

            # Index
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Indexing in vector store...",
                current_step=3,
                total_steps=4,
            )
            self.vector_service.index_documents(chunks)

            # Finalize
            self._finalize_ingestion(ingestion, source, chunks, cmd)

            # Update Diarization record status to COMPLETED
            self.diarization_repo.update_status(
                diarization_id=str(cmd.diarization_id),
                status=DiarizationStatus.COMPLETED.value,
                status_message="Ingestão concluída com sucesso",
                error_message="",  # Clear any previous error
            )

            # Notify frontend that diarization is fully done
            self.event_bus.publish(
                "ingestion_status",
                {
                    "type": "diarization",
                    "id": str(cmd.diarization_id),
                    "status": "done",
                    "message": "Diarização indexada com sucesso",
                },
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
            if source:
                self.cs_service.update_processing_status(
                    content_source_id=source.id,
                    status=ContentSourceStatus.FAILED,
                    error_message=str(e),
                )
            raise

    def _resolve_source_info(self, record: Any) -> tuple[SourceType, str]:
        source_type_val = cast(str, record.source_type)
        if source_type_val == "upload":
            source_type = SourceType.AUDIO
        else:
            try:
                source_type = SourceType(source_type_val.lower())
            except ValueError:
                source_type = SourceType.OTHER

        external_source = cast(str, record.external_source)
        if record.source_metadata and isinstance(record.source_metadata, dict):
            original = record.source_metadata.get("original_url")
            if original:
                external_source = original

        # Normalize YouTube IDs to prevent duplicates (Short URLs, Full URLs vs 11-char IDs)
        if source_type == SourceType.YOUTUBE:
            normalized_vid = YoutubeExtractor.get_video_id(external_source)
            if normalized_vid:
                external_source = normalized_vid

        return source_type, external_source

    def _create_ingestion_job(
        self, external_source: str, source_type: SourceType, subject_id: UUID
    ) -> Any:
        return self.ingestion_service.create_job(
            content_source_id=None,
            status=IngestionJobStatus.STARTED,
            embedding_model=self.model_loader_service.model_name,
            pipeline_version="1.0",
            ingestion_type=f"diarization_{source_type.value}",
            vector_store_type=self.vector_store_type,
            external_source=external_source,
            subject_id=subject_id,
        )

    def _get_or_create_source(
        self,
        source_type: SourceType,
        external_source: str,
        subject_id: UUID,
        display_title: str,
        cmd: IngestDiarizationCommand,
        record: Any,
    ) -> Any:
        source = self.cs_service.get_by_source_info(
            source_type=source_type,
            external_source=external_source,
            subject_id=subject_id,
        )

        if not source:
            source = self.cs_service.create_source(
                subject_id=subject_id,
                source_type=source_type,
                external_source=external_source,
                status=ContentSourceStatus.PROCESSING,
                title=display_title,
                language=cmd.language,
                source_metadata=cast(dict, record.source_metadata),
            )
        else:
            self.cs_service.update_processing_status(
                source.id, ContentSourceStatus.PROCESSING
            )
            # Update title if it has changed
            if cmd.name and source.title != cmd.name:
                self.cs_service.update_title(source.id, cmd.name)

            if cmd.reprocess:
                self.chunk_service.delete_by_content_source(source.id)
                self.vector_service.delete(
                    filters={"content_source_id": str(source.id)}
                )
        return source

    def _generate_split_docs(
        self,
        full_text: str,
        title: str,
        source: str,
        source_type: SourceType,
        cmd: IngestDiarizationCommand,
        record: Any,
    ) -> List[Document]:
        base_metadata = {
            "source": source,
            "title": title,
            "source_type": source_type.value,
            "diarization_id": str(cmd.diarization_id),
        }
        if record.source_metadata:
            base_metadata.update(record.source_metadata)

        tokenizer = getattr(self.model_loader_service, "model", None)
        tokenizer = getattr(tokenizer, "tokenizer", None) if tokenizer else None

        if tokenizer:
            splitter_service = TextSplitterService(tokenizer=tokenizer)
            return splitter_service.split_text(
                text=full_text,
                tokens_per_chunk=cmd.tokens_per_chunk,
                tokens_overlap=cmd.tokens_overlap,
                metadata=base_metadata,
            )

        from langchain_text_splitters import RecursiveCharacterTextSplitter

        langchain_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cmd.tokens_per_chunk * 4,
            chunk_overlap=cmd.tokens_overlap * 4,
        )
        full_doc = Document(page_content=full_text, metadata=base_metadata)
        return langchain_splitter.split_documents([full_doc])

    def _finalize_ingestion(
        self,
        ingestion: Any,
        source: Any,
        chunks: List[ChunkEntity],
        cmd: IngestDiarizationCommand,
    ) -> None:
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
            embedding_model=self.model_loader_service.model_name or "unknown",
            dimensions=int(dims) if dims else 0,
            chunks=len(chunks),
            total_tokens=total_tokens,
            max_tokens_per_chunk=cmd.tokens_per_chunk,
            source_metadata=source.source_metadata,
        )

    def _format_seconds(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _format_transcript(
        self, segments: List[Dict[str, Any]], recognition: Optional[Dict[str, Any]]
    ) -> str:
        if not segments:
            return ""

        mapping = recognition.get("mapping", {}) if recognition else {}

        merged_lines = []
        curr_speaker, curr_start, curr_end, curr_texts = None, None, None, []

        for seg in segments:
            spk_label = seg.get("speaker", "UNKNOWN")
            spk_name = mapping.get(spk_label, spk_label)
            start = float(seg.get("start", 0))
            end = float(seg.get("end", 0))
            text = seg.get("text", "").strip()

            if spk_name == curr_speaker:
                curr_end = end
                if text:
                    curr_texts.append(text)
            else:
                if curr_speaker is not None:
                    ts = f"[{self._format_seconds(cast(float, curr_start))} - {self._format_seconds(cast(float, curr_end))}]"
                    merged_lines.append(f"{ts} {curr_speaker}: {' '.join(curr_texts)}")

                curr_speaker, curr_start, curr_end, curr_texts = (
                    spk_name,
                    start,
                    end,
                    [text] if text else [],
                )

        if curr_speaker is not None:
            ts = f"[{self._format_seconds(cast(float, curr_start))} - {self._format_seconds(cast(float, curr_end))}]"
            merged_lines.append(f"{ts} {curr_speaker}: {' '.join(curr_texts)}")

        return "\n".join(merged_lines)

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
