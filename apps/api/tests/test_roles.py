"""The runtime role must be able to use data and nothing else."""

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.db.session import get_engine, set_rls
from app.models import Brand
from tests.helpers import seed_tenant


def _refused(sql: str) -> None:
    with get_engine().connect() as c:
        with pytest.raises(DBAPIError) as exc:
            c.execute(text(sql))
        assert "permission denied" in str(exc.value.orig).lower()
        c.rollback()


def test_app_runs_as_restricted_role(migrated):
    with get_engine().connect() as c:
        row = c.execute(
            text(
                "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls FROM pg_roles "
                "WHERE rolname = current_user"
            )
        ).one()
    assert row.rolname == "creatoros_app"
    assert not (row.rolsuper or row.rolcreaterole or row.rolcreatedb or row.rolbypassrls)


def test_app_role_owns_no_application_tables(migrated):
    with get_engine().connect() as c:
        owners = c.execute(
            text(
                "SELECT tablename, tableowner FROM pg_tables "
                "WHERE tablename IN ('users', 'memberships', 'organizations', 'brands')"
            )
        ).all()
    assert owners and all(o.tableowner != "creatoros_app" for o in owners)


def test_app_role_can_read_and_write_data(db):
    user_id, org_id, brand_id = seed_tenant(db)
    set_rls(db, tenant_id=org_id)
    assert db.scalar(select(Brand.name).where(Brand.id == brand_id)) == "Brand"
    db.execute(update(Brand).where(Brand.id == brand_id).values(name="Renamed"))
    assert db.execute(delete(Brand).where(Brand.id == brand_id)).rowcount == 1
    db.commit()


def test_app_role_cannot_create_tables(migrated):
    _refused("CREATE TABLE public.should_fail (id int)")


def test_app_role_cannot_drop_tables(migrated):
    with get_engine().connect() as c:
        with pytest.raises(DBAPIError) as exc:
            c.execute(text("DROP TABLE brands"))
        assert "must be owner" in str(exc.value.orig).lower()
        c.rollback()


def test_app_role_cannot_create_roles(migrated):
    _refused("CREATE ROLE should_fail")


def test_app_role_cannot_create_schemas(migrated):
    _refused("CREATE SCHEMA should_fail")
