from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for our future database models."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()

    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=10,
        connect_args={
            "sslmode": settings.db_sslmode,
            "connect_timeout": 10,
            "options": "-c statement_timeout=10000",
        },
        echo=False,
        hide_parameters=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()

    with session_factory() as session:
        yield session