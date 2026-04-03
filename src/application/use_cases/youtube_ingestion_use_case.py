import concurrent.futures
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from langchain_core.documents import Document

from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType
from src.application.dtos.results.ingest_youtube_result import IngestYoutubeResult
from src.config.logger import Logger
from src.config.settings import settings
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.domain.exception.youtube_exceptions import (
    YoutubeVideoPrivateException,
    YoutubeVideoUnplayableException,
    YoutubeTranscriptNotFoundException,
    YoutubeTranscriptsDisabledException,
    YoutubeNetworkException,
)
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
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
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

logger = Logger()


class YoutubeIngestionUseCase:
    """Orquestra a ingestão de vídeos do YouTube usando métodos por step para facilitar testes e logs.

    Agora suporta ingestão de múltiplos vídeos (video_urls) e diferenciação por data_type (VIDEO/PLAYLIST).
    """

    PIPELINE_VERSION = "1.0"

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
        self._lock = threading.Lock()

    def _report_status(
        self,
        job_id: Any,
        status: str,
        step: Optional[str] = None,
        message: Optional[str] = None,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = 4,
        **extra,
    ) -> None:
        """Centralized status reporting for both DB and EventBus."""
        if not job_id:
            return

        # 1. Update Ingestion Job in Database
        job_status_map = {
            "started": IngestionJobStatus.STARTED,
            "processing": IngestionJobStatus.PROCESSING,
            "indexing": IngestionJobStatus.PROCESSING,
            "completed": IngestionJobStatus.FINISHED,
            "failed": IngestionJobStatus.FAILED,
            "cancelled": IngestionJobStatus.CANCELLED,
        }

        db_status = job_status_map.get(status, IngestionJobStatus.PROCESSING)
        if self.ingestion_service and job_id != "new":
            self.ingestion_service.update_job(
                job_id=job_id,
                status=db_status,
                status_message=message,
                current_step=current_step,
                total_steps=total_steps,
                error_message=extra.get("error") if status == "failed" else None,
                chunks_count=extra.get("chunks_count"),
                source_title=extra.get("title"),
                content_source_id=extra.get("content_source_id"),
            )

        # 2. Publish to Event Bus
        event_payload = {
            "job_id": str(job_id),
            "status": status,
            "step": step,
            **extra,
        }
        if message:
            event_payload["message"] = message

        self.event_bus.publish("ingestion_status", event_payload)

    def _resolve_video_list(self, cmd: IngestYoutubeCommand) -> List[str]:
        """Resolves whether we are dealing with a playlist or a list of videos."""
        if cmd.data_type == YoutubeDataType.PLAYLIST:
            playlist_url = cmd.video_url or (
                cmd.video_urls[0] if cmd.video_urls else None
            )
            if not playlist_url:
                raise ValueError("No video_url provided for playlist")

            logger.info("Processing playlist", context={"playlist_url": playlist_url})
            video_list = YoutubeExtractor.extract_playlist_videos(playlist_url)
            if not video_list:
                logger.warning(
                    "No videos found in playlist",
                    context={"playlist_url": playlist_url},
                )
                raise ValueError(
                    f"No videos found in playlist: {playlist_url}. Verify if the URL is valid and public."
                )
            return video_list

        video_list = []
        if cmd.video_urls:
            video_list = [v for v in cmd.video_urls if v is not None]
        elif cmd.video_url:
            video_list = [cmd.video_url]

        if not video_list:
            raise ValueError("No video_url(s) provided")

        return video_list

    def _process_video_batch(
        self,
        video_list: List[str],
        subject: Any,
        cmd: IngestYoutubeCommand,
        result: IngestYoutubeResult,
    ) -> None:
        """Processes a list of videos in batches with adaptive throttling."""
        batch_size = settings.youtube.throttle_batch_size
        wait_time = settings.youtube.throttle_wait_seconds
        current_wait_time = wait_time

        def process_video_task(url: str) -> Dict[str, Any]:
            try:
                vid_id = self._extract_video_id_from_url(url)
                if not vid_id:
                    raise ValueError(f"Unable to extract video id from url: {url}")
                # Use a separate variable or cast for Mypy
                video_id_str: str = str(vid_id)
                # subject is Any in _process_video_batch signature
                return self._process_single_video(url, video_id_str, subject, cmd)
            except YoutubeNetworkException as e:
                logger.error(
                    e,
                    context={
                        "video_url": url,
                        "video_id": vid_id,
                        "error_type": "network_error",
                    },
                )
                return {
                    "video_url": url,
                    "video_id": vid_id,
                    "error": str(e),
                    "is_network_error": True,
                }
            except Exception as e:
                logger.error(
                    e,
                    context={
                        "video_url": url,
                        "video_id": vid_id,
                        "action": "process_video",
                    },
                )
                return {"video_url": url, "video_id": vid_id, "error": str(e)}

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
                futures = [executor.submit(process_video_task, url) for url in batch]
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
                        result.vector_ids.extend(single_result.get("vector_ids", []))

            # Adaptive Throttling
            if batch_has_network_error:
                current_wait_time = min(current_wait_time * 2, 600)
                logger.warning(
                    "Network error detected. Increasing wait time",
                    context={"new_wait_time": current_wait_time},
                )

            # Wait if there are more batches
            if i + batch_size < len(video_list):
                total_wait = current_wait_time + random.uniform(0, 5)
                logger.debug(
                    "Throttling: waiting before next batch",
                    context={"wait_time": total_wait},
                )
                time.sleep(total_wait)

    def _finalize_parent_job(
        self, ingestion: Any, result: IngestYoutubeResult, any_failed: bool
    ) -> None:
        """Updates the status of the main tracking job."""
        if any_failed:
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
                # Only known limitations/cancellations
                cancelled_msgs = [
                    r["error"]
                    for r in result.video_results
                    if r.get("cancelled", False)
                ]
                summary = f"Partial ingestion: {len(cancelled_msgs)} items skipped (private/unplayable)."
                self._report_status(
                    job_id=ingestion.id,
                    status="completed",
                    message=summary,
                    chunks_count=result.created_chunks,
                )
        else:
            self._finish_job(ingestion, chunks_count=result.created_chunks)

    def _finalize_parent_source(
        self, source: Any, result: IngestYoutubeResult, cmd: IngestYoutubeCommand
    ) -> None:
        """Updates the status of the parent source."""
        real_errors = [
            r["error"]
            for r in result.video_results
            if "error" in r and not r.get("cancelled", False)
        ]

        if real_errors:
            self._fail_ingestion(source)
        elif cmd.data_type != YoutubeDataType.PLAYLIST:
            # For single videos, if not already DONE/FAILED
            current_source = self.cs_service.get_by_id(source.id)
            if current_source and current_source.processing_status not in [
                ContentSourceStatus.FAILED,
                ContentSourceStatus.DONE,
            ]:
                # Handled inside _process_single_video usually, but here for safety
                pass

    def execute(self, cmd: IngestYoutubeCommand) -> IngestYoutubeResult:
        self._report_status(
            job_id=cmd.ingestion_job_id if cmd.ingestion_job_id else "new",
            status="started",
            video_url=cmd.video_url,
        )
        logger.info(
            "STARTING YOUTUBE INGESTION PIPELINE",
            context={
                "video_url": getattr(cmd, "video_url", None),
                "video_urls": getattr(cmd, "video_urls", None),
                "subject_id": getattr(cmd, "subject_id", None),
                "data_type": getattr(cmd, "data_type", None),
            },
        )

        ingestion = None
        source = None
        if cmd.ingestion_job_id:
            try:
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
            video_list = self._resolve_video_list(cmd)

            result = IngestYoutubeResult()
            result.created_chunks = 0  # Pre-initialize to 0 for counters
            if ingestion:
                result.job_id = ingestion.id
                self._update_ingestion_processing(ingestion)

            self._process_video_batch(video_list, subject, cmd, result)

            # 1. Determine overall status
            any_failed = any("error" in r for r in result.video_results)

            # 2. Update the parent Tracking Job
            if ingestion:
                self._finalize_parent_job(ingestion, result, any_failed)

            # 3. For single video ingestion, if it fails, raise error for API
            is_batch = len(video_list) > 1
            if (
                any_failed
                and cmd.data_type != YoutubeDataType.PLAYLIST
                and not is_batch
            ):
                failed_item = next(r for r in result.video_results if "error" in r)
                raise ValueError(failed_item["error"])

            # 4. Update the parent Source if applicable
            if source:
                self._finalize_parent_source(source, result, cmd)

            logger.info(
                "YouTube ingestion completed",
                context={
                    "job_ids": [
                        r.get("job_id") for r in result.video_results if r.get("job_id")
                    ]
                    or cmd.ingestion_job_id,
                    "chunks": result.created_chunks,
                    "total_videos": len(result.video_results),
                    "skipped": sum(
                        1 for r in result.video_results if r.get("skipped", False)
                    ),
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

            raise

    def _ensure_ingestion_context(
        self, video_id: str, subject_id: UUID, cmd: IngestYoutubeCommand
    ) -> tuple[Optional[Any], Optional[Any], bool]:
        """Ensures we have an IngestionJob and ContentSource context."""
        existing = self._check_existing_source(video_id, subject_id)

        # 1. Skip if already exists and done (not reprocessing)
        if (
            existing
            and existing.processing_status == "done"
            and not getattr(cmd, "reprocess", False)
        ):
            logger.info(
                "Source already exists and is DONE, skipping ingestion (reprocess=False)",
                context={"source_id": str(existing.id), "external_source": video_id},
            )
            try:
                failed_job = self.ingestion_service.create_job(
                    content_source_id=existing.id,
                    status=IngestionJobStatus.CANCELLED,
                    embedding_model=self.model_loader_service.model_name,
                    pipeline_version=self.PIPELINE_VERSION,
                    ingestion_type=SourceType.YOUTUBE.value,
                    vector_store_type=self.vector_store_type,
                )
                # Update with detailed messages
                self.ingestion_service.update_job(
                    job_id=failed_job.id,
                    status=IngestionJobStatus.CANCELLED,
                    error_message="Duplicate: this content has already been ingested.",
                    status_message=f"Skipped: {video_id} already exists",
                )
            except Exception:
                failed_job = None
            return existing, failed_job, True

        # 2. Get or create Job
        job = None
        jid = cmd.ingestion_job_id if hasattr(cmd, "ingestion_job_id") else None
        if jid:
            try:
                job_uuid = UUID(jid) if isinstance(jid, str) else jid
                job = self.ingestion_service.get_by_id(job_uuid)
            except Exception:
                pass

        if not job:
            job = self._create_ingestion_job(
                source=existing, external_source=video_id, subject_id=subject_id
            )

        return existing, job, False

    def _handle_reprocessing_cleanup(
        self, source: Any, job_id: UUID, video_id: str
    ) -> None:
        """Cleans up previous ingestion data if reprocessing."""
        logger.info(
            "REPROCESSING: Performing pre-ingestion cleanup",
            context={"source_id": str(source.id), "video_id": video_id},
        )
        try:
            sql_del = self.chunk_service.delete_by_content_source(
                content_source_id=source.id
            )
            vec_del = self.vector_service.delete_by_video_id(video_id=video_id)

            # Mark previous jobs as REPROCESSED
            self.ingestion_service.mark_previous_jobs_as_reprocessed(
                content_source_id=source.id, current_job_id=job_id
            )

            logger.info(
                "Reprocessing cleanup finished",
                context={"sql_deleted": sql_del, "vector_deleted": vec_del},
            )
        except Exception as ce:
            logger.warning(
                "Error during reprocessing cleanup",
                context={"source_id": str(source.id), "error": str(ce)},
            )

        self.cs_service.update_processing_status(
            content_source_id=source.id, status=ContentSourceStatus.PROCESSING
        )

    def _rollback_failed_ingestion(
        self, job_id: UUID, video_id: str, error_msg: str, source: Optional[Any] = None
    ) -> None:
        """Rolls back changes on failure."""
        logger.info(
            "Starting rollback for failed ingestion",
            context={"job_id": str(job_id), "video_id": video_id},
        )
        try:
            sql_deleted = self.chunk_service.delete_by_job_id(job_id=job_id)
            vec_deleted = self.vector_service.delete_by_job_id(job_id=job_id)
            logger.info(
                "Rollback completed",
                context={
                    "job_id": str(job_id),
                    "sql_deleted": sql_deleted,
                    "vector_deleted": vec_deleted,
                },
            )
        except Exception as er:
            logger.error(
                er, context={"action": "rollback_ingestion", "job_id": str(job_id)}
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

        if job_id:
            self._report_status(job_id=job_id, status="failed", error=error_msg)

    def _process_single_video(
        self, video_url: str, video_id: str, subject: Any, cmd: IngestYoutubeCommand
    ) -> Dict[str, Any]:
        """Orchestrates the ingestion of a single YouTube video."""
        logger.info(
            "Processing video", context={"video_id": video_id, "video_url": video_url}
        )

        # 1. Resolve source and job early
        source, ingestion, skipped = self._ensure_ingestion_context(
            video_id, subject.id, cmd
        )

        if skipped:
            return {
                "video_url": video_url,
                "video_id": video_id,
                "skipped": True,
                "reason": "source_exists_and_done",
                "source_id": source.id if source else None,
                "job_id": str(ingestion.id) if ingestion else None,
            }

        try:
            if ingestion is None:
                raise ValueError("Failed to create or retrieve ingestion job")

            # 2. Pre-cleanup for reprocessing
            if source and source.id and getattr(cmd, "reprocess", False):
                self._handle_reprocessing_cleanup(source, ingestion.id, video_id)

            # 3. Extract core metadata
            yt_extractor = YoutubeExtractor(video_id=video_id, language=cmd.language)
            metadata = yt_extractor.extract_metadata()
            extracted_title = (
                metadata.full_title
                or metadata.title
                or cmd.title
                or f"Video {video_id}"
            )

            # 4. Ensure source exists and is linked
            if source is None:
                source = self._create_content_source(
                    subject,
                    cmd,
                    video_id,
                    title=extracted_title,
                    source_metadata=metadata.model_dump(),
                )

            # Link job to source
            self._report_status(
                job_id=ingestion.id,
                status="processing",
                step="extracting",
                message="Downloading & splitting transcript...",
                current_step=1,
                title=extracted_title,
                content_source_id=source.id,
            )

            # 5. Extract and Index (The core steps)
            with self._lock:
                docs = self._extract_and_split(cmd, video_id, yt_extractor=yt_extractor)

            if not docs:
                raise ValueError(
                    f"No transcript chunks generated for video {video_id}."
                )

            self.cs_service.update_title(
                content_source_id=source.id, title=extracted_title
            )
            self._mark_source_processing(source)

            # 6. Embed and Persist
            self._report_status(
                job_id=ingestion.id,
                status="processing",
                step="embedding",
                message=f"Generating embeddings for {len(docs)} chunks...",
                current_step=2,
                chunks_count=len(docs),
            )
            chunks = self._build_chunk_entities(
                docs, source, subject, cmd, job_id=ingestion.id
            )
            self._persist_chunks(chunks)

            # 7. Vector Indexing
            self._report_status(
                job_id=ingestion.id,
                status="processing",
                step="indexing",
                message="Finalizing vector store index...",
                current_step=3,
            )
            with self._lock:
                created_ids = self._index_chunks(chunks)

            # 8. Success Finalization
            total_tokens = sum(
                c.tokens_count for c in chunks if c.tokens_count is not None
            )
            self._report_status(
                job_id=ingestion.id,
                status="completed",
                message=f"Ingestion complete: {extracted_title}",
                current_step=4,
                chunks_count=len(chunks),
                source_id=str(source.id),
            )

            self._finish_ingestion(
                source,
                len(chunks),
                total_tokens,
                cmd.tokens_per_chunk,
                metadata.model_dump(),
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
                context={"video_id": video_id, "error": error_msg},
            )

            if ingestion:
                self._report_status(
                    job_id=ingestion.id, status="failed", error=error_msg
                )
            if source:
                self.cs_service.update_processing_status(
                    content_source_id=source.id, status=ContentSourceStatus.CANCELLED
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
                e, context={"video_id": video_id, "action": "process_single_video"}
            )

            if ingestion:
                self._rollback_failed_ingestion(
                    ingestion.id, video_id, error_msg, source=source
                )

            raise

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

        # 1. Quick check for plain 11-char ID
        if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
            return url

        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if "youtu.be" in netloc:
            vid = parsed.path.lstrip("/")
            return vid or None

        if "youtube" in netloc:
            q = parse_qs(parsed.query)
            if "v" in q:
                vid = q["v"][0]
                if len(vid) == 11:
                    return vid

            path_parts = [p for p in parsed.path.split("/") if p]
            for i, part in enumerate(path_parts):
                if part in ("embed", "v", "shorts") and i + 1 < len(path_parts):
                    vid = path_parts[i + 1]
                    if len(vid) == 11:
                        return vid
            if path_parts:
                potential_id = path_parts[-1]
                # YouTube video IDs are strictly 11 characters.
                # Avoid common navigation sub-paths.
                if len(potential_id) == 11 and potential_id not in (
                    "videos",
                    "shorts",
                    "about",
                    "featured",
                    "playlists",
                ):
                    return potential_id

        # 2. Broader search: look for 11-char ID preceded by common prefixes or non-alphanumerics
        m = re.search(
            r"(?:v=|be/|embed/|shorts/|^|[^A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?:$|[^A-Za-z0-9_-])",
            url,
        )
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
