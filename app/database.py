"""
Database connection, engine, and session factory.
Import all models so that Base.metadata registers every table before create_all().
See docs/data/models.md.
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
import models.schedule_rule  # noqa: F401

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


def _migrate_schedule_rules(db_engine) -> None:
    """Add new columns to schedule_rules if missing (rule_type, niche, trend_*, last_keywords_count)."""
    if "sqlite" not in str(db_engine.url):
        return
    from sqlalchemy import text
    with db_engine.connect() as conn:
        info = conn.execute(text("SELECT name FROM pragma_table_info('schedule_rules')")).fetchall()
        existing = {row[0] for row in info} if info else set()
        for col, sql in [
            ("rule_type", "ALTER TABLE schedule_rules ADD COLUMN rule_type VARCHAR(32) DEFAULT 'articles'"),
            ("niche", "ALTER TABLE schedule_rules ADD COLUMN niche VARCHAR(256)"),
            ("trend_keywords_count", "ALTER TABLE schedule_rules ADD COLUMN trend_keywords_count INTEGER"),
            ("trend_time_window", "ALTER TABLE schedule_rules ADD COLUMN trend_time_window VARCHAR(64)"),
            ("last_keywords_count", "ALTER TABLE schedule_rules ADD COLUMN last_keywords_count INTEGER"),
        ]:
            if col not in existing:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception:
                    conn.rollback()


def init_db() -> None:
    """Create all tables. Safe to call on startup (idempotent for existing tables)."""
    Base.metadata.create_all(bind=_engine)
    _migrate_schedule_rules(_engine)


def get_engine():
    """Return the global engine (e.g. for migrations or tests)."""
    return _engine
