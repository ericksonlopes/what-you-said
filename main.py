from pprint import pprint
from typing import List

from langchain_core.documents import Document
from src.config.logger import Logger
from src.config.settings import settings
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.repository.weaviate.youtube_repository import WeaviateYoutubeRepository
from src.infrastructure.services.embeddding_service import EmbeddingService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_service import YoutubeDataService

logger = Logger()

if __name__ == '__main__':
    v_id = "VQnM8Y3RIyM"
    language = "pt"

    pprint(settings.model_dump())

    model = settings.model_embedding.name
    model_loader = ModelLoaderService(model)
    embedding_service = EmbeddingService(model_loader)

    yt_extractor = YoutubeExtractor(video_id=v_id)
    ytts = YoutubeDataService(model_loader_service=model_loader, yt_extractor=yt_extractor)
    result: List[Document] = ytts.split_transcript(mode="tokens", tokens_per_chunk=512, tokens_overlap=30)

    wea_client = WeaviateClient(weaviate_config=settings.weaviate)

    repository = WeaviateYoutubeRepository(weaviate_client=wea_client, embedding_service=embedding_service,
                                           collection_name=settings.weaviate.collection_name_youtube_transcripts)
    repository.create_documents(result)

    query_result = repository.query("Aqui tem coxinha?")

    repository.delete_by_video_id(video_id=v_id)
