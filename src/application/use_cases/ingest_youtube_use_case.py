import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType
from src.application.dtos.results.ingest_youtube_result import IngestYoutubeResult
from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embeddding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_process_service import YoutubeDataProcessService
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

logger = Logger()


class IngestYoutubeUseCase:
    """Orquestra a ingestão de vídeos do YouTube usando métodos por step para facilitar testes e logs.

    Agora suporta ingestão de múltiplos vídeos (video_urls) e diferenciação por data_type (VIDEO/PLAYLIST).
    """

    def __init__(
            self,
            ks_service: KnowledgeSubjectService,
            cs_service: ContentSourceService,
            ingestion_service: IngestionJobService,
            model_loader_service: ModelLoaderService,
            embedding_service: EmbeddingService,
            chunk_service: ChunkIndexService,
            vector_service: YouTubeVectorService,
    ) -> None:
        self.ks_service = ks_service
        self.cs_service = cs_service
        self.ingestion_service = ingestion_service
        self.model_loader_service = model_loader_service
        self.embedding_service = embedding_service
        self.chunk_service = chunk_service
        self.vector_service = vector_service

    def execute(self, cmd: IngestYoutubeCommand) -> IngestYoutubeResult:
        logger.info(
            "Starting YouTube ingestion",
            context={
                "video_url": getattr(cmd, "video_url", None),
                "video_urls": getattr(cmd, "video_urls", None),
                "subject_id": getattr(cmd, "subject_id", None),
                "data_type": getattr(cmd, "data_type", None),
            },
        )

        # Try to recover job context early for failure reporting
        ingestion = None
        source = None
        if cmd.ingestion_job_id:
            try:
                from uuid import UUID
                jid = UUID(cmd.ingestion_job_id) if isinstance(cmd.ingestion_job_id, str) else cmd.ingestion_job_id
                ingestion = self.ingestion_service.get_by_id(jid)
                if ingestion and ingestion.content_source_id:
                    source = self.cs_service.get_by_id(ingestion.content_source_id)
            except Exception as context_error:
                logger.debug(f"Could not recover job context: {context_error}")

        try:
            subject = self._resolve_subject(cmd)
            logger.debug("KnowledgeSubject validated",
                        context={"subject_id": str(subject.id), "subject_name": subject.name})

            if cmd.data_type == YoutubeDataType.PLAYLIST:
                logger.info("Processing playlist", context={"playlist_url": cmd.video_url or (cmd.video_urls[0] if cmd.video_urls else None)})
                playlist_url = cmd.video_url or (cmd.video_urls[0] if cmd.video_urls else None)
                if not playlist_url:
                    raise ValueError("No video_url provided for playlist ingestion")
                video_list = YoutubeExtractor.extract_playlist_videos(playlist_url)
                if not video_list:
                    logger.warning("No videos found in playlist", context={"playlist_url": playlist_url})
                    raise ValueError(f"No videos found in playlist: {playlist_url}. Verify if the URL is a valid public playlist.")
            else:
                # determine list of video URLs to process
                if cmd.video_urls:
                    video_list = [v for v in cmd.video_urls if v is not None]
                elif cmd.video_url:
                    video_list = [cmd.video_url]
                else:
                    raise ValueError("No video_url(s) provided in command")

            result = IngestYoutubeResult()

            # For tracking the main job status in case of playlist, we update it to PROCESSING
            if ingestion:
                self._update_ingestion_processing(ingestion)

            for video_url in video_list:
                try:
                    video_id = self._extract_video_id_from_url(video_url)
                    if not video_id:
                        raise ValueError(f"Unable to extract video id from url: {video_url}")

                    # If this is the first video of a playlist and we have a job without a source,
                    # we could link it here, but it's better to just process individually.
                    # Individual videos create their own jobs and sources.
                    
                    single_result = self._process_single_video(video_url, video_id, subject, cmd)
                    result.video_results.append(single_result)
                    if not single_result.get("skipped", False):
                        result.created_chunks = (result.created_chunks or 0) + single_result.get("created_chunks", 0)
                        result.vector_ids.extend(single_result.get("vector_ids", []))
                except Exception as e:
                    logger.error(e, context={"video_url": video_url})
                    result.video_results.append({"video_url": video_url, "error": str(e)})

            # Finish the main tracking job
            if ingestion:
                self._finish_job(ingestion)
            
            # Finish the parent source only if it exists (for single videos)
            if cmd.data_type != YoutubeDataType.PLAYLIST and source:
                self._finish_ingestion(source, result.created_chunks or 0)

            logger.info("YouTube ingestion completed", context={"job_id": cmd.ingestion_job_id, "chunks": result.created_chunks})
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(error_msg, context={"video_urls": getattr(cmd, "video_urls", None)})
            
            if source:
                try:
                    self._fail_ingestion(source)
                except Exception as ef:
                    logger.error(f"Failed to mark source as FAILED: {ef}")
            
            if ingestion:
                try:
                    self._fail_job(ingestion, error_msg)
                except Exception as ej:
                    logger.error(f"Failed to mark job as FAILED: {ej}")
            
            raise e

    def _process_single_video(self, video_url: str, video_id: str, subject, cmd: IngestYoutubeCommand) -> Dict[
        str, Any]:
        logger.info("Processing video", context={"video_id": video_id, "video_url": video_url})

        existing = self._check_existing_source(video_id)
        if existing and existing.processing_status == "done":
            logger.info("Source already exists and is DONE, skipping ingestion",
                        context={"source_id": str(existing.id), "external_source": video_id})
            return {"video_url": video_url, "video_id": video_id, "skipped": True, "reason": "source_exists_and_done",
                    "source_id": existing.id}

        source = existing 
        ingestion = None
        try:
            # Extract metadata to get the actual video title
            yt_extractor = YoutubeExtractor(video_id=video_id, language=cmd.language)
            metadata = yt_extractor.extract_metadata()
            extracted_title = metadata.full_title or metadata.title or cmd.title
            
            if not extracted_title or not str(extracted_title).strip():
                logger.warning("No title extracted for video, using fallback", context={"video_id": video_id})
                extracted_title = f"YouTube Video {video_id}"

            logger.debug("Video title determined", context={"video_id": video_id, "title": extracted_title})

            if source is None:
                source = self._create_content_source(subject, cmd, video_id, title=extracted_title)
            else:
                self.cs_service._repo.update_title(content_source_id=source.id, title=extracted_title)

            # Reuse pre-created job if provided, otherwise create a new one
            if cmd.ingestion_job_id:
                try:
                    from uuid import UUID
                    jid = UUID(cmd.ingestion_job_id) if isinstance(cmd.ingestion_job_id, str) else cmd.ingestion_job_id
                    ingestion = self.ingestion_service.get_by_id(jid)
                    logger.debug("Reusing pre-created ingestion job", context={"job_id": str(jid)})
                except Exception as ej:
                    logger.warning(f"Failed to retrieve pre-created job {cmd.ingestion_job_id}, creating new one: {ej}")
                    ingestion = self._create_ingestion_job(source)
            else:
                ingestion = self._create_ingestion_job(source)

            self._mark_source_processing(source)
            self._update_ingestion_processing(ingestion)

            docs = self._extract_and_split(cmd, video_id, yt_extractor=yt_extractor)
            
            if not docs:
                raise ValueError(f"No transcript chunks generated for video {video_id}. It might be too short or have no available subtitles.")

            chunks = self._build_chunk_entities(docs, source, subject, cmd)
            self._persist_chunks(chunks)

            created_ids = self._index_chunks(chunks)

            self._finish_ingestion(source, len(chunks))
            self._finish_job(ingestion)

            return {"video_url": video_url, "video_id": video_id, "skipped": False, "created_chunks": len(chunks),
                    "vector_ids": created_ids, "source_id": source.id}
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing video {video_id}: {error_msg}", context={"video_url": video_url})
            
            if source:
                try:
                    self._fail_ingestion(source)
                except Exception as ef:
                    logger.error(f"Failed to mark source as FAILED: {ef}")
            
            if ingestion:
                try:
                    self._fail_job(ingestion, error_msg)
                except Exception as ej:
                    logger.error(f"Failed to mark job as FAILED: {ej}")
            
            raise e

    def _fail_ingestion(self, source) -> None:
        self.cs_service.update_processing_status(content_source_id=source.id, status=ContentSourceStatus.FAILED)
        logger.info("Content source marked as FAILED", context={"content_source_id": str(source.id)})

    def _fail_job(self, ingestion, error_message: str) -> None:
        self.ingestion_service.update_job(job_id=ingestion.id, status=IngestionJobStatus.FAILED, error_message=error_message)
        logger.info("Ingestion job updated to FAILED", context={"job_id": str(ingestion.id)})

    @classmethod
    def _extract_video_id_from_url(cls, url: str) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if "youtu.be" in netloc:
            vid = parsed.path.lstrip("/")
            return vid or None
        if "youtube" in netloc:
            q = parse_qs(parsed.query)
            if "v" in q:
                return q["v"][0]
            path_parts = [p for p in parsed.path.split("/") if p]
            for i, part in enumerate(path_parts):
                if part in ("embed", "v") and i + 1 < len(path_parts):
                    return path_parts[i + 1]
            if path_parts:
                return path_parts[-1]
        m = re.search(r"([A-Za-z0-9_-]{11})", url)
        if m:
            return m.group(1)
        return None

    def _resolve_subject(self, cmd: IngestYoutubeCommand):
        if getattr(cmd, "subject_id", None):
            try:
                subject_id_val = cmd.subject_id if isinstance(cmd.subject_id, uuid.UUID) else uuid.UUID(
                    str(cmd.subject_id))
            except Exception as e:
                logger.error(e, context={"subject_id": getattr(cmd, "subject_id", None)})
                raise ValueError(f"Invalid subject_id provided: {e}")
            subject = self.ks_service.get_subject_by_id(subject_id_val)
            if subject is None:
                logger.error("KnowledgeSubject not found by id", context={"subject_id": str(subject_id_val)})
                raise ValueError(f"KnowledgeSubject with id {subject_id_val} not found")
            return subject

        if cmd.subject_name:
            subject = self.ks_service.get_by_name(cmd.subject_name)
            if subject is None:
                logger.error("KnowledgeSubject not found by name", context={"subject_name": cmd.subject_name})
                raise ValueError(f"KnowledgeSubject with name '{cmd.subject_name}' not found")
            return subject

        logger.error("No subject identifier provided", context={"video_url": getattr(cmd, "video_url", None)})
        raise ValueError("Either subject_id or subject_name must be provided")

    def _check_existing_source(self, video_id: str):
        logger.debug("Checking existing content source", context={"external_source": video_id})
        return self.cs_service.get_by_source_info(source_type=SourceType.YOUTUBE, external_source=video_id)

    def _create_content_source(self, subject, cmd: IngestYoutubeCommand, video_id: str, title: Optional[str] = None):
        source = self.cs_service.create_source(
            subject_id=subject.id,
            source_type=SourceType.YOUTUBE,
            external_source=video_id,
            title=title or cmd.title,
            language=cmd.language,
            status=ContentSourceStatus.ACTIVE,
            processing_status="pending"
        )
        logger.debug("Content source created", context={"content_source_id": str(source.id), "external_source": video_id})
        return source

    def _create_ingestion_job(self, source):
        ingestion = self.ingestion_service.create_job(
            content_source_id=source.id,
            status=IngestionJobStatus.STARTED,
            embedding_model=self.model_loader_service.model_name,
            pipeline_version="1.0",
        )
        logger.debug("Ingestion job created", context={"job_id": str(ingestion.id)})
        return ingestion

    def _mark_source_processing(self, source) -> None:
        self.cs_service.update_processing_status(content_source_id=source.id, status=ContentSourceStatus.PROCESSING)
        logger.debug("Content source marked as PROCESSING", context={"content_source_id": str(source.id)})

    def _extract_and_split(self, cmd: IngestYoutubeCommand, video_id: str, yt_extractor: Optional[YoutubeExtractor] = None) -> List[Document]:
        logger.debug("Starting extraction and transcript split", context={"video_id": video_id})
        if yt_extractor is None:
            yt_extractor = YoutubeExtractor(video_id=video_id, language=cmd.language)

        ytts = YoutubeDataProcessService(model_loader_service=self.model_loader_service, yt_extractor=yt_extractor)
        docs: List[Document] = ytts.split_transcript(mode="tokens", tokens_per_chunk=cmd.tokens_per_chunk,
                                                     tokens_overlap=cmd.tokens_overlap,)

        logger.debug("Transcript split completed", context={"video_id": video_id, "chunks": len(docs)})
        return docs

    def _update_ingestion_processing(self, ingestion) -> None:
        self.ingestion_service.update_job(job_id=ingestion.id, status=IngestionJobStatus.PROCESSING)
        logger.debug("Ingestion job updated to PROCESSING", context={"job_id": str(ingestion.id)})

    def _build_chunk_entities(self, docs: List[Document], source, subject, cmd: IngestYoutubeCommand) -> List[
        ChunkEntity]:
        list_chunks: List[ChunkEntity] = []
        for doc in docs:
            chunk_entity = ChunkEntity(
                id=uuid.uuid4(),
                job_id=uuid.uuid4(),
                content_source_id=source.id,
                source_type=SourceType(source.source_type),
                external_source=source.external_source,
                subject_id=subject.id,
                content=doc.page_content,
                tokens_count=doc.metadata.get("token_count"),
                extra=doc.metadata,
                language=cmd.language,
                embedding_model=self.model_loader_service.model_name,
                created_at=datetime.now(timezone.utc),
                version_number=1,
            )
            list_chunks.append(chunk_entity)
        logger.debug("Built chunk entities", context={"num_chunks": len(list_chunks)})
        return list_chunks

    def _persist_chunks(self, chunks: List[ChunkEntity]) -> None:
        self.chunk_service.create_chunks(chunks)
        logger.debug("Persisted chunks to SQL repository", context={"num_chunks": len(chunks)})

    def _index_chunks(self, chunks: List[ChunkEntity]) -> List[str]:
        created_ids = self.vector_service.index_documents(chunks)
        logger.debug("Indexed chunks in vector store", context={"indexed_count": len(created_ids)})
        return created_ids

    def _finish_ingestion(self, source, num_chunks: int) -> None:
        dims = getattr(self.model_loader_service, "dimensions", None)
        dims_val: int = int(dims) if dims is not None else 0

        self.cs_service.finish_ingestion(
            content_source_id=source.id,
            embedding_model=self.model_loader_service.model_name,
            dimensions=dims_val,
            chunks=num_chunks,
        )
        logger.info("Ingestion finished",
                    context={"content_source_id": str(source.id), "chunks": num_chunks})

    def _finish_job(self, ingestion) -> None:
        self.ingestion_service.update_job(job_id=ingestion.id, status=IngestionJobStatus.FINISHED)
        logger.debug("Ingestion job marked as FINISHED", context={"job_id": str(ingestion.id)})
