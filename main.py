from pprint import pprint
from typing import List

from langchain_core.documents import Document

from src.config.settings import settings
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_service import YoutubeDataService

if __name__ == '__main__':
    v_id = "VQnM8Y3RIyM"
    language = "pt"

    model = settings.MODEL_EMBEDDING_NAME
    model_loader = ModelLoaderService(model)

    yt_extractor = YoutubeExtractor(video_id=v_id)

    ytts = YoutubeDataService(model_loader_service=model_loader, yt_extractor=yt_extractor)
    result: List[Document] = ytts.split_transcript(mode="tokens", tokens_per_chunk=512, tokens_overlap=30)

    pprint(result)
