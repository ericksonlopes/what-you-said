from src.config.logger import setup_logging, Logger

def test_setup_logging():
    """Verify setup_logging returns a Logger instance."""
    logger = setup_logging()
    assert isinstance(logger, Logger)
    assert logger._logger is not None
