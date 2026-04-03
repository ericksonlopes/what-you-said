# Pytest fixture to provide an in-memory SQLite DB for SQL repository tests
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.infrastructure.repositories.sql.connector as connector
from main import app
from src.presentation.api.dependencies import get_current_user
from src.domain.entities.user import User


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app.state has necessary attributes for tests."""
    if not hasattr(app.state, "model_loader"):
        app.state.model_loader = MagicMock()
    if not hasattr(app.state, "rerank_service"):
        app.state.rerank_service = MagicMock()
    yield


@pytest.fixture(autouse=True)
def mock_auth():
    """Global mock for current user to avoid 401 Unauthorized in API tests."""
    mock_user = User(id="admin", email="admin@whatyousaid.local", full_name="Admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def sqlite_memory():
    """Yield a fresh in-memory SQLite database and session for the duration of the test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    # Rebind connector's engine and Session factory for tests
    connector.engine = engine
    connector.Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Create all tables declared on Base
    connector.Base.metadata.create_all(bind=engine)
    db = connector.Session()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables to cleanup
        connector.Base.metadata.drop_all(bind=engine)
