from typing import Callable, Any
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType
from src.application.use_cases.ingest_youtube_use_case import IngestYoutubeUseCase
from src.config.logger import Logger

logger = Logger()

def run_youtube_ingestion(get_services_func: Callable[[], dict[str, Any]], video_url: str, subject_id: str, pre_job_id: str, 
                           data_type: YoutubeDataType = YoutubeDataType.VIDEO,
                           tokens_per_chunk: int = 512, tokens_overlap: int = 50):
    """Background job to run YouTube ingestion use case.
    
    This function is intended to be called by a background worker (e.g. ThreadPoolExecutor).
    It initializes the full service stack and executes the IngestYoutubeUseCase.
    """
    logger.info("Starting background YouTube ingestion", context={
        "video_url": video_url, 
        "job_id": pre_job_id, 
        "data_type": data_type.value,
        "tokens": tokens_per_chunk,
        "overlap": tokens_overlap
    })
    
    try:
        init_result = get_services_func()
        if not init_result or not init_result.get('ok'):
            error_msg = init_result.get('error', 'Unknown initialization error')
            logger.error(f"Failed to initialize services for background job: {error_msg}")
            raise RuntimeError(f"Service initialization failed: {error_msg}")
            
        svc = init_result['services']
        
        use_case = IngestYoutubeUseCase(
            ks_service=svc.get("ks_service"),
            cs_service=svc.get("cs_service"),
            ingestion_service=svc.get("ingestion_service"),
            model_loader_service=svc.get("model_loader"),
            embedding_service=svc.get("embedding_service"),
            chunk_service=svc.get("chunk_service"),
            vector_service=svc.get("vector_service"),
        )
        
        cmd = IngestYoutubeCommand(
            video_url=video_url, 
            subject_id=subject_id, 
            data_type=data_type,
            ingestion_job_id=pre_job_id,
            tokens_per_chunk=tokens_per_chunk,
            tokens_overlap=tokens_overlap
        )
        
        result = use_case.execute(cmd)
        logger.info("Background YouTube ingestion completed successfully", context={"job_id": pre_job_id or "playlist_background_job"})
        return result
    except Exception as e:
        logger.error(f"Error in background YouTube ingestion: {e}", context={"job_id": pre_job_id or "playlist_background_job"})
        raise
