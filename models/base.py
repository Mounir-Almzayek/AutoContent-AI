"""
SQLAlchemy declarative base. All DB models inherit from this.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for all ORM models."""

    pass
