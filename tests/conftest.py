"""Shared pytest fixtures: fresh DB per test, TestClient."""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import limiter
from app.main import app


@pytest.fixture(autouse=True)
def reset_limiter():
    """Clear slowapi rate-limit state between tests (same process, same IP)."""
    yield
    try:
        limiter.reset()
    except Exception:
        pass


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    yield SessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
