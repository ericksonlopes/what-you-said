import inspect
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Any

from src.config.settings import settings
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

    @staticmethod
    def get_logger_module_files(base_dir=None):
        """
        Returns a set with normalized (absolute) paths of ALL .py files
        inside src/infrastructure/logger, including subdirectories.
        This list adapts dynamically to all files present in the logger infra.
        """
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__))
            )
        logger_files = set()
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.py'):
                    logger_files.add(os.path.abspath(os.path.join(root, file)))
        return logger_files

    @staticmethod
    def get_log_record(level: str, message: str):
        """
        Extracts detailed context from the frame where the log was originally called.
        Returns a dict with all fields for the standard log template.
        This context excludes any frame from infrastructure python files found in the logger directory.
        """
        logger_files = StdLogger.get_logger_module_files()
        stack = inspect.stack()
        cls_name = ""
        frame_best = stack[1]
        for frame_info in stack:
            filename_abs = os.path.abspath(frame_info.filename)
            if filename_abs not in logger_files:
                self_obj = frame_info.frame.f_locals.get('self', None)
                if self_obj:
                    cls_name = type(self_obj).__name__
                frame_best = frame_info
                break

        asctime = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        filename = os.path.basename(frame_best.filename)
        # Caminho relativo ao diretório do projeto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        filepath_abs = os.path.abspath(frame_best.filename)
        filepath_rel = os.path.relpath(filepath_abs, project_root).replace('\\', '/')
        lineno = frame_best.lineno
        func_name = frame_best.function

        return {
            'asctime': asctime,
            'levelname': level.upper(),
            'filename': filename,
            'filepath': filepath_rel,
            'lineno': lineno,
            'class': cls_name,
            'funcName': func_name,
            'message': message
        }

    @classmethod
    def _get_log_level(cls, level_name: str):
        return getattr(logging, level_name.upper(), None)

    def _is_allowed(self, level_name: str) -> bool:
        try:
            if not self.allowed_levels:
                return False
            level = self._get_log_level(level_name)
            return level in self.allowed_levels
        except KeyError:
            return True
        except Exception as exc:
            raise RuntimeError(f"Unexpected error in _is_allowed: {exc}") from exc

    def _log(self, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        if not self._is_allowed(level):
            return
        ctx = StdLogger.get_log_record(level, message)
        # Adiciona o contexto como string (JSON ou str) ao campo 'context'
        if context:
            import json
            try:
                ctx['context'] = json.dumps(context, ensure_ascii=False)
            except TypeError:
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
