"""Row-level security on the real cluster, bypassing all API checks. Assumes the app itself has a bug."""

import uuid

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db.session import set_rls
from app.models import Brand, Membership, Organization, User
from tests.helpers import seed_tenant


@pytest.fixture
def tenants(db):
    return seed_tenant(db), seed_tenant(db)


@pytest.mark.parametrize("model", [Brand, Organization, Membership, User])
def test_no_context_sees_nothing(db, tenants, model):
    set_rls(db)
    assert db.scalar(select(func.count()).select_from(model)) == 0


def test_tenant_sees_only_its_own_rows(db, tenants):
    (a_user, a_org, a_brand), (_, b_org, b_brand) = tenants
    set_rls(db, tenant_id=a_org)
    assert set(db.scalars(select(Brand.id))) == {a_brand}
    assert set(db.scalars(select(Organization.id))) == {a_org}
    assert set(db.scalars(select(Membership.organization_id))) == {a_org}


def test_explicitly_asking_for_another_tenants_row_returns_nothing(db, tenants):
    (_, a_org, _), (_, _, b_brand) = tenants
    set_rls(db, tenant_id=a_org)
    assert db.scalar(select(Brand).where(Brand.id == b_brand)) is None


def test_cross_tenant_update_changes_nothing(db, tenants):
    (_, a_org, _), (_, b_org, b_brand) = tenants
    set_rls(db, tenant_id=a_org)
    assert db.execute(update(Brand).where(Brand.id == b_brand).values(name="hacked")).rowcount == 0
    assert db.execute(update(Organization).where(Organization.id == b_org).values(name="x")).rowcount == 0
    db.commit()
    set_rls(db, tenant_id=b_org)
    assert db.scalar(select(Brand.name).where(Brand.id == b_brand)) == "Brand"


def test_cross_tenant_delete_changes_nothing(db, tenants):
    (_, a_org, _), (_, _, b_brand) = tenants
    set_rls(db, tenant_id=a_org)
    assert db.execute(delete(Brand).where(Brand.id == b_brand)).rowcount == 0


def test_cannot_move_own_brand_to_another_tenant(db, tenants):
    (_, a_org, a_brand), (_, b_org, _) = tenants
    set_rls(db, tenant_id=a_org)
    with pytest.raises(DBAPIError):
        db.execute(update(Brand).where(Brand.id == a_brand).values(organization_id=b_org))
    db.rollback()


def test_cannot_insert_brand_into_another_tenant(db, tenants):
    (a_user, a_org, _), (b_user, b_org, _) = tenants
    set_rls(db, tenant_id=a_org)
    db.add(Brand(organization_id=b_org, name="x", slug="x", owner_id=b_user, created_by=a_user))
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_cannot_add_yourself_to_another_tenant(db, tenants):
    (a_user, a_org, _), (_, b_org, _) = tenants
    set_rls(db, tenant_id=a_org)
    db.add(Membership(organization_id=b_org, user_id=a_user, role="owner"))
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_brand_owner_must_be_a_member_of_that_tenant(db, tenants):
    (a_user, a_org, _), (b_user, _, _) = tenants
    set_rls(db, tenant_id=a_org)
    db.add(Brand(organization_id=a_org, name="x", slug="x", owner_id=b_user, created_by=a_user))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_users_are_visible_only_as_self_or_fellow_member(db, tenants):
    (a_user, a_org, _), (b_user, _, _) = tenants
    set_rls(db, user_id=a_user)
    assert set(db.scalars(select(User.id))) == {a_user}
    set_rls(db, tenant_id=a_org)
    assert set(db.scalars(select(User.id))) == {a_user}
    set_rls(db, user_id=a_user)
    assert db.scalar(select(User).where(User.id == b_user)) is None


def test_cannot_create_a_user_for_someone_elses_subject(db):
    set_rls(db, auth_subject="my-subject")
    db.add(User(auth_provider_id="someone-else", email=f"{uuid.uuid4().hex}@example.com"))
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_removed_member_no_longer_sees_the_organization(db, tenants):
    (a_user, a_org, _), _ = tenants
    set_rls(db, tenant_id=a_org)
    db.execute(update(Membership).where(Membership.user_id == a_user).values(status="removed"))
    db.commit()
    set_rls(db, user_id=a_user)
    assert db.scalar(select(Organization).where(Organization.id == a_org)) is None


def test_context_does_not_leak_to_the_next_session_on_a_pooled_connection(db, tenants):
    (_, a_org, _), _ = tenants
    set_rls(db, tenant_id=a_org)
    assert db.scalar(select(func.count()).select_from(Brand)) == 1
    db.commit()
    with db.get_bind().connect() as raw:
        assert raw.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar() in (None, "")
        assert raw.execute(text("SELECT count(*) FROM brands")).scalar() == 0


def test_context_survives_commit_within_a_session(db, tenants):
    (_, a_org, _), _ = tenants
    set_rls(db, tenant_id=a_org)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Brand)) == 1


def test_email_lookup_returns_only_an_id(db, tenants):
    (a_user, _, _), _ = tenants
    set_rls(db, auth_subject="nobody")
    email = None
    set_rls(db, user_id=a_user)
    email = db.scalar(select(User.email).where(User.id == a_user))
    set_rls(db)
    found = db.scalar(text("SELECT find_user_id_by_email(:e)"), {"e": email.upper()})
    assert found == a_user
    assert db.scalar(text("SELECT find_user_id_by_email('missing@example.com')")) is None


def test_repeated_queries_survive_the_connection_manager(db, tenants):
    """Regression: automatic prepared statements failed once a query repeated on the real cluster."""
    (_, a_org, _), _ = tenants
    set_rls(db, tenant_id=a_org)
    for _ in range(12):
        assert db.scalar(select(func.count()).select_from(Brand)) == 1
        db.commit()
