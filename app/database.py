"""
Database engine and session management.

Provides:
    engine          — SQLAlchemy Engine (sync)
    SessionLocal    — session factory for dependency injection
    get_db()        — FastAPI dependency that yields a scoped session
    Base            — declarative base for all ORM models
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Shared declarative base.  All ORM models inherit from this."""


engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,     # detect stale connections
    pool_recycle=3600,      # recycle connections after 1 h
    echo=settings.debug,    # log SQL in development; silent in production
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency.  Yields a database session and ensures cleanup.

    Usage in a router:
        @router.get("/vehicles")
        def list_vehicles(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
