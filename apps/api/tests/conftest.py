"""Integration tests run against the real YugabyteDB cluster in DATABASE_URL.

Each session migrates a throwaway schema and drops it afterwards, so existing
data (public schema) is never touched.
"""

import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session

from alembic import command
from app.config import get_settings
from app.db import get_engine, get_sessionmaker

ENV = Path(__file__).resolve().parents[3] / ".env"


def _reset_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def migrated():
    schema = f"creatoros_test_{uuid.uuid4().hex[:8]}"
    _reset_caches()
    settings = get_settings()
    app_role = make_url(settings.database_url).username
    migrator = make_url(settings.migration_database_url).username
    admin = create_engine(
        os.environ.get("ADMIN_DATABASE_URL") or dotenv_values(ENV)["ADMIN_DATABASE_URL"],
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}" AUTHORIZATION "{migrator}"'))
        c.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{app_role}"'))
        c.execute(
            text(
                f'ALTER DEFAULT PRIVILEGES FOR ROLE "{migrator}" IN SCHEMA "{schema}" '
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{app_role}"'
            )
        )
    mp = pytest.MonkeyPatch()
    mp.setenv("DB_SCHEMA", schema)
    _reset_caches()
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
        yield cfg
    finally:
        get_engine().dispose()
        mp.undo()
        _reset_caches()
        with admin.connect() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def db(migrated) -> Session:
    session = get_sessionmaker()()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(migrated):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
