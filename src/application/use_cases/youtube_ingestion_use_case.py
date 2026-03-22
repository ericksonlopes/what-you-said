import random
import re
import uuid
import concurrent.futures
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from uuid import UUID

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
from src.domain.exception.youtube_exceptions import (
    YoutubeVideoPrivateException,
    YoutubeVideoUnplayableException,
    YoutubeTranscriptNotFoundException,
    YoutubeTranscriptsDisabledException,
    YoutubeNetworkException,
)
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_process_service import (
    YoutubeDataProcessService,
)
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService
from src.config.settings import settings

logger = Logger()


class YoutubeIngestionUseCase:
    """Orquestra a ingestão de vídeos do YouTube usando métodos por step para facilitar testes e logs.

    Agora suporta ingestão de múltiplos vídeos (video_urls) e diferenciação por data_type (VIDEO/PLAYLIST).
    """

    _lock = threading.Lock()

    def __init__(
        self,
        ks_service: KnowledgeSubjectService,
        cs_service: ContentSourceService,
        ingestion_service: IngestionJobService,
        model_loader_service: ModelLoaderService,
        embedding_service: EmbeddingService,
        chunk_service: ChunkIndexService,
        vector_service: YouTubeVectorService,
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

    def execute(self, cmd: IngestYoutubeCommand) -> IngestYoutubeResult:
        self.event_bus.publish(
            "ingestion_status",
            {
                "job_id": str(cmd.ingestion_job_id) if cmd.ingestion_job_id else "new",
                "status": "started",
                "video_url": cmd.video_url,
            },
        )
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

                jid = (
                    UUID(cmd.ingestion_job_id)
                    if isinstance(cmd.ingestion_job_id, str)
                    else cmd.ingestion_job_id
                )
                ingestion = self.ingestion_service.get_by_id(jid)
                if ingestion and ingestion.content_source_id:
                    source = self.cs_service.get_by_id(ingestion.content_source_id)
            except Exception as context_error:
                logger.debug(
                    "Could not recover job context",
                    context={"error": str(context_error)},
                )

        try:
            subject = self._resolve_subject(cmd)
            logger.debug(
                "KnowledgeSubject validated",
                context={"subject_id": str(subject.id), "subject_name": subject.name},
            )

            if cmd.data_type == YoutubeDataType.PLAYLIST:
                logger.info(
                    "Processing playlist",
                    context={
                        "playlist_url": cmd.video_url
                        or (cmd.video_urls[0] if cmd.video_urls else None)
                    },
                )
                playlist_url = cmd.video_url or (
                    cmd.video_urls[0] if cmd.video_urls else None
                )
                if not playlist_url:
                    raise ValueError("No video_url provided for playlist ingestion")
                video_list = YoutubeExtractor.extract_playlist_videos(playlist_url)
                if not video_list:
                    logger.warning(
                        "No videos found in playlist",
                        context={"playlist_url": playlist_url},
                    )
                    raise ValueError(
                        f"No videos found in playlist: {playlist_url}. Verify if the URL is a valid public playlist."
                    )
            else:
                # determine list of video URLs to process
                if cmd.video_urls:
                    video_list = [v for v in cmd.video_urls if v is not None]
                elif cmd.video_url:
                    video_list = [cmd.video_url]
                else:
                    raise ValueError("No video_url(s) provided in command")

            result = IngestYoutubeResult()
            if ingestion:
                result.job_id = ingestion.id

            # For tracking the main job status in case of playlist, we update it to PROCESSING
            if ingestion:
                self._update_ingestion_processing(ingestion)

            def process_video(video_url: str) -> Dict[str, Any]:
                try:
                    video_id = self._extract_video_id_from_url(video_url)
                    if not video_id:
                        raise ValueError(
                            f"Unable to extract video id from url: {video_url}"
                        )
                    return self._process_single_video(video_url, video_id, subject, cmd)
                except YoutubeNetworkException as e:
                    logger.error(
                        e,
                        context={"video_url": video_url, "error_type": "network_error"},
                    )
                    return {
                        "video_url": video_url,
                        "error": str(e),
                        "is_network_error": True,
                    }
                except Exception as e:
                    logger.error(
                        e, context={"video_url": video_url, "action": "process_video"}
                    )
                    return {"video_url": video_url, "error": str(e)}

            batch_size = settings.youtube.throttle_batch_size
            wait_time = settings.youtube.throttle_wait_seconds
            current_wait_time = wait_time

            for i in range(0, len(video_list), batch_size):
                batch = video_list[i : i + batch_size]
                logger.debug(
                    "Processing batch of YouTube videos",
                    context={
                        "batch_index": i // batch_size + 1,
                        "batch_size": len(batch),
                        "total_videos": len(video_list),
                    },
                )

                batch_has_network_error = False
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=len(batch)
                ) as executor:
                    futures = [executor.submit(process_video, url) for url in batch]
                    for future in concurrent.futures.as_completed(futures):
                        single_result = future.result()
                        result.video_results.append(single_result)

                        if single_result.get("is_network_error"):
                            batch_has_network_error = True

                        if (
                            not single_result.get("skipped", False)
                            and "error" not in single_result
                        ):
                            result.created_chunks = (
                                result.created_chunks or 0
                            ) + single_result.get("created_chunks", 0)
                            result.vector_ids.extend(
                                single_result.get("vector_ids", [])
                            )

                # Adaptive Throttling: If we hit a network error, double the wait time for the next batch
                if batch_has_network_error:
                    current_wait_time = min(
                        current_wait_time * 2, 600
                    )  # Max 10 minutes
                    logger.warning(
                        "Network error detected in batch. Increasing wait time",
                        context={
                            "new_wait_time": current_wait_time,
                            "batch_index": i // batch_size + 1,
                        },
                    )

                # Wait if there are more batches to process
                if i + batch_size < len(video_list):
                    # Add jitter to the wait time (randomly add 0-5 seconds)
                    jitter = random.uniform(0, 5)
                    total_wait = current_wait_time + jitter
                    logger.info(
                        "Throttling: waiting before next batch",
                        context={
                            "wait_time": total_wait,
                            "jitter": jitter,
                            "current_base_wait": current_wait_time,
                        },
                    )
                    time.sleep(total_wait)

            # 1. Determine overall status
            any_failed = any("error" in r for r in result.video_results)
            logger.debug(
                "Overall ingestion result status",
                context={
                    "any_failed": any_failed,
                    "results_count": len(result.video_results),
                },
            )

            # 2. Update the parent Tracking Job
            if ingestion:
                if any_failed:
                    # Collect error messages from failed videos (excluding cancelled ones)
                    errors = [
                        r["error"]
                        for r in result.video_results
                        if "error" in r and not r.get("cancelled", False)
                    ]
                    if errors:
                        error_summary = (
                            f"Ingestion failed for {len(errors)} items: "
                            + "; ".join(errors)[:200]
                        )
                        self._fail_job(ingestion, error_summary)
                    else:
                        # Only cancelled items
                        cancelled_msgs = [
                            r["error"]
                            for r in result.video_results
                            if r.get("cancelled", False)
                        ]
                        summary = f"Partial ingestion: {len(cancelled_msgs)} items skipped (private/unplayable)."
                        self.ingestion_service.update_job(
                            job_id=ingestion.id,
                            status=IngestionJobStatus.FINISHED,
                            status_message=summary,
                            chunks_count=result.created_chunks,
                        )
                else:
                    self._finish_job(ingestion, chunks_count=result.created_chunks)

            # 3. For single video ingestion, if it fails, we raise an error here
            # so the API returns a non-200 status and the user gets a notification.
            # We only do this if it's strictly a single video request (not a list of URLs)
            is_batch = len(video_list) > 1
            if (
                any_failed
                and cmd.data_type != YoutubeDataType.PLAYLIST
                and not is_batch
            ):
                failed_item = next(r for r in result.video_results if "error" in r)
                raise ValueError(failed_item["error"])

            # 4. Update the parent Source
            if source:
                # We fail the source only if there are real errors (not just cancellations)
                real_errors = [
                    r["error"]
                    for r in result.video_results
                    if "error" in r and not r.get("cancelled", False)
                ]
                if real_errors:
                    self._fail_ingestion(source)
                elif cmd.data_type != YoutubeDataType.PLAYLIST:
                    # For single videos, only finish if not already marked failed or done
                    current_source = self.cs_service.get_by_id(source.id)
                    if current_source and current_source.processing_status not in [
                        ContentSourceStatus.FAILED,
                        ContentSourceStatus.DONE,
                    ]:
                        # Sum tokens if possible, but for batch it's more complex.
                        # For now, we'll use the result created_chunks if chunks entities are available.
                        # Wait, execute() doesn't have easy access to all chunk entities here if it was parallel.
                        # However, _process_single_video already calls _finish_ingestion.
                        # So for single videos, it's already handled.
                        pass  # handled in _process_single_video

            skipped_count = sum(
                1 for r in result.video_results if r.get("skipped", False)
            )
            job_ids = [r.get("job_id") for r in result.video_results if r.get("job_id")]
            logger.info(
                "YouTube ingestion completed",
                context={
                    "job_ids": job_ids or cmd.ingestion_job_id,
                    "chunks": result.created_chunks,
                    "total_videos": len(result.video_results),
                    "skipped": skipped_count,
                },
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                e,
                context={
                    "video_urls": getattr(cmd, "video_urls", None),
                    "action": "youtube_ingestion_execute",
                },
            )

            if source:
                try:
                    self._fail_ingestion(source)
                except Exception as ef:
                    logger.error(
                        ef,
                        context={
                            "action": "fail_ingestion",
                            "source_id": str(source.id),
                        },
                    )

            if ingestion:
                try:
                    self._fail_job(ingestion, error_msg)
                except Exception as ej:
                    logger.error(
                        ej, context={"action": "fail_job", "job_id": str(ingestion.id)}
                    )

            raise e

    def _process_single_video(
        self, video_url: str, video_id: str, subject, cmd: IngestYoutubeCommand
    ) -> Dict[str, Any]:
        logger.info(
            "Processing video", context={"video_id": video_id, "video_url": video_url}
        )

        existing = self._check_existing_source(video_id, subject.id)
        if (
            existing
            and existing.processing_status == "done"
            and not getattr(cmd, "reprocess", False)
        ):
            logger.info(
                "Source already exists and is DONE, skipping ingestion (reprocess=False)",
                context={"source_id": str(existing.id), "external_source": video_id},
            )

            # Create a CANCELLED ingestion job to record the duplicate attempt
            failed_job_id = None
            try:
                failed_job = self.ingestion_service.create_job(
                    content_source_id=existing.id,
                    status=IngestionJobStatus.STARTED,
                    embedding_model=self.model_loader_service.model_name,
                    pipeline_version="1.0",
                    ingestion_type=SourceType.YOUTUBE.value,
                    vector_store_type=self.vector_store_type,
                )
                self.ingestion_service.update_job(
                    job_id=failed_job.id,
                    status=IngestionJobStatus.CANCELLED,
                    error_message="Duplicate: this content has already been ingested.",
                    status_message=f"Skipped: {video_id} already exists",
                )
                failed_job_id = str(failed_job.id)
                logger.info(
                    "Created CANCELLED job for duplicate attempt",
                    context={"job_id": failed_job_id, "video_id": video_id},
                )
            except Exception as ej:
                logger.error(
                    ej, context={"action": "create_cancelled_job", "video_id": video_id}
                )

            return {
                "video_url": video_url,
                "video_id": video_id,
                "skipped": True,
                "reason": "source_exists_and_done",
                "source_id": existing.id,
                "job_id": failed_job_id,
            }

        source = existing
        ingestion = None
        try:
            # --- REPROCESSING CLEANUP ---
            if source and getattr(cmd, "reprocess", False):
                logger.info(
                    "REPROCESSING: Performing pre-ingestion cleanup",
                    context={"source_id": str(source.id), "video_id": video_id},
                )
                try:
                    sql_del = self.chunk_service.delete_by_content_source(source.id)
                    vec_del = self.vector_service.delete_by_video_id(video_id)
                    logger.info(
                        "Reprocessing cleanup finished",
                        context={"sql_deleted": sql_del, "vector_deleted": vec_del},
                    )
                except Exception as ce:
                    logger.warning(
                        "Error during reprocessing cleanup",
                        context={"source_id": str(source.id), "error": str(ce)},
                    )

            # 1. Reuse or create Ingestion Job EARLY (even before source exists)
            if cmd.ingestion_job_id:
                try:
                    from uuid import UUID

                    jid = (
                        UUID(cmd.ingestion_job_id)
                        if isinstance(cmd.ingestion_job_id, str)
                        else cmd.ingestion_job_id
                    )
                    ingestion = self.ingestion_service.get_by_id(jid)
                    if ingestion is None:
                        logger.warning(
                            "Job not found, creating new one",
                            context={"job_id": str(cmd.ingestion_job_id)},
                        )
                        ingestion = self._create_ingestion_job(
                            source=source,
                            external_source=video_id,
                            subject_id=subject.id,
                        )
                    else:
                        logger.debug(
                            "Reusing pre-created ingestion job",
                            context={"job_id": str(jid)},
                        )
                except Exception as ej:
                    logger.warning(
                        "Failed to retrieve pre-created job, creating new one",
                        context={"job_id": str(cmd.ingestion_job_id), "error": str(ej)},
                    )
                    ingestion = self._create_ingestion_job(
                        source=source, external_source=video_id, subject_id=subject.id
                    )
            else:
                ingestion = self._create_ingestion_job(
                    source=source, external_source=video_id, subject_id=subject.id
                )

            if ingestion is None:
                raise ValueError("Failed to create or retrieve ingestion job")

            # 2. Extract metadata
            yt_extractor = YoutubeExtractor(video_id=video_id, language=cmd.language)
            metadata = yt_extractor.extract_metadata()
            extracted_title = metadata.full_title or metadata.title or cmd.title

            if not extracted_title or not str(extracted_title).strip():
                logger.warning(
                    "No title extracted for video, using fallback",
                    context={"video_id": video_id},
                )
                extracted_title = f"YouTube Video {video_id}"

            # 3. Create or Get Source EARLY
            if source is None:
                logger.info(
                    "Creating new ContentSource",
                    context={"video_id": video_id, "title": extracted_title},
                )
                source = self._create_content_source(
                    subject,
                    cmd,
                    video_id,
                    title=extracted_title,
                    source_metadata=metadata.model_dump(),
                )

            # Update Job with source info and status
            self.ingestion_service.update_job(
                job_id=ingestion.id,
                content_source_id=source.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Downloading & splitting transcript...",
                current_step=1,
                total_steps=4,
                source_title=extracted_title,
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "processing",
                    "step": "extracting",
                    "title": extracted_title,
                },
            )

            # 4. Extract and split transcript (CRITICAL STEP)
            with self._lock:
                docs = self._extract_and_split(cmd, video_id, yt_extractor=yt_extractor)

            if not docs:
                raise ValueError(
                    f"No transcript chunks generated for video {video_id}. It might be too short or have no available subtitles."
                )

            # Ensure source has latest title
            self.cs_service._repo.update_title(
                content_source_id=source.id, title=extracted_title
            )

            self._mark_source_processing(source)

            # 5. Embed and Index
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
            chunks = self._build_chunk_entities(
                docs, source, subject, cmd, job_id=ingestion.id
            )
            self._persist_chunks(chunks)

            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.PROCESSING,
                status_message="Generating embeddings and indexing...",
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
            with self._lock:
                created_ids = self._index_chunks(chunks)

            self.ingestion_service.update_job(
                job_id=ingestion.id,
                status=IngestionJobStatus.FINISHED,
                status_message=f"Ingestion complete: {cmd.title or video_url}",
                current_step=4,
                total_steps=4,
                chunks_count=len(chunks),
            )
            self.event_bus.publish(
                "ingestion_status",
                {
                    "job_id": str(ingestion.id),
                    "status": "completed",
                    "title": cmd.title or video_url,
                    "source_id": str(source.id),
                    "chunks_count": len(chunks),
                },
            )
            total_tokens = sum(
                c.tokens_count for c in chunks if c.tokens_count is not None
            )
            max_tokens = cmd.tokens_per_chunk
            self._finish_ingestion(
                source,
                len(chunks),
                total_tokens,
                max_tokens,
                source_metadata=metadata.model_dump(),
            )

            return {
                "video_url": video_url,
                "video_id": video_id,
                "job_id": ingestion.id,
                "skipped": False,
                "created_chunks": len(chunks),
                "vector_ids": created_ids,
                "source_id": source.id,
            }

        except (
            YoutubeVideoPrivateException,
            YoutubeVideoUnplayableException,
            YoutubeTranscriptNotFoundException,
            YoutubeTranscriptsDisabledException,
        ) as e:
            error_msg = str(e)
            logger.warning(
                "Known limitation for video",
                context={
                    "video_id": video_id,
                    "video_url": video_url,
                    "error": error_msg,
                },
            )

            if ingestion:
                try:
                    self.ingestion_service.update_job(
                        job_id=ingestion.id,
                        status=IngestionJobStatus.FAILED,
                        error_message=error_msg,
                    )
                    self.event_bus.publish(
                        "ingestion_status",
                        {
                            "job_id": str(ingestion.id),
                            "status": "failed",
                            "error": error_msg,
                        },
                    )
                except Exception as ej:
                    logger.error(
                        ej, context={"action": "fail_job", "job_id": str(ingestion.id)}
                    )

            if source:
                try:
                    self.cs_service.update_processing_status(
                        content_source_id=source.id,
                        status=ContentSourceStatus.CANCELLED,
                    )
                except Exception as ef:
                    logger.error(
                        ef,
                        context={
                            "action": "cancel_source",
                            "source_id": str(source.id),
                        },
                    )

            return {
                "video_url": video_url,
                "video_id": video_id,
                "job_id": ingestion.id if ingestion else None,
                "skipped": False,
                "cancelled": True,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(
                e,
                context={
                    "video_id": video_id,
                    "video_url": video_url,
                    "action": "process_single_video",
                },
            )

            # --- ROLLBACK LOGIC ---
            if ingestion:
                logger.info(
                    "Starting rollback for failed ingestion",
                    context={"job_id": str(ingestion.id), "video_id": video_id},
                )
                try:
                    # 1. Delete from SQL
                    sql_deleted = self.chunk_service.delete_by_job_id(ingestion.id)
                    # 2. Delete from Vector Store
                    vec_deleted = self.vector_service.delete_by_job_id(ingestion.id)
                    logger.info(
                        "Rollback completed",
                        context={
                            "job_id": str(ingestion.id),
                            "sql_deleted": sql_deleted,
                            "vector_deleted": vec_deleted,
                        },
                    )
                except Exception as er:
                    logger.error(
                        er,
                        context={
                            "action": "rollback_ingestion",
                            "job_id": str(ingestion.id),
                        },
                    )

            if source:
                try:
                    self._fail_ingestion(source)
                except Exception as ef:
                    logger.error(
                        ef,
                        context={"action": "fail_source", "source_id": str(source.id)},
                    )

            if ingestion:
                try:
                    self._fail_job(ingestion, error_msg)
                except Exception as ej:
                    logger.error(
                        ej, context={"action": "fail_job", "job_id": str(ingestion.id)}
                    )

            raise e

    def _fail_ingestion(self, source) -> None:
        self.cs_service.update_processing_status(
            content_source_id=source.id, status=ContentSourceStatus.FAILED
        )
        logger.info(
            "Content source marked as FAILED",
            context={"content_source_id": str(source.id)},
        )

    def _fail_job(self, ingestion, error_message: str) -> None:
        self.ingestion_service.update_job(
            job_id=ingestion.id,
            status=IngestionJobStatus.FAILED,
            error_message=error_message,
        )
        logger.info(
            "Ingestion job updated to FAILED", context={"job_id": str(ingestion.id)}
        )

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
                subject_id_val = (
                    cmd.subject_id
                    if isinstance(cmd.subject_id, uuid.UUID)
                    else uuid.UUID(str(cmd.subject_id))
                )
            except Exception as e:
                logger.error(
                    e, context={"subject_id": getattr(cmd, "subject_id", None)}
                )
                raise ValueError(f"Invalid subject_id provided: {e}")
            subject = self.ks_service.get_subject_by_id(subject_id_val)
            if subject is None:
                logger.error(
                    "KnowledgeSubject not found by id",
                    context={"subject_id": str(subject_id_val)},
                )
                raise ValueError(f"KnowledgeSubject with id {subject_id_val} not found")
            return subject

        if cmd.subject_name:
            subject = self.ks_service.get_by_name(cmd.subject_name)
            if subject is None:
                logger.error(
                    "KnowledgeSubject not found by name",
                    context={"subject_name": cmd.subject_name},
                )
                raise ValueError(
                    f"KnowledgeSubject with name '{cmd.subject_name}' not found"
                )
            return subject

        logger.error(
            "No subject identifier provided",
            context={"video_url": getattr(cmd, "video_url", None)},
        )
        raise ValueError("Either subject_id or subject_name must be provided")

    def _check_existing_source(self, video_id: str, subject_id: Optional[UUID] = None):
        logger.debug(
            "Checking existing content source",
            context={"external_source": video_id, "subject_id": subject_id},
        )
        return self.cs_service.get_by_source_info(
            source_type=SourceType.YOUTUBE,
            external_source=video_id,
            subject_id=subject_id,
        )

    def _create_content_source(
        self,
        subject,
        cmd: IngestYoutubeCommand,
        video_id: str,
        title: Optional[str] = None,
        source_metadata: Optional[dict] = None,
    ):
        source = self.cs_service.create_source(
            subject_id=subject.id,
            source_type=SourceType.YOUTUBE,
            external_source=video_id,
            title=title or cmd.title,
            language=cmd.language,
            status=ContentSourceStatus.ACTIVE,
            processing_status="pending",
            source_metadata=source_metadata,
        )
        logger.debug(
            "Content source created",
            context={"content_source_id": str(source.id), "external_source": video_id},
        )
        return source

    def _create_ingestion_job(
        self,
        source: Optional[Any] = None,
        external_source: Optional[str] = None,
        subject_id: Optional[UUID] = None,
    ):
        source_id = source.id if source else None
        ingestion = self.ingestion_service.create_job(
            content_source_id=source_id,
            status=IngestionJobStatus.STARTED,
            embedding_model=self.model_loader_service.model_name,
            pipeline_version="1.0",
            ingestion_type=SourceType.YOUTUBE.value,
            vector_store_type=self.vector_store_type,
            external_source=external_source,
            subject_id=subject_id,
        )
        if ingestion:
            logger.debug(
                "Ingestion job created",
                context={
                    "job_id": str(ingestion.id),
                    "content_source_id": str(source_id),
                },
            )
        return ingestion

    def _mark_source_processing(self, source) -> None:
        self.cs_service.update_processing_status(
            content_source_id=source.id, status=ContentSourceStatus.PROCESSING
        )
        logger.debug(
            "Content source marked as PROCESSING",
            context={"content_source_id": str(source.id)},
        )

    def _extract_and_split(
        self,
        cmd: IngestYoutubeCommand,
        video_id: str,
        yt_extractor: Optional[YoutubeExtractor] = None,
    ) -> List[Document]:
        logger.debug(
            "Starting extraction and transcript split", context={"video_id": video_id}
        )
        if yt_extractor is None:
            yt_extractor = YoutubeExtractor(video_id=video_id, language=cmd.language)

        ytts = YoutubeDataProcessService(
            model_loader_service=self.model_loader_service, yt_extractor=yt_extractor
        )
        effective_tokens = cmd.tokens_per_chunk
        docs: List[Document] = ytts.split_transcript(
            mode="tokens",
            tokens_per_chunk=effective_tokens,
            tokens_overlap=cmd.tokens_overlap,
        )

        logger.debug(
            "Transcript split completed",
            context={"video_id": video_id, "chunks": len(docs)},
        )
        return docs

    def _update_ingestion_processing(self, ingestion) -> None:
        self.ingestion_service.update_job(
            job_id=ingestion.id, status=IngestionJobStatus.PROCESSING
        )
        logger.debug(
            "Ingestion job updated to PROCESSING", context={"job_id": str(ingestion.id)}
        )
        self.event_bus.publish(
            "ingestion_status",
            {
                "job_id": str(ingestion.id),
                "status": "indexing",  # Using 'indexing' to represent PROCESSING phase
            },
        )

    def _build_chunk_entities(
        self,
        docs: List[Document],
        source,
        subject,
        cmd: IngestYoutubeCommand,
        job_id: UUID,
    ) -> List[ChunkEntity]:
        list_chunks: List[ChunkEntity] = []
        for i, doc in enumerate(docs):
            chunk_entity = ChunkEntity(
                id=uuid.uuid4(),
                job_id=job_id,
                content_source_id=source.id,
                source_type=SourceType(source.source_type),
                external_source=source.external_source,
                subject_id=subject.id,
                index=i,
                content=doc.page_content,
                tokens_count=doc.metadata.get("token_count"),
                extra={**doc.metadata, "vector_store_type": self.vector_store_type},
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
        logger.debug(
            "Persisted chunks to SQL repository", context={"num_chunks": len(chunks)}
        )

    def _index_chunks(self, chunks: List[ChunkEntity]) -> List[str]:
        created_ids = self.vector_service.index_documents(chunks)
        logger.debug(
            "Indexed chunks in vector store",
            context={"indexed_count": len(created_ids)},
        )
        return created_ids

    def _finish_ingestion(
        self,
        source,
        num_chunks: int,
        total_tokens: int = 0,
        max_tokens_per_chunk: Optional[int] = None,
        source_metadata: Optional[dict] = None,
    ) -> None:
        dims = getattr(self.model_loader_service, "dimensions", None)
        dims_val: int = int(dims) if dims is not None else 0

        self.cs_service.finish_ingestion(
            content_source_id=source.id,
            embedding_model=self.model_loader_service.model_name,
            dimensions=dims_val,
            chunks=num_chunks,
            total_tokens=total_tokens,
            max_tokens_per_chunk=max_tokens_per_chunk,
            source_metadata=source_metadata,
        )
        logger.info(
            "Ingestion finished",
            context={"content_source_id": str(source.id), "chunks": num_chunks},
        )

    def _finish_job(self, ingestion, chunks_count: Optional[int] = None) -> None:
        self.ingestion_service.update_job(
            job_id=ingestion.id,
            status=IngestionJobStatus.FINISHED,
            chunks_count=chunks_count,
        )
        logger.debug(
            "Ingestion job marked as FINISHED",
            context={"job_id": str(ingestion.id), "chunks": chunks_count},
        )
