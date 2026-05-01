"""
Shared model utilities.

TimestampMixin
--------------
Adds created_at and updated_at to any model that inherits it.
Both columns are managed by the database engine, not by the application,
so they are always accurate even for bulk inserts or direct SQL edits.

Usage:
    class MyModel(TimestampMixin, Base):
        __tablename__ = "my_table"
        ...
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import MappedColumn, mapped_column


class TimestampMixin:
    """Mixin that adds created_at and updated_at to a model."""

    created_at: MappedColumn[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: MappedColumn[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
