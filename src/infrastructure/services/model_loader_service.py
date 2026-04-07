import logging
import threading
from typing import Any, ClassVar, Dict, Optional

import torch
import whisperx
from pyannote.audio import Inference, Model
from sentence_transformers import SentenceTransformer

from src.domain.interfaces.services.mode_loader_service import IModelLoaderService

logger = logging.getLogger(__name__)


class ModelLoaderService(IModelLoaderService):
    _instance: Optional["ModelLoaderService"] = None
    _lock = threading.Lock()
    _models: ClassVar[Dict[str, Any]] = {}
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelLoaderService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized and model_name is None:
            return

        self.model_name = model_name
        self._embedding_model: Optional[SentenceTransformer] = None
        self._initialized = True

    @property
    def max_seq_length(self) -> int:
        if self._embedding_model is None:
            self.load_model()
        return int(getattr(self._embedding_model, "max_seq_length", 0))

    @property
    def model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self.load_model()
        return self._embedding_model  # type: ignore

    @property
    def dimensions(self) -> int:
        if self._embedding_model is None:
            self.load_model()
        return int(self._embedding_model.get_sentence_embedding_dimension() or 0)  # type: ignore

    def load_model(self):
        if not self.model_name:
            raise ValueError("Model name not set for embedding model loading")

        with self._lock:
            if self._embedding_model is None:
                logger.info("Loading Embedding model: %s", self.model_name)
                self._embedding_model = SentenceTransformer(self.model_name)
        return self._embedding_model

    def get_whisper_model(
        self,
        model_size: str,
        device: str,
        compute_type: str,
        language: str | None = None,
    ):
        key = f"whisper_{model_size}_{device}_{compute_type}"
        with self._lock:
            if key not in ModelLoaderService._models:
                logger.info("Loading WhisperX model: %s (%s)", model_size, compute_type)
                ModelLoaderService._models[key] = whisperx.load_model(
                    model_size, device, compute_type=compute_type, language=language
                )
            return ModelLoaderService._models[key]

    def get_align_model(self, language_code: str, device: str):
        key = f"align_{language_code}_{device}"
        with self._lock:
            if key not in ModelLoaderService._models:
                logger.info("Loading Alignment model: %s", language_code)
                ModelLoaderService._models[key] = whisperx.load_align_model(
                    language_code=language_code, device=device
                )
            return ModelLoaderService._models[key]

    def get_diarization_pipeline(self, hf_token: str, device: str):
        key = f"diarize_{device}"
        with self._lock:
            if key not in ModelLoaderService._models:
                logger.info("Loading Diarization pipeline (pyannote 3.1)")
                from whisperx.diarize import DiarizationPipeline

                ModelLoaderService._models[key] = DiarizationPipeline(
                    model_name="pyannote/speaker-diarization-3.1",
                    token=hf_token,
                    device=device,
                )
            return ModelLoaderService._models[key]

    def get_voice_inference(self, hf_token: str, device: str):
        key = f"voice_inference_{device}"
        with self._lock:
            if key not in ModelLoaderService._models:
                logger.info("Loading Pyannote Voice Identification model")
                model = Model.from_pretrained(
                    "pyannote/wespeaker-voxceleb-resnet34-LM", use_auth_token=hf_token
                )
                if model is None:
                    raise RuntimeError("Failed to load Pyannote Model")
                ModelLoaderService._models[key] = Inference(
                    model, window="whole", device=torch.device(device)
                )
            return ModelLoaderService._models[key]

    def clear_cache(self):
        with self._lock:
            logger.info("Clearing model cache and VRAM")
            ModelLoaderService._models.clear()
            self._embedding_model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


# Singleton access for diarization workers
model_loader = ModelLoaderService()
