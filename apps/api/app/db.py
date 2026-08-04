from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


def session_factory(settings: Settings):
    engine = create_engine(settings.database_url)
    return sessionmaker(engine)

