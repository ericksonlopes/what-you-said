import inspect
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Optional, Any, Dict

from src.config.settings import settings
from src.domain.interfaces.logger.logger import ILogger


# Global context for logging via contextvars
_global_log_context: ContextVar[Dict[str, Any]] = ContextVar(
    "global_log_context", default={}
)


def set_global_context(context: Dict[str, Any]) -> None:
    """Set global context for all subsequent logs in the current execution context."""
    current = _global_log_context.get()
    _global_log_context.set({**current, **context})


def clear_global_context() -> None:
    """Clear all global context."""
    _global_log_context.set({})


# ANSI color codes
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",
}


class StdLogger(ILogger):
    """
    Standard loggers that uses Python's built-in logging instead of loguru.
    Keeps compatibility with the ILogger interface.
    """

    def __init__(
        self,
        log_format: str,
        name: Optional[str] = None,
        logger_id: Optional[str] = None,
    ) -> None:
        self.log_format = log_format
        self.service_name = name or "std-loggers"

        logger_name = f"std_logger_{self.service_name}"
        if logger_id is not None:
            logger_name = f"{logger_name}_{logger_id}"
        else:
            logger_name = f"{logger_name}_{id(self)}"
        self._logger = logging.getLogger(logger_name)

        # Remove any existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Set the loggers to accept all levels (NOTSET)
        # This prevents it from inheriting the root loggers level
        self._logger.setLevel(logging.NOTSET)
        self._logger.propagate = False

        # Configure handler to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        # Also set the handler to accept all levels
        console_handler.setLevel(logging.NOTSET)

        # Simple formatter that just prints the formatted message
        formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # Force loggers to not inherit from parent (bypass root loggers's level)
        self._logger.parent = None

        self.allowed_levels = settings.app.allowed_log_levels
        # Check if we should use colors (default to True if terminal)
        self.use_colors = sys.stdout.isatty()

    @staticmethod
    def get_logger_module_files(base_dir=None):
        """
        Returns a set with normalized (absolute) paths of ALL .py files
        inside src/infrastructure/loggers, including subdirectories.
        This list adapts dynamically to all files present in the loggers infra.
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        logger_files = set()
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".py"):
                    logger_files.add(os.path.abspath(os.path.join(root, file)))
        return logger_files

    @staticmethod
    def get_log_record(level: str, message: str):
        """
        Extracts detailed context from the frame where the log was originally called.
        Returns a dict with all fields for the standard log template.
        This context excludes any frame from infrastructure python files found in the loggers directory.
        """
        logger_files = StdLogger.get_logger_module_files()
        stack = inspect.stack()
        cls_name = ""
        frame_best = stack[1]
        for frame_info in stack:
            filename_abs = os.path.abspath(frame_info.filename)
            if filename_abs not in logger_files:
                self_obj = frame_info.frame.f_locals.get("self", None)
                if self_obj:
                    cls_name = type(self_obj).__name__
                frame_best = frame_info
                break

        asctime = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        filename = os.path.basename(frame_best.filename)
        # Caminho relativo ao diretório do projeto
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../..")
        )
        filepath_abs = os.path.abspath(frame_best.filename)
        filepath_rel = os.path.relpath(filepath_abs, project_root).replace("\\", "/")
        lineno = frame_best.lineno
        func_name = frame_best.function

        return {
            "asctime": asctime,
            "levelname": level.upper(),
            "filename": filename,
            "filepath": filepath_rel,
            "lineno": lineno,
            "class": cls_name,
            "funcName": func_name,
            "message": message,
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

    def _log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | Optional[Any] = None,
        *args,
        **kwargs,
    ) -> None:
        if not self._is_allowed(level):
            return

        # Handle standard logging message interpolation if args are provided
        if args:
            try:
                message = message % args
            except Exception:
                pass

        ctx = StdLogger.get_log_record(level, message)

        # Apply colors if enabled
        if self.use_colors:
            color = COLORS.get(ctx["levelname"], "")
            reset = COLORS["RESET"]
            ctx["levelname"] = f"{color}{ctx['levelname']:<8}{reset}"
        else:
            ctx["levelname"] = f"{ctx['levelname']:<8}"

        # Merge local context with global context from contextvars
        global_ctx = _global_log_context.get()

        # Ensure context is a mapping if it's not None
        safe_context: dict[str, Any] = {}
        if context:
            if isinstance(context, dict):
                safe_context = context
            else:
                # If it's not a dict, we put it into a default key to avoid crash
                safe_context = {"extra": context}

        # Handle extra from kwargs (standard logging)
        if "extra" in kwargs and isinstance(kwargs["extra"], dict):
            safe_context.update(kwargs["extra"])

        full_context = {**global_ctx, **safe_context}

        # Adiciona o contexto como string (JSON ou str) ao campo 'context'
        if full_context:
            import json

            try:
                # One-liner for standard view, but could be indented if preferred
                ctx["context"] = (
                    f"| \033[2m{json.dumps(full_context, ensure_ascii=False)}\033[0m"
                    if self.use_colors
                    else f"| {json.dumps(full_context, ensure_ascii=False)}"
                )
            except (TypeError, OverflowError):
                ctx["context"] = f"| {str(full_context)}"
        else:
            ctx["context"] = ""

        # Adjust format slightly if context exists to avoid trailing pipe
        current_format = self.log_format.replace(" | {context}", "{context}")
        formatted_message = current_format.format(**ctx)

        log_method = getattr(self._logger, level.lower(), None)
        if log_method:
            log_method(formatted_message)

    def info(
        self, message: str, context: dict[str, Any] | None = None, *args, **kwargs
    ) -> None:
        """Log at INFO level."""
        self._log("INFO", message, context, *args, **kwargs)

    def debug(
        self, message: str, context: dict[str, Any] | None = None, *args, **kwargs
    ) -> None:
        """Log at DEBUG level."""
        self._log("DEBUG", message, context, *args, **kwargs)

    def warning(
        self, message: str, context: dict[str, Any] | None = None, *args, **kwargs
    ) -> None:
        """Log at WARNING level."""
        self._log("WARNING", message, context, *args, **kwargs)

    def error(
        self, error: Any, context: dict[str, Any] | None = None, *args, **kwargs
    ) -> None:
        """Log at ERROR level with optional exception/context support."""
        self._log("ERROR", str(error), context, *args, **kwargs)

    def critical(
        self, message: str, context: dict[str, Any] | None = None, *args, **kwargs
    ) -> None:
        """Log at CRITICAL level."""
        self._log("CRITICAL", message, context, *args, **kwargs)


class InterceptHandler(logging.Handler):
    """
    Standard logging handler that intercepts logs and redirects them to our custom Logger.
    """

    def __init__(self, custom_logger):
        super().__init__()
        self.custom_logger = custom_logger

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        level = record.levelname
        message = record.getMessage()

        # Determine which method to call on custom_logger
        if level == "DEBUG":
            self.custom_logger.debug(message)
        elif level == "INFO":
            self.custom_logger.info(message)
        elif level == "WARNING":
            self.custom_logger.warning(message)
        elif level == "ERROR":
            self.custom_logger.error(RuntimeError(message))
        elif level == "CRITICAL":
            self.custom_logger.critical(message)
        else:
            self.custom_logger.info(message)
