"""Database engine + session management.

SQLite (WAL) for zero-setup dev, PostgreSQL via DATABASE_URL for production.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_database_url = settings.database_url

# Vercel's serverless filesystem is read-only outside /tmp. If we're running
# on Vercel and still pointing at the dev SQLite default, redirect it to a
# writable path so the startup ``create_all`` can create the tables.
if _database_url.startswith("sqlite") and os.environ.get("VERCEL"):
    _database_url = "sqlite:////tmp/hisab.db"

connect_args = {"check_same_thread": False} if _database_url.startswith("sqlite") else {}

engine = create_engine(_database_url, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create any missing tables.

    Idempotent by design (``create_all`` skips tables that already exist), so
    it is safe to call from both module-import time and the lifespan handler.
    This matters on Vercel: the serverless Python runtime imports the module and
    serves the request directly, and does NOT reliably run FastAPI's lifespan
    startup -- so if we only create tables in ``lifespan``, every request on a
    cold start hits ``no such table``. Import-time ``init_db`` closes that gap.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
