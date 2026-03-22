import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_web_command import IngestWebCommand
from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.extractors.crawl4ai_extractor import Crawl4AIExtractor
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


class WebScrapingUseCase:
    """Orchestrates web scraping ingestion using Crawl4AI."""

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
        extractor: Crawl4AIExtractor,
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
        self.extractor = extractor

    async def execute(self, cmd: IngestWebCommand) -> Dict[str, Any]:
        """
        Executes the web scraping ingestion process.
        This method is async to support Crawl4AI's async nature.
        """
        self.event_bus.publish(
            "ingestion_status",
            {
                "job_id": str(cmd.ingestion_job_id) if cmd.ingestion_job_id else "new",
                "status": "started",
                "url": cmd.url,
            },
        )
        logger.info(
            "Starting Web Scraping ingestion",
            context={
                "url": cmd.url,
                "subject_id": str(cmd.subject_id) if cmd.subject_id else None,
            },
        )

        ingestion = None
        source = None

        try:
            subject = self._resolve_subject(cmd)

            # 1. Create or retrieve Ingestion Job
            if cmd.ingestion_job_id:
                try:
                    jid = (
                        UUID(cmd.ingestion_job_id)
                        if isinstance(cmd.ingestion_job_id, str)
                        else cmd.ingestion_job_id
                    )
                    ingestion = self.ingestion_service.get_by_id(jid)
                except Exception as e:
                    logger.warning(f"Could not retrieve ingestion job {cmd.ingestion_job_id}: {e}")

            if ingestion is None:
                ingestion = self.ingestion_service.create_job(
                    content_source_id=None,
                    status=IngestionJobStatus.STARTED,
                    embedding_model=self.model_loader_service.model_name,
                    pipeline_version="1.0",
                    ingestion_type=SourceType.WEB.value,
                    vector_store_type=self.vector_store_type,
                    external_source=cmd.url,
                    subject_id=subject.id,
                )

            # 2. Extract content
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message=f"Scraping content from {cmd.url}...",
                current_step=1,
                total_steps=4,
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "processing",
                    "step": "extracting",
                    "title": cmd.title or cmd.url,
                },
            )

            try:
                docs = await self.extractor.extract(
                    source=cmd.url, css_selector=cmd.css_selector, depth=cmd.depth
                )
            except Exception as e:
                logger.error(f"Scraping failed for {cmd.url}: {e}")
                raise e

            if not docs:
                raise ValueError(f"No content extracted from URL: {cmd.url}")

            # 3. Create or Get Source
            extracted_title = docs[0].metadata.get("title") or cmd.title or cmd.url

            source = self.cs_service.get_by_source_info(
                source_type=SourceType.WEB,
                external_source=cmd.url,
                subject_id=subject.id,
            )

            if not source:
                source = self.cs_service.create_source(
                    subject_id=subject.id,
                    source_type=SourceType.WEB,
                    external_source=cmd.url,
                    status=ContentSourceStatus.PROCESSING,
                    title=extracted_title,
                    language=cmd.language,
                    source_metadata=docs[0].metadata,
                )
            else:
                # Update title and metadata if it exists
                self.cs_service.update_processing_status(
                    source.id, ContentSourceStatus.PROCESSING
                )

                # --- REPROCESSING CLEANUP ---
                if cmd.reprocess:
                    logger.info(
                        "REPROCESSING: Performing pre-ingestion cleanup for web source",
                        context={"source_id": str(source.id), "url": cmd.url},
                    )
                    try:
                        sql_del = self.chunk_service.delete_by_content_source(source.id)
                        # We use a filter to target only this source's chunks
                        filters = {"content_source_id": str(source.id)}
                        vec_del = self.vector_service.delete(filters=filters)

                        logger.info(
                            "Web reprocessing cleanup finished",
                            context={"sql_deleted": sql_del, "vector_deleted": vec_del},
                        )
                    except Exception as ce:
                        logger.warning(
                            f"Error during reprocessing cleanup for source {source.id}: {ce}"
                        )

            # 4. Generate chunks and Embeddings
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message=f"Generating embeddings for {len(docs)} chunks...",
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

            full_text = "\n\n".join([doc.page_content for doc in docs])
            base_metadata = docs[0].metadata

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

            created_ids = self.vector_service.index_documents(chunks)

            # 7. Finalize
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.FINISHED,
                status_message=f"Ingestion complete: {extracted_title}",
                current_step=4,
                total_steps=4,
                chunks_count=len(chunks),
            )

            total_tokens = sum(
                c.tokens_count for c in chunks if c.tokens_count is not None
            )
            dims = getattr(self.model_loader_service, "dimensions", 0)

            self.cs_service.finish_ingestion(
                content_source_id=source.id,
                embedding_model=self.model_loader_service.model_name,
                dimensions=int(dims) if dims is not None else 0,
                chunks=len(chunks),
                total_tokens=total_tokens,
                max_tokens_per_chunk=cmd.tokens_per_chunk,
                source_metadata=docs[0].metadata,
            )

            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "completed",
                    "title": extracted_title,
                    "source_id": str(source.id),
                    "chunks_count": len(chunks),
                },
            )

            return {
                "url": cmd.url,
                "created_chunks": len(chunks),
                "vector_ids": created_ids,
                "source_id": source.id,
                "job_id": ingestion.id,
            }

        except Exception as e:
            logger.error(f"Error in WebScrapingUseCase: {e}")
            if ingestion:
                self.ingestion_service.update_job(
                    job_id=ingestion.id,
                    status=IngestionJobStatus.FAILED,
                    error_message=str(e),
                )
                self.event_bus.publish(
                    "ingestion_status",
                    {
                        "job_id": str(ingestion.id),
                        "status": "failed",
                        "error": str(e),
                    },
                )
            if source:
                self.cs_service.update_processing_status(
                    content_source_id=source.id, status=ContentSourceStatus.FAILED
                )
            raise e

    def _resolve_subject(self, cmd: IngestWebCommand):
        if cmd.subject_id:
            subject = self.ks_service.get_subject_by_id(
                UUID(cmd.subject_id)
                if isinstance(cmd.subject_id, str)
                else cmd.subject_id
            )
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_id}")
            return subject
        if cmd.subject_name:
            subject = self.ks_service.get_by_name(cmd.subject_name)
            if not subject:
                raise ValueError(f"Subject not found: {cmd.subject_name}")
            return subject
        raise ValueError("Either subject_id or subject_name must be provided")

    def _build_chunk_entities(
        self,
        docs: List[Document],
        source,
        subject,
        cmd: IngestWebCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        list_chunks: List[ChunkEntity] = []

        tokenizer = None
        if hasattr(self.model_loader_service, "model") and hasattr(
            self.model_loader_service.model, "tokenizer"
        ):
            tokenizer = self.model_loader_service.model.tokenizer

        for i, doc in enumerate(docs):
            tokens_count = None
            if tokenizer:
                try:
                    tokens = tokenizer.encode(
                        doc.page_content, add_special_tokens=False
                    )
                    tokens_count = len(tokens)
                except Exception:
                    tokens_count = len(doc.page_content) // 4
            else:
                tokens_count = len(doc.page_content) // 4

            chunk_entity = ChunkEntity(
                id=uuid.uuid4(),
                job_id=job_id,
                content_source_id=source.id,
                source_type=SourceType.WEB,
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
