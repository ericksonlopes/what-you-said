import os
import shutil
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
from src.infrastructure.extractors.plain_text_extractor import PlainTextExtractor
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
        event_bus: IEventBus,
    ) -> None:
        self.ks_service = ks_service
        self.cs_service = cs_service
        self.ingestion_service = ingestion_service
        self.model_loader_service = model_loader_service
        self.embedding_service = embedding_service
        self.chunk_service = chunk_service
        self.vector_service = vector_service
        self.vector_store_type = vector_store_type
        self.event_bus = event_bus
        self.extractor = DoclingExtractor()
        self.plain_text_extractor = PlainTextExtractor()

    def execute(self, cmd: IngestFileCommand) -> Dict[str, Any]:
        self.event_bus.publish(
            "ingestion_status",
            {
                "job_id": str(cmd.ingestion_job_id) if cmd.ingestion_job_id else "new",
                "status": "started",
                "file_name": cmd.file_name,
            },
        )
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
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "processing",
                    "step": "extracting",
                    "title": cmd.title or cmd.file_name,
                },
            )

            source_path = cmd.file_url or cmd.file_path
            if not source_path:
                raise ValueError(
                    "Neither file_path nor file_url provided for ingestion"
                )

            try:
                docs = self.extractor.extract(source_path, do_ocr=cmd.do_ocr)
            except Exception as e:
                error_str = str(e).lower()
                if "format not allowed" in error_str or "unsupported" in error_str:
                    logger.info(
                        "Docling does not support format, falling back to PlainTextExtractor",
                        context={"file_name": cmd.file_name},
                    )
                    docs = self.plain_text_extractor.extract(source_path)
                else:
                    # For other errors, re-raise
                    raise e

            if not docs:
                raise ValueError(f"No content extracted from file {cmd.file_name}")

            # Refine source_type based on actual extracted metadata if available
            extracted_ext = docs[0].metadata.get("source_type")
            docling_detected = docs[0].metadata.get("docling_source_type")

            logger.debug(
                "Attempting source_type refinement",
                context={
                    "extracted_ext": extracted_ext,
                    "docling_detected": docling_detected,
                    "current_source_type": source_type.value,
                },
            )

            # Prioritize Docling's specific detection if it's a known format
            to_try = [docling_detected, extracted_ext]
            for ext_str in to_try:
                if ext_str and isinstance(ext_str, str):
                    try:
                        refined = SourceType(ext_str.lower())
                        if refined != SourceType.OTHER:
                            source_type = refined
                            logger.info(
                                "Refined source_type",
                                context={
                                    "file_name": cmd.file_name,
                                    "source_type": source_type.value,
                                    "detected_ext": ext_str,
                                },
                            )
                            break
                    except ValueError:
                        pass

            # 3. Initialize Source Ingestion
            source = self.cs_service.get_by_source_info(
                source_type=source_type,
                external_source=cmd.file_name,
                subject_id=cmd.subject_id,
            )
            if not source:
                source = self.cs_service.create_source(
                    subject_id=subject.id,
                    source_type=source_type,
                    external_source=cmd.file_name,
                    status=ContentSourceStatus.PROCESSING,
                    title=cmd.title or cmd.file_name,
                    language=cmd.language,
                    source_metadata=docs[0].metadata,
                )

            # 4. Generate chunks and Embeddings
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message=f"Generating embeddings for {len(docs)} chunks...",
                current_step=2,
                total_steps=4,
                content_source_id=source.id,  # Link job to source in DB
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "processing",
                    "step": "embedding",
                    "chunks_count": len(docs),
                },
            )
            tokenizer = (
                self.model_loader_service.model.tokenizer
                if hasattr(self.model_loader_service, "model")
                and hasattr(self.model_loader_service.model, "tokenizer")
                else None
            )

            effective_tokens = cmd.tokens_per_chunk

            full_text = "\n\n".join([doc.page_content for doc in docs])
            base_metadata = docs[0].metadata if docs else {}

            if tokenizer and docs:
                splitter_service = TextSplitterService(tokenizer=tokenizer)
                split_docs = splitter_service.split_text(
                    text=full_text,
                    tokens_per_chunk=effective_tokens,
                    tokens_overlap=cmd.tokens_overlap,
                    metadata=base_metadata,
                )
            elif docs:
                # Fallback to basic RecursiveCharacterTextSplitter if no tokenizer
                from langchain_text_splitters import RecursiveCharacterTextSplitter

                langchain_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=effective_tokens * 4,
                    chunk_overlap=cmd.tokens_overlap * 4,
                )
                # Create a temporary document with the full text for langchain_splitter
                full_doc = Document(page_content=full_text, metadata=base_metadata)
                split_docs = langchain_splitter.split_documents([full_doc])
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
                status_message="Indexing in vector store...",
                current_step=3,
                total_steps=4,
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "processing",
                    "step": "indexing",
                },
            )

            created_ids = self.vector_service.index_documents(chunks)

            # 7. Finalize
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.FINISHED,
                status_message=f"Ingestion complete: {cmd.title or cmd.file_name}",
                current_step=4,
                total_steps=4,
                chunks_count=len(chunks),
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "completed",
                    "title": cmd.title or cmd.file_name,
                    "source_id": str(source.id),
                    "chunks_count": len(chunks),
                },
            )

            total_tokens = sum(
                c.tokens_count for c in chunks if c.tokens_count is not None
            )
            dims = getattr(self.model_loader_service, "dimensions", None)
            dims_val: int = int(dims) if dims is not None else 0

            max_tokens = cmd.tokens_per_chunk
            logger.info(
                "FileIngestion finished",
                context={
                    "source_id": str(source.id),
                    "requested_tokens": cmd.tokens_per_chunk,
                    "limit": self.model_loader_service.max_seq_length,
                    "effective_tokens": max_tokens,
                },
            )

            self.cs_service.finish_ingestion(
                content_source_id=source.id,
                embedding_model=self.model_loader_service.model_name,
                dimensions=dims_val,
                chunks=len(chunks),
                total_tokens=total_tokens,
                max_tokens_per_chunk=max_tokens,
                source_metadata=docs[0].metadata,
            )

            return {
                "file_name": cmd.file_name,
                "created_chunks": len(chunks),
                "vector_ids": created_ids,
                "source_id": source.id,
                "job_id": ingestion.id,
            }

        except Exception as e:
            logger.error(e, context={"action": "file_ingestion_execute"})
            if ingestion:
                error_msg = str(e).lower()
                status = IngestionJobStatus.FAILED

                # Treat 404 or Not Found as Cancelled (as requested by user)
                if "404" in error_msg or "not found" in error_msg:
                    status = IngestionJobStatus.CANCELLED

                self.ingestion_service.update_job(
                    job_id=ingestion.id,
                    status=status,
                    error_message=str(e),
                )
                self.event_bus.publish(
                    "ingestion_status",
                    {
                        "job_id": str(ingestion.id),
                        "status": status.value,
                        "error": str(e),
                    },
                )
            if source:
                self.cs_service.update_processing_status(
                    content_source_id=source.id, status=ContentSourceStatus.FAILED
                )
            raise e
        finally:
            if (
                cmd.delete_after_ingestion
                and cmd.file_path
                and os.path.exists(cmd.file_path)
            ):
                try:
                    # If it's in a temp dir we created, delete the whole dir
                    # Assumption: it's in a subfolder of tempfile.gettempdir()
                    parent_dir = os.path.dirname(cmd.file_path)
                    if "tmp" in parent_dir.lower() or "temp" in parent_dir.lower():
                        shutil.rmtree(parent_dir, ignore_errors=True)
                    else:
                        os.remove(cmd.file_path)
                    logger.info(
                        "Cleaned up temporary file/directory",
                        context={"path": cmd.file_path},
                    )
                except Exception as ex:
                    logger.warning(
                        "Failed to cleanup temporary files",
                        context={"path": cmd.file_path, "error": str(ex)},
                    )

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
