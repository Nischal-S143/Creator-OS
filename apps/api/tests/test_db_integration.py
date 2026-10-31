from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.db.session import get_db, get_engine

TABLES = {"users", "organizations", "memberships", "brands"}


def test_tables_and_tenant_columns_exist(migrated):
    insp = inspect(get_engine())
    assert TABLES <= set(insp.get_table_names())
    brand_cols = {c["name"] for c in insp.get_columns("brands")}
    assert {"organization_id", "owner_id", "created_by", "meko_datapack_id"} <= brand_cols
    assert {"plan", "status", "owner_id"} <= {c["name"] for c in insp.get_columns("organizations")}


def test_get_db_dependency_yields_working_session(migrated):
    gen = get_db()
    session = next(gen)
    assert session.execute(select(1)).scalar_one() == 1
    gen.close()


def test_health_db_ok(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_db_503_when_database_unreachable(client):
    from app.main import app

    bad = create_engine("postgresql+psycopg://u:p@127.0.0.1:1/x", connect_args={"connect_timeout": 2})

    def broken():
        with Session(bad) as s:
            yield s

    app.dependency_overrides[get_db] = broken
    assert client.get("/health/db").status_code == 503


def test_migration_downgrade_and_reupgrade(migrated):
    command.downgrade(migrated, "base")
    assert "brands" not in inspect(get_engine()).get_table_names()
    command.upgrade(migrated, "head")
    assert TABLES <= set(inspect(get_engine()).get_table_names())
