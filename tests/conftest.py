# Pytest fixture to provide an in-memory SQLite DB for SQL repository tests
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.infrastructure.repositories.sql.connector as connector
from main import app


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app.state has necessary attributes for tests."""
    if not hasattr(app.state, "model_loader"):
        app.state.model_loader = MagicMock()
    yield


@pytest.fixture()
def sqlite_memory():
    """Yield a fresh in-memory SQLite database and session for the duration of the test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    # Rebind connector's engine and Session factory for tests
    connector.engine = engine
    connector.Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Create all tables declared on Base
    connector.Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        # Drop all tables to cleanup
        connector.Base.metadata.drop_all(bind=engine)
