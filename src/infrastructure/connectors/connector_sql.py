from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import settings

connect_args = {}
if settings.sql.url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.sql.url, connect_args=connect_args)

Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


class Connector:
    def __init__(self):
        self.session = Session()

    def __enter__(self):
        return self.session

    def __exit__(self, *args, **kwargs):
        self.session.close()
