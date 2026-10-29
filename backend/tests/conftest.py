"""Shared pytest fixtures.

Tests run against a real Postgres database (your database name + "_test"), which is
created and migrated automatically. Each test runs inside a transaction that is rolled
back at the end, so tests never see each other's data and the database stays empty.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import CrewMember, CrewRole

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    url = make_url(settings.database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _create_database_if_missing(url: str) -> None:
    db_name = make_url(url).database
    admin = create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Create the test database and build the schema by running the real migrations."""
    url = _test_database_url()
    _create_database_if_missing(url)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    # Down then up: starts from a clean schema and checks both directions of every migration.
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose changes are all rolled back after the test.

    "create_savepoint" means code under test can call commit() freely: each commit only
    closes a savepoint inside our outer transaction, which we roll back at the end.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """An API client whose requests use the test session instead of the real database."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def crew_member(db: Session) -> CrewMember:
    member = CrewMember(name="Maya Torres", role=CrewRole.CAMERA)
    db.add(member)
    db.flush()
    return member
