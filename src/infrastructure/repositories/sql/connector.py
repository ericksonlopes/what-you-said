from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config.settings import settings

engine = create_engine(settings.sql.url)

Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

from src.infrastructure.repositories.sql.models import knowledge_subject, content_source, chunk_index, ingestion_job, query_log  # noqa: F401

class Connector:
    def __init__(self):
        self.session = Session()

    def __enter__(self):
        return self.session

    def __exit__(self, *args, **kwargs):
        self.session.close()
