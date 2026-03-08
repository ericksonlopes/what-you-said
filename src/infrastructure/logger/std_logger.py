import logging
import sys
from typing import Optional, Dict

from src.config.settings import settings
from src.infrastructure.logger.util import get_log_record

from src.domain.infraestructure.logger.logger import ILogger


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

    def info(self, message: str, context: Optional[Dict] = None) -> None:
        """Log at INFO level."""
        if self._is_allowed('INFO'):
            msg = message
            if context:
                msg += f" | context={context}"
            ctx = get_log_record('INFO', msg)
            formatted_message = self.log_format.format(**ctx)
            self._logger.info(formatted_message)

    def debug(self, message: str, context: Optional[Dict] = None) -> None:
        """Log at DEBUG level."""
        if self._is_allowed('DEBUG'):
            msg = message
            if context:
                msg += f" | context={context}"
            ctx = get_log_record('DEBUG', msg)
            formatted_message = self.log_format.format(**ctx)
            self._logger.debug(formatted_message)

    def warning(self, message: str, context: Optional[Dict] = None) -> None:
        """Log at WARNING level."""
        if self._is_allowed('WARNING'):
            msg = message
            if context:
                msg += f" | context={context}"
            ctx = get_log_record('WARNING', msg)
            formatted_message = self.log_format.format(**ctx)
            self._logger.warning(formatted_message)

    def error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """Log at ERROR level with optional exception/context support."""
        if self._is_allowed('ERROR'):
            msg = f"{error}"
            if context:
                msg += f" | context={context}"

            ctx = get_log_record('ERROR', msg)
            formatted_message = self.log_format.format(**ctx)
            self._logger.error(formatted_message)

    # Additional methods for compatibility with other implementations
    def critical(self, message: str, context: Optional[Dict] = None) -> None:
        """Log at CRITICAL level."""
        if self._is_allowed('CRITICAL'):
            msg = message
            if context:
                msg += f" | context={context}"
            ctx = get_log_record('CRITICAL', msg)
            formatted_message = self.log_format.format(**ctx)
            self._logger.critical(formatted_message)
