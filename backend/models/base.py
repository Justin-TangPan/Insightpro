"""Shared declarative base for all ORM models."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata root — all models inherit from this."""
    pass
