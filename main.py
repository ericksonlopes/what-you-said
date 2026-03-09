from pprint import pprint
from typing import List

from langchain_core.documents import Document
from youtube_transcript_api import FetchedTranscript

from src.config.settings import settings
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_text_temporal_splitter_service import YoutubeTranscriptSplitterService

if __name__ == '__main__':
    v_id = "VQnM8Y3RIyM"
    language = "pt"

    model = settings.MODEL_EMBEDDING_NAME
    model_loader = ModelLoaderService(model)

    yt_extractor = YoutubeExtractor(video_id=v_id)

    transcript: FetchedTranscript = yt_extractor.extract_transcript(language=language)
    metadata = yt_extractor.extract_metadata()

    ytts = YoutubeTranscriptSplitterService(model_loader)
    result: List[Document] = ytts.split_transcript(transcript, mode="tokens", tokens_per_chunk=512, token_overlap=5)
    pprint(result)
    pprint(metadata)
