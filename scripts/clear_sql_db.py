import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.repositories.sql.connector import engine, Base
from src.infrastructure.repositories.sql import models  # noqa: F401
from src.config.logger import Logger

logger = Logger()


def clear_sql_db():
    """Drops and recreates all tables defined in the SQLAlchemy metadata."""
    logger.info("Starting SQL database cleanup...")
    try:
        # Import all models to ensure they are registered with Base.metadata

        logger.debug("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

        logger.debug("Recreating all tables...")
        Base.metadata.create_all(bind=engine)

        logger.info("SQL database cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during SQL database cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clear_sql_db()
