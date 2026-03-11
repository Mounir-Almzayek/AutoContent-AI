"""
Database connection, engine, and session factory.
Import all models so that Base.metadata registers every table before create_all().
See docs/07_DATA_MODELS.md.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from models.base import Base

# Import model modules so that tables are registered with Base.metadata
import models.article  # noqa: F401
import models.keyword  # noqa: F401
import models.token_usage  # noqa: F401

_settings = get_settings()

_engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in _settings.database_url else {},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a DB session (for FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call on startup (idempotent for existing tables)."""
    Base.metadata.create_all(bind=_engine)


def get_engine():
    """Return the global engine (e.g. for migrations or tests)."""
    return _engine
