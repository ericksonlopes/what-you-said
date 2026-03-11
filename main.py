import uuid
from datetime import datetime, timezone
from pprint import pprint
from typing import List

from langchain_core.documents import Document

from src.config.logger import Logger
from src.config.settings import settings
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.external_source_enum_entity import ExternalSourceEnum
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.repository.weaviate.chunk_repository import WeaviateChunkRepository
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.services.embeddding_service import EmbeddingService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_service import YoutubeDataService
from src.infrastructure.services.youtube_weaviate_service import YouTubeService

logger = Logger()

if __name__ == '__main__':
    video_id = "VQnM8Y3RIyM"
    language = "pt"

    pprint(settings.model_dump())

    model = settings.model_embedding.name
    model_loader = ModelLoaderService(model)
    embedding_service = EmbeddingService(model_loader)

    yt_extractor = YoutubeExtractor(video_id=video_id)
    ytts = YoutubeDataService(model_loader_service=model_loader, yt_extractor=yt_extractor)
    result: List[Document] = ytts.split_transcript(mode="tokens", tokens_per_chunk=512, tokens_overlap=30)

    wea_client = WeaviateClient(weaviate_config=settings.weaviate)

    repository = WeaviateChunkRepository(weaviate_client=wea_client, embedding_service=embedding_service,
                                         collection_name=settings.weaviate.collection_name_youtube_transcripts)

    service = YouTubeService(repository=repository)

    list_chunk: List[ChunkEntity] = []

    for doc in result:
        chunk_entity = ChunkEntity(
            id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            content_source_id=uuid.uuid4(),
            source_type=ExternalSourceEnum.YOUTUBE,
            external_source=video_id,
            subject_id=uuid.uuid4(),
            content=doc.page_content,
            extra=doc.metadata,
            language="pt",
            embedding_model=model_loader.model_name,
            created_at=datetime.now(timezone.utc),
            version_number=1
        )
        list_chunk.append(chunk_entity)

    created_ids = service.index_documents(list_chunk)

    query_result: List[ChunkEntity] = service.search_by_video_id(video_id=video_id)

    query = service.search(query="coxinha", top_k=1)

    service.delete_by_video_id(video_id=video_id)
