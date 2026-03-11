import logging

import pytest

from src.config.settings import Settings, App


def test_allowed_log_levels_default():
    s = Settings(app=App(list_log_levels=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]))
    expected = {logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL}
    assert s.app.allowed_log_levels == expected


@pytest.mark.parametrize("levels,expected", [
    ("DEBUG,INFO", {logging.DEBUG, logging.INFO}),
    (["ERROR", "CRITICAL"], {logging.ERROR, logging.CRITICAL}),
    ("", set()),
    (["NOT_A_LEVEL"], set()),
])
def test_allowed_log_levels_various(levels, expected):
    s = Settings(app=App(list_log_levels=levels))
    assert s.app.allowed_log_levels == expected


# Edge case: LIST_LOG_LEVELS with whitespace and invalid values

def test_allowed_log_levels_whitespace_and_invalid():
    s = Settings(app=App(list_log_levels=" DEBUG , INVALID , INFO "))
    assert s.app.allowed_log_levels == {logging.DEBUG, logging.INFO}
