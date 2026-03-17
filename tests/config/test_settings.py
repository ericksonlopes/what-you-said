import logging
import os

import pytest
from pydantic import ValidationError

from src.config.settings import Settings, App, SQLConfig, VectorConfig


def test_allowed_log_levels_default():
    s = Settings(
        app=App(list_log_levels=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    )
    expected = {
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    }
    assert s.app.allowed_log_levels == expected


@pytest.mark.parametrize(
    "levels,expected",
    [
        ("DEBUG,INFO", {logging.DEBUG, logging.INFO}),
        (["ERROR", "CRITICAL"], {logging.ERROR, logging.CRITICAL}),
        ("", set()),
        (["NOT_A_LEVEL"], set()),
    ],
)
def test_allowed_log_levels_various(levels, expected):
    s = Settings(app=App(list_log_levels=levels))
    assert s.app.allowed_log_levels == expected


# Edge case: LIST_LOG_LEVELS with whitespace and invalid values


def test_allowed_log_levels_whitespace_and_invalid():
    s = Settings(app=App(list_log_levels=" DEBUG , INVALID , INFO "))
    assert s.app.allowed_log_levels == {logging.DEBUG, logging.INFO}


def test_sql_url_postgres():
    test_pw = os.environ.get("TEST_SQL_PASSWORD", "p")
    cfg = SQLConfig(
        type="postgres",
        user="u",
        password=test_pw,
        host="h",
        port="5432",
        database="db",
    )
    assert cfg.url == f"postgresql://u:{test_pw}@h:5432/db"


def test_sql_url_mysql():
    test_pw = os.environ.get("TEST_SQL_PASSWORD", "p")
    cfg = SQLConfig(
        type="mysql", user="u", password=test_pw, host="h", port="3306", database="db"
    )
    assert cfg.url == f"mysql+pymysql://u:{test_pw}@h:3306/db"


def test_weaviate_url_custom():
    vcfg = VectorConfig(weaviate_host="example.com", weaviate_port=9999)
    assert vcfg.weaviate_url == "http://example.com:9999"


def test_app_invalid_env_raises():
    with pytest.raises(ValidationError):
        App(env="invalid")
