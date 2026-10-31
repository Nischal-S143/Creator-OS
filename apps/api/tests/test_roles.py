"""The runtime role must be able to use data and nothing else."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import get_engine


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
            text("SELECT tablename, tableowner FROM pg_tables WHERE tablename IN ('organizations', 'brands')")
        ).all()
    assert owners and all(o.tableowner != "creatoros_app" for o in owners)


def test_app_role_can_read_and_write_data(migrated):
    org_id, owner = uuid.uuid4(), uuid.uuid4()
    with get_engine().begin() as c:
        c.execute(
            text("INSERT INTO organizations (id, name, slug, owner_id) VALUES (:i, 'R', :s, :o)"),
            {"i": org_id, "s": f"r-{org_id.hex[:8]}", "o": owner},
        )
        assert (
            c.execute(text("SELECT name FROM organizations WHERE id = :i"), {"i": org_id}).scalar_one() == "R"
        )
        c.execute(text("UPDATE organizations SET name = 'S' WHERE id = :i"), {"i": org_id})
        c.execute(text("DELETE FROM organizations WHERE id = :i"), {"i": org_id})


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
