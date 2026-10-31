from alembic import context
from app.core.config import get_settings
from app.db.session import build_engine
from app.graphs.checkpoints import ensure_checkpoint_tables
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
    ensure_checkpoint_tables(settings)


run_migrations_online()
