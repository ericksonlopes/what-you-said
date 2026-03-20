import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.extractors.docling_extractor import DoclingExtractor
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

logger = Logger()


class FileIngestionUseCase:
    """Orchestrates ingestion of various file types using Docling."""

    def __init__(
        self,
        ks_service: KnowledgeSubjectService,
        cs_service: ContentSourceService,
        ingestion_service: IngestionJobService,
        model_loader_service: ModelLoaderService,
        embedding_service: EmbeddingService,
        chunk_service: ChunkIndexService,
        vector_service: ChunkVectorService,
        vector_store_type: str,
    ) -> None:
        self.ks_service = ks_service
        self.cs_service = cs_service
        self.ingestion_service = ingestion_service
        self.model_loader_service = model_loader_service
        self.embedding_service = embedding_service
        self.chunk_service = chunk_service
        self.vector_service = vector_service
        self.vector_store_type = vector_store_type
        self.extractor = DoclingExtractor()

    def execute(self, cmd: IngestFileCommand) -> Dict[str, Any]:
        logger.info(
            "Starting File ingestion",
            context={
                "file_name": cmd.file_name,
                "subject_id": str(cmd.subject_id) if cmd.subject_id else None,
            },
        )

        ingestion = None
        source = None

        try:
            subject = self._resolve_subject(cmd)
            source_type = self._determine_source_type(cmd.file_name)

            # 1. Create or retrieve Ingestion Job
            if cmd.ingestion_job_id:
                ingestion = self.ingestion_service.get_by_id(cmd.ingestion_job_id)

            if ingestion is None:
                ingestion = self.ingestion_service.create_job(
                    content_source_id=None,
                    status=IngestionJobStatus.STARTED,
                    embedding_model=self.model_loader_service.model_name,
                    pipeline_version="1.0",
                    ingestion_type=source_type.value,
                    vector_store_type=self.vector_store_type,
                    external_source=cmd.file_name,
                )

            # 2. Extract content
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message=f"Extracting content from {cmd.file_name}...",
                current_step=1,
                total_steps=4,
            )

            docs = self.extractor.extract(cmd.file_path)
            if not docs:
                raise ValueError(f"No content extracted from file {cmd.file_name}")

            # 3. Create ContentSource
            source = self.cs_service.create_source(
                subject_id=subject.id,
                source_type=source_type,
                external_source=cmd.file_name,
                title=cmd.title or cmd.file_name,
                language=cmd.language,
                status=ContentSourceStatus.ACTIVE,
                processing_status="processing",
            )

            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                content_source_id=source.id,
                status_message="Splitting content into chunks...",
                current_step=2,
                total_steps=4,
            )

            # 4. Split and Tokenize
            tokenizer = (
                self.model_loader_service.model.tokenizer
                if hasattr(self.model_loader_service, "model")
                and hasattr(self.model_loader_service.model, "tokenizer")
                else None
            )

            effective_tokens = cmd.tokens_per_chunk

            if tokenizer and docs:
                splitter_service = TextSplitterService(tokenizer=tokenizer)
                split_docs = splitter_service.split_text(
                    text=docs[0].page_content,
                    tokens_per_chunk=effective_tokens,
                    tokens_overlap=cmd.tokens_overlap,
                    metadata=docs[0].metadata,
                )
            elif docs:
                # Fallback to basic RecursiveCharacterTextSplitter if no tokenizer
                from langchain_text_splitters import RecursiveCharacterTextSplitter

                langchain_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=effective_tokens * 4,
                    chunk_overlap=cmd.tokens_overlap * 4,
                )
                split_docs = langchain_splitter.split_documents(docs)
            else:
                split_docs = []

            # 5. Build and Persist Chunks
            chunks = self._build_chunk_entities(
                split_docs, source, subject, cmd, ingestion.id
            )
            self.chunk_service.create_chunks(chunks)

            # 6. Index in Vector Store
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Generating embeddings and indexing...",
                current_step=3,
                total_steps=4,
            )

            created_ids = self.vector_service.index_documents(chunks)

            # 7. Finalize
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.FINISHED,
                status_message="Ingestion complete!",
                current_step=4,
                total_steps=4,
                chunks_count=len(chunks),
            )

            total_tokens = sum(
                c.tokens_count for c in chunks if c.tokens_count is not None
            )
            dims = getattr(self.model_loader_service, "dimensions", None)
            dims_val: int = int(dims) if dims is not None else 0

            max_tokens = cmd.tokens_per_chunk
            logger.info(
                f"FileIngestion: finishing with requested={cmd.tokens_per_chunk}, limit={self.model_loader_service.max_seq_length}, effective={max_tokens}",
                context={"source_id": str(source.id)},
            )

            self.cs_service.finish_ingestion(
                content_source_id=source.id,
                embedding_model=self.model_loader_service.model_name,
                dimensions=dims_val,
                chunks=len(chunks),
                total_tokens=total_tokens,
                max_tokens_per_chunk=max_tokens,
            )

            return {
                "file_name": cmd.file_name,
                "created_chunks": len(chunks),
                "vector_ids": created_ids,
                "source_id": source.id,
                "job_id": ingestion.id,
            }

        except Exception as e:
            logger.error(f"Error in FileIngestionUseCase: {e}")
            if ingestion:
                self.ingestion_service.update_job(
                    job_id=ingestion.id,
                    status=IngestionJobStatus.FAILED,
                    error_message=str(e),
                )
            if source:
                self.cs_service.update_processing_status(
                    content_source_id=source.id, status=ContentSourceStatus.FAILED
                )
            raise e

    def _resolve_subject(self, cmd: IngestFileCommand):
        if cmd.subject_id:
            subject = self.ks_service.get_subject_by_id(cmd.subject_id)
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_id}")
            return subject
        if cmd.subject_name:
            subject = self.ks_service.get_by_name(cmd.subject_name)
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_name}")
            return subject
        raise ValueError("Either subject_id or subject_name must be provided")

    def _determine_source_type(self, file_name: str) -> SourceType:
        ext = file_name.split(".")[-1].lower()
        try:
            return SourceType(ext)
        except ValueError:
            # Fallback for common types or generic ARTICLE if unknown
            if ext in ["doc", "docx"]:
                return SourceType.DOCX
            if ext in ["ppt", "pptx"]:
                return SourceType.PPTX
            if ext in ["xls", "xlsx"]:
                return SourceType.XLSX
            if ext in ["md", "markdown"]:
                return SourceType.MARKDOWN
            if ext in ["jpg", "jpeg", "png", "webp"]:
                return SourceType.IMAGE
            if ext == "txt":
                return SourceType.TXT
            return SourceType.OTHER  # Default fallback for unknown supported types

    def _build_chunk_entities(
        self,
        docs: List[Document],
        source,
        subject,
        cmd: IngestFileCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        list_chunks: List[ChunkEntity] = []

        # Try to get tokenizer for more accurate token counting
        tokenizer = None
        if hasattr(self.model_loader_service, "model") and hasattr(
            self.model_loader_service.model, "tokenizer"
        ):
            tokenizer = self.model_loader_service.model.tokenizer

        for i, doc in enumerate(docs):
            tokens_count = None
            if tokenizer:
                try:
                    # Some tokenizers might require specific encode calls
                    tokens = tokenizer.encode(
                        doc.page_content, add_special_tokens=False
                    )
                    tokens_count = len(tokens)
                except Exception:
                    try:
                        tokens = tokenizer.encode(doc.page_content)
                        tokens_count = len(tokens)
                    except Exception:
                        pass

            if tokens_count is None:
                tokens_count = len(doc.page_content) // 4  # Fallback approximation

            chunk_entity = ChunkEntity(
                id=uuid.uuid4(),
                job_id=job_id,
                content_source_id=source.id,
                source_type=SourceType(source.source_type),
                external_source=source.external_source,
                subject_id=subject.id,
                index=i,
                content=doc.page_content,
                tokens_count=tokens_count,
                extra={**doc.metadata, "vector_store_type": self.vector_store_type},
                language=cmd.language,
                embedding_model=self.model_loader_service.model_name,
                created_at=datetime.now(timezone.utc),
                version_number=1,
            )
            list_chunks.append(chunk_entity)
        return list_chunks
