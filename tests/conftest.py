# Pytest fixture to provide an in-memory SQLite DB for SQL repository tests
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.infrastructure.repositories.sql.connector as connector


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
