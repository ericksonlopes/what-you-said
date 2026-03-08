import logging
import sys
from typing import Optional, Any

from src.config.settings import settings
from src.domain.infraestructure.logger.logger import ILogger
from src.infrastructure.logger.util import get_log_record


class StdLogger(ILogger):
    """
    Standard logger that uses Python's built-in logging instead of loguru.
    Keeps compatibility with the ILogger interface.
    """

    def __init__(self, log_format: str, name: Optional[str] = None) -> None:
        self.log_format = log_format
        self.service_name = name or "std-logger"

        # Create a unique logger instance to avoid conflicts
        self._logger = logging.getLogger(f'std_logger_{self.service_name}_{id(self)}')

        # Remove any existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Set the logger to accept all levels (NOTSET)
        # This prevents it from inheriting the root logger level
        self._logger.setLevel(logging.NOTSET)
        self._logger.propagate = False

        # Configure handler to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        # Also set the handler to accept all levels
        console_handler.setLevel(logging.NOTSET)

        # Simple formatter that just prints the formatted message
        formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # Force logger to not inherit from parent (bypass root logger's level)
        self._logger.parent = None

        self.allowed_levels = settings.allowed_log_levels

    def _is_allowed(self, level_name: str) -> bool:
        try:
            if not self.allowed_levels:
                return False
            level = getattr(logging, level_name.upper(), None)
            return level in self.allowed_levels
        except Exception:
            return True

    def _log(self, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        if not self._is_allowed(level):
            return
        ctx = get_log_record(level, message)
        # Adiciona o contexto como string (JSON ou str) ao campo 'context'
        if context:
            import json
            try:
                ctx['context'] = json.dumps(context, ensure_ascii=False)
            except Exception:
                ctx['context'] = str(context)
        else:
            ctx['context'] = ""
        formatted_message = self.log_format.format(**ctx)
        log_method = getattr(self._logger, level.lower(), None)
        if log_method:
            log_method(formatted_message)

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log at INFO level."""
        self._log("INFO", message, context)

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log at DEBUG level."""
        self._log("DEBUG", message, context)

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log at WARNING level."""
        self._log("WARNING", message, context)

    def error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Log at ERROR level with optional exception/context support."""
        self._log("ERROR", str(error), context)

    def critical(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log at CRITICAL level."""
        self._log("CRITICAL", message, context)
