import os
from typing import Any
import torch
from sentence_transformers import SentenceTransformer
import logging
import transformers.utils.logging as transformers_logging
from huggingface_hub.utils import disable_progress_bars

# Force disable progress bars via environment variable before any imports
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from src.config.logger import Logger
from src.domain.interfaces.services.mode_loader_service import IModelLoaderService

logger = Logger()

# Redirect transformers logs to our custom logger
# Using ERROR level to silence the verbose loading reports and configs
transformers_logging.set_verbosity_error()
transformers_logging.disable_progress_bar()  # Explicitly disable transformers progress bars
transformers_logger = logging.getLogger("transformers")
transformers_logger.addHandler(logger.get_intercept_handler())
transformers_logger.propagate = False  # Prevent double logging

disable_progress_bars()


class ModelLoaderService(IModelLoaderService):
    _model_cache: dict[str, Any] = {}

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.load_model()

    def load_model(self):
        if self.model_name not in ModelLoaderService._model_cache:
            try:
                logger.info(
                    "Loading models",
                    context={"model_name": self.model_name, "device": self.device},
                )
                ModelLoaderService._model_cache[self.model_name] = SentenceTransformer(
                    self.model_name, device=self.device
                )
            except Exception as e:
                logger.error(f"Error loading models: {e}")
                raise RuntimeError(f"Failed to load models '{self.model_name}': {e}")

    @property
    def dimensions(self) -> int:
        dims = self.model.get_sentence_embedding_dimension()
        if dims is None:
            raise RuntimeError("Failed to determine model embedding dimensions")
        return int(dims)

    @property
    def max_seq_length(self) -> int:
        """Returns the maximum sequence length (tokens) the model can process."""
        try:
            return int(self.model.max_seq_length)
        except (AttributeError, TypeError):
            return 512

    @property
    def model(self) -> SentenceTransformer:
        if self.model_name not in ModelLoaderService._model_cache:
            # Attempt to (re)load the models; load_model will raise on failure.
            self.load_model()
        return ModelLoaderService._model_cache[self.model_name]
