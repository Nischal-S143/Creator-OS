from alembic import context
from app.config import get_settings
from app.db import build_engine
from app.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    settings = get_settings()
    engine = build_engine(settings, settings.migration_database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
