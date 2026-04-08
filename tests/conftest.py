import os
from unittest.mock import MagicMock, patch

# Suppress NNPACK warnings (Unsupported hardware)
os.environ["NNPACK_CPU_FAST_8x8_CONV"] = "0"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.infrastructure.connectors.connector_sql as connector
import src.infrastructure.repositories.sql.models  # noqa: F401


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app.state has necessary attributes for tests."""
    from main import app

    if not hasattr(app.state, "model_loader"):
        app.state.model_loader = MagicMock()
    if not hasattr(app.state, "rerank_service"):
        app.state.rerank_service = MagicMock()
    if not hasattr(app.state, "task_queue"):
        app.state.task_queue = MagicMock()
    if not hasattr(app.state, "event_bus"):
        app.state.event_bus = MagicMock()
    yield


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """Mock heavy infrastructure components globally."""
    with (
        patch("src.infrastructure.repositories.storage.storage.StorageService"),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_auth():
    """Global mock for current user to avoid 401 Unauthorized in API tests."""
    from main import app
    from src.domain.entities.user import User
    from src.presentation.api.dependencies import get_current_user

    mock_user = User(id="admin", email="admin@whatyousaid.local", full_name="Admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def sqlite_memory():
    """Yield a fresh in-memory SQLite database and session for the duration of the test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    connector.engine = engine
    connector.Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    connector.Base.metadata.create_all(bind=engine)
    db = connector.Session()
    try:
        yield db
    finally:
        db.close()
        connector.Base.metadata.drop_all(bind=engine)
