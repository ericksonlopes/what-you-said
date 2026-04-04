import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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
        self._notify_status(cmd, "started")
        logger.info(
            "Starting File ingestion",
            context={"file_name": cmd.file_name, "subject_id": str(cmd.subject_id)},
        )

        ingestion, source = None, None
        try:
            subject = self._resolve_subject(cmd)
            source_type = self._determine_source_type_refined(cmd)
            external_source = cmd.external_source or cmd.file_name

            ingestion = self._get_or_create_job(cmd, source_type, external_source)
            self._notify_status(
                cmd, "processing", job_id=ingestion.id, step="extracting"
            )

            # 1. Extraction
            source_path = cmd.file_url or cmd.file_path
            if not source_path:
                raise ValueError("Neither file_path nor file_url provided")

            docs = self._extract_docs(source_path, cmd)
            source_type = self._refine_source_type(docs, source_type)

            # 2. Source Management
            source = self._get_or_create_source(
                subject, source_type, external_source, docs[0].metadata, cmd
            )
            if cmd.reprocess:
                self._handle_reprocessing(source, ingestion)

            # 3. Processing (Splitting, Embedding, Indexing)
            self._notify_status(
                cmd,
                "processing",
                job_id=ingestion.id,
                step="embedding",
                chunks_count=len(docs),
            )

            chunks = self._process_chunks(docs, source, subject, cmd, ingestion.id)

            self._notify_status(cmd, "processing", job_id=ingestion.id, step="indexing")
            created_ids = self.vector_service.index_documents(chunks)

            # 4. Finalize
            self._finalize(ingestion, source, chunks, docs[0].metadata, cmd)
            self._notify_status(
                cmd,
                "completed",
                job_id=ingestion.id,
                source_id=source.id,
                chunks_count=len(chunks),
            )

            return {
                "file_name": cmd.file_name,
                "created_chunks": len(chunks),
                "vector_ids": created_ids,
                "source_id": source.id,
                "job_id": ingestion.id,
            }

        except Exception as e:
            self._handle_error(e, ingestion, source)
            raise
        finally:
            self._cleanup(cmd)

    def _notify_status(
        self,
        cmd: IngestFileCommand,
        status: str,
        job_id: Any = "new",
        step: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "job_id": str(job_id),
            "status": status,
            "file_name": cmd.file_name,
            "title": cmd.title or cmd.file_name,
        }
        if step:
            payload["step"] = step
        payload.update(kwargs)
        self.event_bus.publish("ingestion_status", payload)

    def _extract_docs(self, source_path: str, cmd: IngestFileCommand) -> List[Document]:
        try:
            docs = self.extractor.extract(source_path, do_ocr=cmd.do_ocr)
        except Exception as e:
            if any(m in str(e).lower() for m in ["format not allowed", "unsupported"]):
                docs = self.plain_text_extractor.extract(source_path)
            else:
                raise
        if not docs:
            raise ValueError(f"No content extracted from {cmd.file_name}")
        return docs

    def _refine_source_type(
        self, docs: List[Document], current: SourceType
    ) -> SourceType:
        docling_detected = docs[0].metadata.get("docling_source_type")
        extracted_ext = docs[0].metadata.get("source_type")

        for ext in [docling_detected, extracted_ext]:
            if not ext or not isinstance(ext, str):
                continue
            try:
                refined = SourceType(ext.lower())
                if refined == SourceType.OTHER:
                    continue
                if (
                    current in [SourceType.YOUTUBE, SourceType.WEB]
                    and refined == SourceType.TXT
                ):
                    continue
                return refined
            except ValueError:
                continue
        return current

    def _get_or_create_job(
        self, cmd: IngestFileCommand, source_type: SourceType, external_source: str
    ) -> Any:
        if cmd.ingestion_job_id:
            job = self.ingestion_service.get_by_id(cmd.ingestion_job_id)
            if job:
                return job

        return self.ingestion_service.create_job(
            content_source_id=None,
            status=IngestionJobStatus.STARTED,
            embedding_model=self.model_loader_service.model_name,
            pipeline_version="1.0",
            ingestion_type=source_type.value,
            vector_store_type=self.vector_store_type,
            external_source=external_source,
        )

    def _get_or_create_source(
        self,
        subject: Any,
        source_type: SourceType,
        external_source: str,
        metadata: dict,
        cmd: IngestFileCommand,
    ) -> Any:
        source = self.cs_service.get_by_source_info(
            source_type, external_source, cmd.subject_id
        )
        final_meta = {**metadata, **(cmd.source_metadata or {})}

        if not source:
            return self.cs_service.create_source(
                subject_id=subject.id,
                source_type=source_type,
                external_source=external_source,
                status=ContentSourceStatus.PROCESSING,
                title=cmd.title or cmd.file_name,
                language=cmd.language,
                source_metadata=final_meta,
            )

        self.cs_service.update_processing_status(
            source.id, ContentSourceStatus.PROCESSING
        )
        return source

    def _process_chunks(
        self,
        docs: List[Document],
        source: Any,
        subject: Any,
        cmd: IngestFileCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        full_text = "\n\n".join([doc.page_content for doc in docs])
        tokenizer = (
            getattr(self.model_loader_service.model, "tokenizer", None)
            if hasattr(self.model_loader_service, "model")
            else None
        )

        if tokenizer:
            splitter = TextSplitterService(tokenizer=tokenizer)
            split_docs = splitter.split_text(
                full_text, cmd.tokens_per_chunk, cmd.tokens_overlap, docs[0].metadata
            )
        else:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            ls = RecursiveCharacterTextSplitter(
                chunk_size=cmd.tokens_per_chunk * 4,
                chunk_overlap=cmd.tokens_overlap * 4,
            )
            split_docs = ls.split_documents(
                [Document(page_content=full_text, metadata=docs[0].metadata)]
            )

        chunks = self._build_chunk_entities(split_docs, source, subject, cmd, job_id)
        self.chunk_service.create_chunks(chunks)
        return chunks

    def _handle_reprocessing(self, source: Any, ingestion: Any):
        sid = source.id
        self.chunk_service.delete_by_content_source(sid)
        self.vector_service.delete(filters={"content_source_id": str(sid)})
        if ingestion:
            self.ingestion_service.mark_previous_jobs_as_reprocessed(sid, ingestion.id)

    def _finalize(
        self,
        job: Any,
        source: Any,
        chunks: List[ChunkEntity],
        metadata: dict,
        cmd: IngestFileCommand,
    ):
        self.ingestion_service.update_job(
            job.id,
            IngestionJobStatus.FINISHED,
            f"Ingestion complete: {cmd.file_name}",
            chunks_count=len(chunks),
        )
        tokens = sum(c.tokens_count for c in chunks if c.tokens_count)
        dims = getattr(self.model_loader_service, "dimensions", 0)
        self.cs_service.finish_ingestion(
            source.id,
            self.model_loader_service.model_name,
            int(dims or 0),
            len(chunks),
            tokens,
            cmd.tokens_per_chunk,
            metadata,
        )

    def _handle_error(self, e: Exception, ingestion: Any, source: Any):
        logger.error(e, context={"action": "file_ingestion_execute"})
        if ingestion:
            msg = str(e).lower()
            status = (
                IngestionJobStatus.CANCELLED
                if ("404" in msg or "not found" in msg)
                else IngestionJobStatus.FAILED
            )
            self.ingestion_service.update_job(
                ingestion.id, status, error_message=str(e)
            )
        if source:
            self.cs_service.update_processing_status(
                source.id, ContentSourceStatus.FAILED
            )

    def _cleanup(self, cmd: IngestFileCommand):
        if (
            cmd.delete_after_ingestion
            and cmd.file_path
            and os.path.exists(cmd.file_path)
        ):
            parent = os.path.dirname(cmd.file_path)
            if any(t in parent.lower() for t in ["tmp", "temp"]):
                shutil.rmtree(parent, ignore_errors=True)
            else:
                os.remove(cmd.file_path)

    def _resolve_subject(self, cmd: IngestFileCommand):
        if cmd.subject_id:
            s = self.ks_service.get_subject_by_id(cmd.subject_id)
        elif cmd.subject_name:
            s = self.ks_service.get_by_name(cmd.subject_name)
        else:
            raise ValueError("Subject missing")
        if not s:
            raise ValueError("Subject not found")
        return s

    def _determine_source_type_refined(self, cmd: IngestFileCommand) -> SourceType:
        if cmd.source_type:
            try:
                return SourceType(cmd.source_type.lower())
            except ValueError:
                pass

        ext = cmd.file_name.split(".")[-1].lower() if "." in cmd.file_name else ""
        if cmd.external_source and any(
            d in cmd.external_source for d in ["youtube.com", "youtu.be"]
        ):
            return SourceType.YOUTUBE

        mapping = {
            "doc": SourceType.DOCX,
            "docx": SourceType.DOCX,
            "ppt": SourceType.PPTX,
            "pptx": SourceType.PPTX,
            "xls": SourceType.XLSX,
            "xlsx": SourceType.XLSX,
            "md": SourceType.MARKDOWN,
            "markdown": SourceType.MARKDOWN,
            "jpg": SourceType.IMAGE,
            "png": SourceType.IMAGE,
            "txt": SourceType.TXT,
        }
        return mapping.get(ext, SourceType.OTHER)

    def _build_chunk_entities(
        self,
        docs: List[Document],
        source: Any,
        subject: Any,
        cmd: IngestFileCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        tokenizer = (
            getattr(self.model_loader_service.model, "tokenizer", None)
            if hasattr(self.model_loader_service, "model")
            else None
        )
        chunks = []
        for i, doc in enumerate(docs):
            t_count = 0
            if tokenizer:
                try:
                    t_count = len(
                        tokenizer.encode(doc.page_content, add_special_tokens=False)
                    )
                except Exception:
                    t_count = len(doc.page_content) // 4
            else:
                t_count = len(doc.page_content) // 4

            chunks.append(
                ChunkEntity(
                    id=uuid.uuid4(),
                    job_id=job_id,
                    content_source_id=source.id,
                    source_type=SourceType(source.source_type),
                    external_source=source.external_source,
                    subject_id=subject.id,
                    index=i,
                    content=doc.page_content,
                    tokens_count=t_count,
                    extra={**doc.metadata, "vector_store_type": self.vector_store_type},
                    language=cmd.language,
                    embedding_model=self.model_loader_service.model_name,
                    created_at=datetime.now(timezone.utc),
                    version_number=1,
                )
            )
        return chunks
