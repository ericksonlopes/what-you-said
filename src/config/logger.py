import logging
from src.infrastructure.loggers.std_logger import StdLogger, InterceptHandler

LOG_FORMAT = "{asctime} | {levelname:<8} | {filepath}:{funcName}:{lineno} | {message} | {context}"


class Logger:
    def __init__(self) -> None:
        self._logger = StdLogger(LOG_FORMAT)

    def __getattr__(self, name):
        return getattr(self._logger, name)

    def get_intercept_handler(self):
        return InterceptHandler(self)


def setup_logging():
    """Setup logging to intercept all standard library logs and redirect to our Logger."""
    custom_logger = Logger()
    intercept_handler = custom_logger.get_intercept_handler()

    # Configure root logger to only show ERRORs by default for all libraries
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.addHandler(intercept_handler)
    root_logger.setLevel(logging.ERROR)

    # Configure our app's 'src' logger to show normal logs (INFO, DEBUG, etc.)
    src_logger = logging.getLogger("src")
    src_logger.setLevel(logging.INFO)
    src_logger.propagate = True

    # Force specific known infrastructure loggers to ERROR to prevent their default setups from overriding
    silence_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "starlette",
        "sqlalchemy",
        "sqlalchemy.engine",
        "httpcore",
        "httpx",
        "urllib3",
        "chromadb",
        "sentence_transformers",
        "weaviate",
        "faiss",
        "onnxruntime",
    ]

    for logger_name in silence_loggers:
        logging_logger = logging.getLogger(logger_name)
        for handler in logging_logger.handlers[:]:
            logging_logger.removeHandler(handler)
        logging_logger.addHandler(intercept_handler)
        logging_logger.propagate = False
        logging_logger.setLevel(logging.ERROR)

    # Allow verbose/visible logs for specific new libraries (Docling, RapidOCR)
    verbose_loggers = [
        "docling",
        "docling_core",
        "rapidocr_onnxruntime",
        "huggingface_hub",
        "transformers",
    ]

    for logger_name in verbose_loggers:
        logging_logger = logging.getLogger(logger_name)
        for handler in logging_logger.handlers[:]:
            logging_logger.removeHandler(handler)
        logging_logger.addHandler(intercept_handler)
        logging_logger.propagate = False
        logging_logger.setLevel(logging.INFO)

    return custom_logger
