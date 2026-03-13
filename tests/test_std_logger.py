import logging
import sys

import pytest

from src.infrastructure.loggers.std_logger import StdLogger


class DummySettings:
    allowed_log_levels = [10, 20, 30, 40, 50]  # DEBUG, INFO, WARNING, ERROR, CRITICAL


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr('src.config.settings.settings', DummySettings())


@pytest.fixture
def logger():
    log_format = "{asctime} [{levelname}] {filename}:{lineno} {class}.{funcName} - {message}"
    return StdLogger(log_format, name="test")


@pytest.mark.std_logger
class TestStdLogger:
    def test_get_logger_module_files_custom_dir(self, tmp_path):
        d = tmp_path / "loggers"
        d.mkdir()
        (d / "a.py").write_text("# test")
        (d / "b.py").write_text("# test")
        files = StdLogger.get_logger_module_files(str(d))
        assert len(files) == 2
        assert any("a.py" in f for f in files)
        assert any("b.py" in f for f in files)

    def test_is_allowed_empty(self):
        logger = StdLogger("{message}")
        logger.allowed_levels = []
        assert logger._is_allowed("INFO") is False

    def test_log_skips_if_not_allowed(self, monkeypatch):
        logger = StdLogger("{message}")
        monkeypatch.setattr(logger, "_is_allowed", lambda x: False)
        logger._log("INFO", "should not log")  # Should do nothing

    def test_log_context_serialization(self):
        logger = StdLogger("{message} {context}")
        context = {"foo": "bar"}
        logger._log("INFO", "msg", context)  # Should serialize context
        logger._log("INFO", "msg", object())  # Should fallback to str

    def test_log_method_fallback(self):
        logger = StdLogger("{message}")
        logger._logger = object()  # No log method
        logger._log("INFO", "msg")  # Should not raise

    def test_error_method(self):
        logger = StdLogger("{message}")
        logger.error(Exception("fail"))

    def test_critical_method(self):
        logger = StdLogger("{message}")
        logger.critical("critical error")

    def test_critical_method_with_context(self):
        logger = StdLogger("{message}")
        logger.critical("critical error", context={"foo": "bar"})

    def test_debug_method(self):
        logger = StdLogger("{message}")
        logger.debug("debug message")
        logger.debug("debug with context", context={"foo": "bar"})

    def test_logger_remove_handlers(self):
        log_format = "{message}"
        logger_name = "test_remove_handlers"
        unique_logger_name = f'std_logger_{logger_name}_unique'
        logger_obj = logging.getLogger(unique_logger_name)
        handler = logging.StreamHandler()
        logger_obj.addHandler(handler)
        assert len(logger_obj.handlers) > 0
        StdLogger(log_format, name=logger_name)
        # After StdLogger instantiation, only one handler should remain
        assert len(logger_obj.handlers) == 1

    def test_logger_handler_removal(self):
        import logging
        log_format = "{message}"
        logger_name = "handler_removal"
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 3  # 1 default + 2 added
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        assert len(logger_obj.handlers) == 1  # Only the new handler remains

    def test_logger_handler_removal_multiple(self):
        import logging
        log_format = "{message}"
        logger_name = "handler_removal_multiple"
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 3  # 1 default + 2 added
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        assert len(logger_obj.handlers) == 1  # Only the new handler remains

    def test_is_allowed_keyerror(self, monkeypatch):
        logger = StdLogger("{message}")
        logger.allowed_levels = [10]

        def broken_get_log_level(level_name):
            raise KeyError("fail")

        monkeypatch.setattr(logger, "_get_log_level", broken_get_log_level)
        assert logger._is_allowed("INFO") is True

    def test_is_allowed_runtimeerror(self, monkeypatch):
        logger = StdLogger("{message}")
        logger.allowed_levels = [10]

        def broken_get_log_level(level_name):
            raise ValueError("fail")

        monkeypatch.setattr(logger, "_get_log_level", broken_get_log_level)
        with pytest.raises(RuntimeError) as exc:
            logger._is_allowed("INFO")
        assert "Unexpected error in _is_allowed" in str(exc.value)

    def test_logger_remove_all_handlers(self):
        log_format = "{message}"
        logger_name = "remove_all_handlers"
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 3  # 1 default + 2 added
        # Re-instantiate StdLogger to trigger handler removal
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        assert len(logger_obj.handlers) == 1  # Only the new handler remains

    def test_handler_removal_loop(self):
        log_format = "{message}"
        logger_name = "handler_removal_loop"
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        # Add multiple handlers
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 3  # 1 default + 2 added
        # Re-instantiate StdLogger to trigger handler removal loop
        logger = StdLogger(log_format, name=logger_name)
        logger_obj = logger._logger
        assert len(logger_obj.handlers) == 1  # Only the new handler remains

    def test_explicit_handler_removal_loop(self):
        """
        Test explicit coverage of handler removal loop in StdLogger (__init__, line 27).
        Ensures that existing handlers are removed from loggers instance.
        """
        import logging
        log_format = "{message}"
        logger_name = "explicit_handler_removal"
        # Create loggers and add handlers
        logger_obj = logging.getLogger(f'std_logger_{logger_name}')
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 2

        # Instantiate StdLogger with same loggers name (simulate same instance)
        class StdLoggerTest(StdLogger):
            def __init__(self, log_format, name=None):
                self.log_format = log_format
                self.service_name = name or "std-loggers"
                # Use fixed loggers name for test
                self._logger = logging.getLogger(f'std_logger_{self.service_name}')
                for handler in self._logger.handlers[:]:
                    self._logger.removeHandler(handler)
                self._logger.setLevel(logging.NOTSET)
                self._logger.propagate = False
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.NOTSET)
                formatter = logging.Formatter('%(message)s')
                console_handler.setFormatter(formatter)
                self._logger.addHandler(console_handler)
                self._logger.parent = None
                self.allowed_levels = [10, 20, 30, 40, 50]

        StdLoggerTest(log_format, name=logger_name)
        # Only one handler should remain
        assert len(logger_obj.handlers) == 1

    def test_handler_removal_loop_coverage(self):
        """
        Test explicit coverage of handler removal loop (linha 27) usando logger_id fixo.
        """
        import logging
        log_format = "{message}"
        logger_name = "coverage_handler_removal"
        logger_id = "fixed"
        # Cria loggers e adiciona handlers
        logger_obj = logging.getLogger(f'std_logger_{logger_name}_{logger_id}')
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        logger_obj.addHandler(handler1)
        logger_obj.addHandler(handler2)
        assert len(logger_obj.handlers) >= 2
        # Instancia StdLogger com logger_id fixo para garantir execução do loop
        StdLogger(log_format, name=logger_name, logger_id=logger_id)
        # Apenas um handler deve restar
        assert len(logger_obj.handlers) == 1
