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

    # loggers to keep at INFO or DEBUG
    app_loggers = [None]  # Root logger

    # infrastructure loggers to silence or set to WARNING/ERROR
    silence_loggers = {
        "uvicorn": logging.WARNING,
        "uvicorn.access": logging.CRITICAL,  # Silence HTTP request logs
        "uvicorn.error": logging.ERROR,
        "fastapi": logging.WARNING,
        "starlette": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "httpcore": logging.WARNING,
        "httpx": logging.WARNING,
    }

    # Configure root and main loggers
    for logger_name in app_loggers:
        logging_logger = logging.getLogger(logger_name)
        for handler in logging_logger.handlers[:]:
            logging_logger.removeHandler(handler)
        logging_logger.addHandler(intercept_handler)
        logging_logger.setLevel(logging.INFO)

    # Configure infrastructure loggers with higher thresholds
    for logger_name, level in silence_loggers.items():
        logging_logger = logging.getLogger(logger_name)
        for handler in logging_logger.handlers[:]:
            logging_logger.removeHandler(handler)
        logging_logger.addHandler(intercept_handler)
        logging_logger.propagate = False
        logging_logger.setLevel(level)

    return custom_logger
