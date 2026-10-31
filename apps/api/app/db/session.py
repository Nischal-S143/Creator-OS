import re
import uuid
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_engine(settings: Settings, url: str | None = None) -> Engine:
    engine = create_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": settings.db_connect_timeout,
            # The YugabyteDB connection manager can switch backends, which lose prepared statements.
            "prepare_threshold": None,
        },
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


def _apply_rls(connection: Connection, context: dict[str, str]) -> None:
    # One statement: this runs at the start of every transaction, so round trips matter.
    connection.execute(
        text(
            "SELECT set_config('app.tenant_id', :tenant, true), "
            "set_config('app.user_id', :user, true), "
            "set_config('app.auth_subject', :subject, true)"
        ),
        {
            "tenant": context.get("app.tenant_id", ""),
            "user": context.get("app.user_id", ""),
            "subject": context.get("app.auth_subject", ""),
        },
    )


def set_rls(
    session: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    auth_subject: str | None = None,
) -> None:
    """Sets the row-level security context. It replaces any earlier context and applies per transaction."""
    context = {}
    if tenant_id:
        context["app.tenant_id"] = str(tenant_id)
    if user_id:
        context["app.user_id"] = str(user_id)
    if auth_subject:
        context["app.auth_subject"] = auth_subject
    session.info["rls"] = context
    if session.in_transaction():
        _apply_rls(session.connection(), context)


@event.listens_for(Session, "after_begin")
def _apply_rls_on_begin(session: Session, _transaction, connection: Connection) -> None:
    _apply_rls(connection, session.info.get("rls", {}))


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
