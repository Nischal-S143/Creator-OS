import re
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings

_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_engine(settings: Settings, url: str | None = None) -> Engine:
    engine = create_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout},
    )
    schema = settings.db_schema
    if schema:
        if not _SCHEMA_RE.match(schema):
            raise ValueError(f"invalid DB_SCHEMA: {schema!r}")

        @event.listens_for(engine, "connect")
        def _set_search_path(dbapi_conn, _record):
            with dbapi_conn.cursor() as cur:
                cur.execute(f'SET search_path TO "{schema}"')
            dbapi_conn.commit()

    return engine


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings())


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request; callers commit explicitly."""
    session = get_sessionmaker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
