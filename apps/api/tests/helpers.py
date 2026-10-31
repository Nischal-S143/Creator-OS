import uuid

from sqlalchemy.orm import Session

from app.db.session import set_rls
from app.models import Brand, Membership, Organization, User


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def seed_tenant(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Creates a user, organization and brand through the app role. Returns their ids."""
    subject = unique("sub")
    user_id, org_id, brand_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    set_rls(db, auth_subject=subject)
    db.add(User(id=user_id, auth_provider_id=subject, email=f"{subject}@example.com"))
    db.commit()
    set_rls(db, auth_subject=subject, user_id=user_id, tenant_id=org_id)
    db.add(Organization(id=org_id, name="Org", slug=unique("org"), owner_id=user_id))
    db.flush()
    db.add(Membership(organization_id=org_id, user_id=user_id, role="owner"))
    db.flush()
    db.add(
        Brand(
            id=brand_id,
            organization_id=org_id,
            name="Brand",
            slug="main",
            owner_id=user_id,
            created_by=user_id,
        )
    )
    db.commit()
    set_rls(db)
    return user_id, org_id, brand_id
