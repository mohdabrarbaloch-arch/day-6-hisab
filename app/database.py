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


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
