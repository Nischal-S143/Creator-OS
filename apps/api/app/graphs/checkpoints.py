"""LangGraph checkpoints in YugabyteDB. They hold workflow position; business data stays in its tables."""

import re
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from app.core.config import Settings, get_settings

_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _connect(url: str, settings: Settings) -> psycopg.Connection:
    schema = settings.db_schema
    if schema and not _SCHEMA_RE.match(schema):
        raise ValueError("invalid DB_SCHEMA")
    return psycopg.connect(
        url.replace("postgresql+psycopg://", "postgresql://"),
        autocommit=True,
        row_factory=dict_row,
        prepare_threshold=None,
        options=f"-c search_path={schema}" if schema else None,
    )


def ensure_checkpoint_tables(settings: Settings) -> None:
    """Runs with the migration role, so the runtime role never needs permission to change the schema."""
    with _connect(settings.migration_database_url or settings.database_url, settings) as connection:
        PostgresSaver(connection).setup()


@contextmanager
def checkpointer() -> Iterator[PostgresSaver]:
    settings = get_settings()
    with _connect(settings.database_url, settings) as connection:
        yield PostgresSaver(connection)
