import math
from typing import Literal, List, Tuple, Dict, Optional

from langchain_core.documents import Document
from youtube_transcript_api import FetchedTranscript

from src.config.logger import Logger
from src.domain.interfaces.services.mode_loader_service import IModelLoaderService
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

logger = Logger()


class YoutubeDataProcessService:
    """Splits the transcript into overlapping temporal windows or into token-sized chunks.

    Usage:
      - Time-based: tempo.split_transcript(transcript, window_size=30, overlap=5)
      - Token-based: tempo.split_transcript(transcript, mode='tokens', tokens_per_chunk=512, token_overlap=50)

    Token-based splitting usa o tokenizer do model_loader_service.models.
    Se não houver tokenizer, faz fallback para tiktoken.
    """

    def __init__(
        self, model_loader_service: IModelLoaderService, yt_extractor: YoutubeExtractor
    ):
        self.model_loader_service: IModelLoaderService = model_loader_service
        self.yt_extractor = yt_extractor

    def split_transcript(
        self,
        mode: Literal["time", "tokens"] = "tokens",
        time_window_size: int = 30,
        time_overlap: int = 5,
        tokens_per_chunk: int = 512,
        tokens_overlap: int = 30,
    ) -> List[Document]:
        """Split transcript. If `transcript` is provided it will be used instead of fetching again from YouTube."""
        video_id = self.yt_extractor.video_id
        context = {
            "window_size": time_window_size,
            "overlap": time_overlap,
            "mode": mode,
            "tokens_per_chunk": tokens_per_chunk,
            "token_overlap": tokens_overlap,
            "video_id": video_id,
        }
        logger.debug("Starting transcript splitting into windows...", context=context)

        transcript: FetchedTranscript = self.yt_extractor.extract_transcript()

        documents: List[Document] = []

        if not transcript:
            logger.warning("Empty transcription.", context=context)
            return documents

        if mode == "time" or not tokens_per_chunk:
            return self._split_by_time(
                transcript, time_window_size, time_overlap, context
            )

        if mode == "tokens":
            return self._split_by_tokens(
                transcript, tokens_per_chunk, tokens_overlap, context
            )

        logger.error("Unknown splitting mode.", context={**context, "mode": mode})
        raise ValueError(f"Unknown splitting mode: {mode}")

    def _split_by_time(
        self,
        transcript: FetchedTranscript,
        window_size: int,
        overlap: int,
        context: dict,
    ) -> List[Document]:
        step = window_size - overlap
        if step <= 0:
            logger.error("window_size must be greater than overlap", context=context)
            raise ValueError("window_size must be greater than overlap")

        total_duration = self._get_snippet_end(transcript[-1])
        windows = math.ceil(total_duration / step)
        documents: List[Document] = []

        logger.debug(
            "Splitting transcript by time windows",
            context={**context, "total_duration": total_duration, "windows": windows},
        )
        for i in range(windows):
            start = i * step
            end = start + window_size
            window_text = [
                self._get_text(snippet)
                for snippet in transcript
                if start <= self._get_start(snippet) < end
            ]

            if window_text:
                doc_context = {
                    **context,
                    "window_index": i,
                    "window_start": start,
                    "window_end": end,
                    "window_text_length": len(window_text),
                }
                logger.debug("Creating document for time window", context=doc_context)
                documents.append(
                    self._create_document(
                        window_text, start, end, self._get_video_id(transcript)
                    )
                )

        logger.debug(
            "Transcript split into windows",
            context={**context, "windows_created": len(documents)},
        )
        return documents

    def _split_by_tokens(
        self,
        transcript: FetchedTranscript,
        tokens_per_chunk: int,
        token_overlap: int,
        context: dict,
    ) -> List[Document]:
        step = tokens_per_chunk - token_overlap
        if step <= 0:
            logger.error(
                "token_overlap must be smaller than tokens_per_chunk", context=context
            )
            raise ValueError("token_overlap must be smaller than tokens_per_chunk")

        tokenizer = getattr(self.model_loader_service.model, "tokenizer", None)
        if tokenizer is None:
            logger.error("No tokenizer available in the models.", context=context)
            raise RuntimeError(
                "No tokenizer available in the models. Please configure a tokenizer in model_loader_service.models."
            )

        token_ids, token_meta = self._tokenize_transcript(
            transcript, tokenizer, context
        )
        documents = self._create_token_chunks(
            token_ids, token_meta, tokens_per_chunk, step, transcript, context
        )
        logger.debug(
            "Transcript split into token windows",
            context={**context, "token_windows_created": len(documents)},
        )
        return documents

    def _tokenize_transcript(
        self, transcript: FetchedTranscript, tokenizer, context: dict
    ) -> Tuple[List[int], List[Dict]]:
        token_ids = []
        token_meta = []

        def _encode(txt: str):
            try:
                return tokenizer.encode(txt, add_special_tokens=False)
            except TypeError:
                return tokenizer.encode(txt)

        logger.debug(
            "Tokenizing transcript",
            context={**context, "transcript_length": len(transcript)},
        )
        for idx, snippet in enumerate(transcript):
            text = self._get_text(snippet)
            start_time = self._get_start(snippet)
            duration = self._get_duration(snippet)
            end_time = start_time + (duration or 0.0)

            if not text:
                logger.debug(
                    "Skipping empty snippet", context={**context, "snippet_index": idx}
                )
                continue

            ids = _encode(text)
            logger.debug(
                "Tokenized snippet",
                context={**context, "snippet_index": idx, "token_count": len(ids)},
            )
            for t_id in ids:
                token_ids.append(t_id)
                token_meta.append(
                    {"start": start_time, "end": end_time, "snippet_index": idx}
                )
        logger.debug(
            "Tokenization complete", context={**context, "total_tokens": len(token_ids)}
        )
        return token_ids, token_meta

    def _create_token_chunks(
        self,
        token_ids: List[int],
        token_meta: List[Dict],
        tokens_per_chunk: int,
        step: int,
        transcript: FetchedTranscript,
        context: dict,
    ) -> List[Document]:
        n = len(token_ids)
        i = 0
        documents: List[Document] = []

        def _decode(_ids: list):
            try:
                return self.model_loader_service.model.tokenizer.decode(
                    _ids, skip_special_tokens=True
                )
            except TypeError:
                return self.model_loader_service.model.tokenizer.decode(_ids)
            except AttributeError:
                return str(_ids)

        logger.debug(
            "Creating token chunks",
            context={
                **context,
                "total_tokens": n,
                "tokens_per_chunk": tokens_per_chunk,
                "step": step,
            },
        )
        while i < n:
            chunk_ids = token_ids[i : i + tokens_per_chunk]
            chunk_meta = token_meta[i : i + tokens_per_chunk]

            chunk_text = _decode(chunk_ids) if chunk_ids else ""

            if chunk_meta:
                window_start = min(m["start"] for m in chunk_meta)
                window_end = max(m["end"] for m in chunk_meta)
            else:
                window_start = 0.0
                window_end = 0.0

            chunk_context = {
                **context,
                "chunk_index": i // step,
                "window_start": window_start,
                "window_end": window_end,
                "token_count": len(chunk_ids),
            }
            logger.debug("Creating document for token chunk", context=chunk_context)
            documents.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "window_start": window_start,
                        "window_end": window_end,
                        "video_id": self._get_video_id(transcript),
                        "token_count": len(chunk_ids),
                    },
                )
            )
            i += step
        logger.debug(
            "Token chunk creation complete",
            context={**context, "chunks_created": len(documents)},
        )
        return documents

    @classmethod
    def _get_text(cls, snippet) -> str:
        return getattr(snippet, "text", "")

    @classmethod
    def _get_start(cls, snippet) -> float:
        return float(getattr(snippet, "start", 0.0))

    @classmethod
    def _get_duration(cls, snippet) -> float:
        return float(getattr(snippet, "duration", 0.0))

    def _get_snippet_end(self, snippet) -> float:
        return self._get_start(snippet) + self._get_duration(snippet)

    @classmethod
    def _get_video_id(cls, transcript) -> str | None:
        return getattr(transcript, "video_id", None)

    def _create_document(
        self,
        text_segments: List[str],
        start: float,
        end: float,
        video_id: Optional[str],
    ) -> Document:
        content = " ".join(text_segments)

        # Calculate tokens if tokenizer is available
        token_count = None
        tokenizer = getattr(self.model_loader_service.model, "tokenizer", None)
        if tokenizer:
            try:
                tokens = tokenizer.encode(content, add_special_tokens=False)
                token_count = len(tokens)
            except Exception:
                try:
                    tokens = tokenizer.encode(content)
                    token_count = len(tokens)
                except Exception:
                    pass

        return Document(
            page_content=content,
            metadata={
                "window_start": start,
                "window_end": end,
                "video_id": video_id,
                "token_count": token_count,
            },
        )
