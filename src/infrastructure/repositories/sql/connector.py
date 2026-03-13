from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config.settings import settings

engine = create_engine(settings.sql.url)

Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


class Connector:
    def __init__(self):
        self.session = Session()

    def __enter__(self):
        return self.session

    def __exit__(self, *args, **kwargs):
        self.session.close()
