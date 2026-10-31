import uuid

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db import get_db, get_engine
from app.models import Brand, Organization


def _org(slug: str | None = None) -> Organization:
    return Organization(name="Acme", slug=slug or f"acme-{uuid.uuid4().hex[:8]}", owner_id=uuid.uuid4())


def test_tables_and_tenant_columns_exist(migrated):
    insp = inspect(get_engine())
    assert {"organizations", "brands"} <= set(insp.get_table_names())
    brand_cols = {c["name"] for c in insp.get_columns("brands")}
    assert {"organization_id", "owner_id", "created_by"} <= brand_cols
    assert "owner_id" in {c["name"] for c in insp.get_columns("organizations")}


def test_insert_and_read_back(db: Session):
    org = _org()
    org.brands.append(Brand(name="Main", slug="main", owner_id=org.owner_id, created_by=org.owner_id))
    db.add(org)
    db.commit()
    brand = db.scalars(select(Brand).where(Brand.organization_id == org.id)).one()
    assert brand.organization_id == org.id and brand.created_at is not None


def test_brand_slug_unique_per_organization(db: Session):
    a, b = _org(), _org()
    db.add_all([a, b])
    db.commit()
    uid = uuid.uuid4()
    db.add(Brand(organization_id=a.id, name="X", slug="x", owner_id=uid, created_by=uid))
    db.add(Brand(organization_id=b.id, name="X", slug="x", owner_id=uid, created_by=uid))
    db.commit()  # same slug in different tenants is allowed
    db.add(Brand(organization_id=a.id, name="Y", slug="x", owner_id=uid, created_by=uid))
    with pytest.raises(IntegrityError):
        db.commit()


def test_brand_requires_existing_organization(db: Session):
    uid = uuid.uuid4()
    db.add(Brand(organization_id=uuid.uuid4(), name="Orphan", slug="o", owner_id=uid, created_by=uid))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_organization_cascades_to_brands(db: Session):
    org = _org()
    org.brands.append(Brand(name="B", slug="b", owner_id=org.owner_id, created_by=org.owner_id))
    db.add(org)
    db.commit()
    org_id = org.id
    db.delete(org)
    db.commit()
    assert db.scalars(select(Brand).where(Brand.organization_id == org_id)).first() is None


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
    assert {"organizations", "brands"} <= set(inspect(get_engine()).get_table_names())
