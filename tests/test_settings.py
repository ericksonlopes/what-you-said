import pytest
import logging
from src.config.settings import Settings

# Line 24: allowed_log_levels property

def test_allowed_log_levels_default():
    s = Settings(LIST_LOG_LEVELS=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    expected = {logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL}
    assert s.allowed_log_levels == expected

@pytest.mark.parametrize("levels,expected", [
    ("DEBUG,INFO", {logging.DEBUG, logging.INFO}),
    (["ERROR", "CRITICAL"], {logging.ERROR, logging.CRITICAL}),
    ("", set()),
    (["NOT_A_LEVEL"], set()),
])
def test_allowed_log_levels_various(levels, expected):
    s = Settings(LIST_LOG_LEVELS=levels)
    assert s.allowed_log_levels == expected

# Edge case: LIST_LOG_LEVELS with whitespace and invalid values

def test_allowed_log_levels_whitespace_and_invalid():
    s = Settings(LIST_LOG_LEVELS=" DEBUG , INVALID , INFO ")
    assert s.allowed_log_levels == {logging.DEBUG, logging.INFO}
