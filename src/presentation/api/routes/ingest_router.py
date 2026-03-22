import os
import shutil
import tempfile
from typing import Annotated, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi import UploadFile, File, Form

from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.use_cases.file_ingestion_use_case import FileIngestionUseCase
from src.application.use_cases.youtube_ingestion_use_case import YoutubeIngestionUseCase
from src.application.use_cases.web_scraping_use_case import WebScrapingUseCase
from src.application.workers import (
    run_file_ingestion_worker,
    run_youtube_ingestion_worker,
    run_web_ingestion_worker,
)
from src.config.logger import Logger
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.presentation.api.dependencies import (
    get_ingest_youtube_use_case,
    get_file_ingestion_use_case,
    get_web_scraping_use_case,
    get_task_queue_service,
)
from src.presentation.api.schemas.ingest_schemas import (
    IngestResponse,
    YoutubeIngestRequest,
    FileUrlIngestRequest,
    WebIngestRequest,
)

logger = Logger()
router = APIRouter()


@router.post(
    "/youtube",
    response_model=IngestResponse,
    responses={
        400: {"description": "Validation error or invalid request"},
        409: {"description": "Validation error"},
        500: {"description": "Internal server error during ingestion"},
    },
)
def ingest_youtube(
    request: Annotated[YoutubeIngestRequest, Body()],
    use_case: Annotated[YoutubeIngestionUseCase, Depends(get_ingest_youtube_use_case)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    """
    Ingest data from YouTube videos or playlists into the vector store.
    """
    logger.info(
        "API request to ingest youtube",
        context={"video_url": request.video_url, "video_urls": request.video_urls},
    )

    cmd = IngestYoutubeCommand(
        video_url=request.video_url,
        video_urls=request.video_urls,
        subject_id=request.subject_id,
        subject_name=request.subject_name,
        title=request.title,
        language=request.language,
        tokens_per_chunk=request.tokens_per_chunk,
        tokens_overlap=request.tokens_overlap,
        data_type=request.data_type,
        ingestion_job_id=request.ingestion_job_id,
        reprocess=request.reprocess,
    )

    # If it's a reprocess request, we always run it in background
    if request.reprocess:
        logger.info("Running reprocessing in background via queue")
        task_queue.enqueue(
            run_youtube_ingestion_worker,
            cmd,
            task_title=request.title or request.video_url or "YouTube Ingestion",
            metadata={"job_id": str(request.ingestion_job_id)}
            if request.ingestion_job_id
            else {},
        )
        return IngestResponse(
            skipped=False, reason="Reprocessing started in background queue."
        )

    try:
        result = use_case.execute(cmd)

        # Check if the ingestion was skipped because the source already exists
        if result.skipped:
            raise HTTPException(
                status_code=409,
                detail=result.reason or "This content has already been ingested.",
            )

        return result
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(
            "Validation error in youtube ingestion", context={"error": str(ve)}
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(e, context={"action": "youtube_ingestion"})
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/file",
    response_model=Dict,
    responses={
        400: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def ingest_file(
    use_case: Annotated[FileIngestionUseCase, Depends(get_file_ingestion_use_case)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
    file: Annotated[UploadFile, File(...)],
    subject_id: Annotated[Optional[str], Form()] = None,
    subject_name: Annotated[Optional[str], Form()] = None,
    title: Annotated[Optional[str], Form()] = None,
    language: Annotated[str, Form()] = "pt",
    tokens_per_chunk: Annotated[int, Form()] = 512,
    tokens_overlap: Annotated[int, Form()] = 50,
    do_ocr: Annotated[bool, Form()] = False,
):
    """
    Upload and ingest a file using Docling.
    """
    logger.info(
        "API request to ingest file",
        context={"file_name": file.filename, "subject_id": subject_id},
    )

    # Validate IDs
    s_id = None
    if subject_id:
        try:
            s_id = UUID(subject_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subject_id format")

    # Validate filename
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="File name is missing")

    # Save uploaded file to a temporary location
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cmd = IngestFileCommand(
        file_path=temp_path,
        file_name=filename,
        subject_id=s_id,
        subject_name=subject_name,
        title=title,
        language=language,
        tokens_per_chunk=tokens_per_chunk,
        tokens_overlap=tokens_overlap,
        do_ocr=do_ocr,
    )

    cmd.delete_after_ingestion = True

    task_queue.enqueue(
        run_file_ingestion_worker,
        cmd,
        task_title=filename,
        metadata={"filename": filename},
    )

    return {
        "message": "File upload successful, ingestion started in background.",
        "file_name": file.filename,
    }


@router.post(
    "/file-url",
    response_model=Dict,
    responses={
        400: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def ingest_file_url(
    request: Annotated[FileUrlIngestRequest, Body()],
    use_case: Annotated[FileIngestionUseCase, Depends(get_file_ingestion_use_case)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    """
    Ingest a file from a URL.
    """
    # Determine filename from URL
    filename = request.file_url.split("/")[-1].split("?")[0]
    if not filename or "." not in filename:
        filename = "downloaded_file"

    # Validate IDs
    s_id = None
    if request.subject_id:
        try:
            s_id = UUID(request.subject_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subject_id format")

    # Delegate download/extraction to Docling in the background worker
    cmd = IngestFileCommand(
        file_url=request.file_url,
        file_name=filename,
        subject_id=s_id,
        subject_name=request.subject_name,
        title=request.title or filename,
        language=request.language,
        tokens_per_chunk=request.tokens_per_chunk,
        tokens_overlap=request.tokens_overlap,
        do_ocr=request.do_ocr,
    )

    task_queue.enqueue(
        run_file_ingestion_worker,
        cmd,
        task_title=filename,
        metadata={"filename": filename, "url": request.file_url},
    )

    return {
        "message": "File URL ingestion started in background.",
        "file_name": filename,
    }


@router.post(
    "/web",
    response_model=Dict,
    responses={
        400: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def ingest_web(
    request: Annotated[WebIngestRequest, Body()],
    use_case: Annotated[WebScrapingUseCase, Depends(get_web_scraping_use_case)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    """
    Ingest content from a URL using Crawl4AI.
    """
    logger.info(
        "API request to ingest web content",
        context={"url": request.url, "subject_id": request.subject_id},
    )

    from src.application.dtos.commands.ingest_web_command import IngestWebCommand

    cmd = IngestWebCommand(
        url=request.url,
        css_selector=request.css_selector,
        title=request.title,
        subject_id=request.subject_id,
        subject_name=request.subject_name,
        language=request.language,
        tokens_per_chunk=request.tokens_per_chunk,
        tokens_overlap=request.tokens_overlap,
        depth=request.depth,
        ingestion_job_id=request.ingestion_job_id,
        reprocess=request.reprocess,
    )

    task_queue.enqueue(
        run_web_ingestion_worker,
        cmd,
        task_title=request.title or request.url,
        metadata={"url": request.url},
    )

    return {
        "message": "Web scraping ingestion started in background.",
        "url": request.url,
    }
