"""Points every test at a dedicated test database, not the dev/prod one -
set before any `app.*` module is imported, since app.database creates its
engine at import time from whatever DATABASE_URL it sees first.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://abhinavsingh@localhost:5432/tavora_test"
)

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts from a completely empty schema - no test depends on
    another's leftover rows, and no test can accidentally pass because an
    earlier test happened to set something up first.

    Deliberately still `create_all`, not `alembic upgrade head` (V7 adds
    real migrations for dev/prod - see backend/alembic/): this runs once per
    test, and running every migration from scratch that many times would
    make the suite meaningfully slower for no correctness benefit - the
    model definitions and the migrations describe the same schema either
    way, and CI additionally runs `alembic upgrade head` against a fresh
    database once (see .github/workflows/ci.yml) to catch the two drifting
    apart."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def _get_db_override():
        yield db

    # Deliberately NOT using `with TestClient(app) as ...` - that triggers
    # main.py's lifespan, which starts the real APScheduler. These are
    # endpoint tests, not scheduler tests; no need for a background job
    # ticking during a test run.
    app.dependency_overrides[get_db] = _get_db_override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def two_users(db):
    user_a = User(name="Test User A")
    user_b = User(name="Test User B")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    return user_a, user_b
