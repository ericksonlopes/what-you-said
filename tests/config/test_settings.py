import logging
import os
import sys
from unittest.mock import MagicMock

import pytest

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


def test_sql_url_mariadb():
    cfg = SQLConfig(
        type="mariadb", user="u", password="p", host="h", port="3306", database="db"
    )
    assert cfg.url == "mariadb+pymysql://u:p@h:3306/db"


def test_sql_url_mssql():
    cfg = SQLConfig(
        type="mssql", user="u", password="p", host="h", port="1433", database="db"
    )
    assert cfg.url == "mssql+pytds://u:p@h:1433/db"


def test_sql_url_default():
    cfg = SQLConfig(type=None)
    assert "sqlite" in cfg.url
    cfg_unknown = SQLConfig(type="unknown")
    assert "sqlite" in cfg_unknown.url


def test_sql_url_override():
    cfg = SQLConfig(url="custom://conn")
    assert cfg.url == "custom://conn"


def test_app_device_cpu_on_import_error(monkeypatch):
    import sys

    # Mock torch import failure
    monkeypatch.setitem(sys.modules, "torch", None)
    app = App()
    assert app.device == "cpu"


def test_app_device_cuda_logic(monkeypatch):
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    monkeypatch.setitem(sys.modules, "torch", mock_torch)
    app = App()
    assert app.device == "cuda"

    mock_torch.cuda.is_available.return_value = False
    assert app.device == "cpu"


def test_app_parse_list_log_levels_already_list():
    # Trigger line 101: if isinstance(v, str) -> else return v
    app = App(list_log_levels=["INFO"])
    assert app.list_log_levels == ["INFO"]
