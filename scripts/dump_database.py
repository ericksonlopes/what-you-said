import json
import logging
import os

# Adjust the path so we can import from src
import sys
from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import Session

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from infrastructure.connectors.connector_sql import engine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def dump_database():
    """
    Dumps all tables from the currently configured database into JSON files.
    This works independently of the database type (SQLite, Postgres, MySQL, etc.)
    because it relies solely on SQLAlchemy's reflection.
    """
    # Create the dump directory
    dump_dir = os.path.join(os.path.dirname(__file__), "..", "data", "dump")
    os.makedirs(dump_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_dump_dir = os.path.join(dump_dir, f"dump_{timestamp}")
    os.makedirs(current_dump_dir, exist_ok=True)

    logger.info(f"Connecting to database using engine: {engine.url}")

    # Reflect the database schema to get all tables
    metadata = MetaData()
    metadata.reflect(bind=engine)

    tables = metadata.sorted_tables
    if not tables:
        logger.warning("No tables found in the database. Are the migrations applied?")
        return

    logger.info(f"Found {len(tables)} tables to dump.")

    with Session(engine) as session:
        for table in tables:
            rows = session.execute(table.select()).fetchall()

            # Convert rows to a list of dicts
            data = []
            for row in rows:
                row_dict = dict(row._mapping)

                # Convert non-serializable objects like datetimes or UUIDs
                for key, value in row_dict.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.isoformat()
                    else:
                        row_dict[key] = str(value) if value is not None else None

                data.append(row_dict)

            # Save to JSON
            file_path = os.path.join(current_dump_dir, f"{table.name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            logger.info(
                f"Dumped table '{table.name}' ({len(data)} rows) -> {file_path}"
            )

    logger.info(f"Database dump completed successfully in '{current_dump_dir}'.")


if __name__ == "__main__":
    dump_database()
