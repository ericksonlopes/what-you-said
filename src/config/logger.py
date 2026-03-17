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
    
    # List of loggers to intercept
    loggers = [
        None,  # Root logger
    #     "uvicorn",
    #     "uvicorn.access",
    #     "uvicorn.error",
    #     "fastapi",
    #     "starlette",
    #     "sqlalchemy.engine"
    ]
    
    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        # Remove existing handlers to avoid duplicate logs
        for handler in logging_logger.handlers[:]:
            logging_logger.removeHandler(handler)
        
        logging_logger.addHandler(intercept_handler)
        # For root logger, we don't set propagate False, but for others we do
        if logger_name is not None:
            logging_logger.propagate = False
        
        logging_logger.setLevel(logging.INFO)

    return custom_logger
