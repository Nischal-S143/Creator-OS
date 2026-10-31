import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db, set_rls
from app.models import Membership, Organization, User
from app.schemas.core import (
    Limit,
    MemberAdd,
    MemberOut,
    MemberUpdate,
    MeOut,
    Offset,
    OrganizationCreate,
    OrganizationOut,
    OrganizationWithRole,
    Page,
)
from app.security.context import TenantContext, get_current_user, require
from app.security.permissions import Permission

router = APIRouter(prefix="/api/v1", tags=["organizations"])


def _user_organizations(db: Session, user: User):
    return (
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id, Membership.status == "active")
    )


def _with_role(organization: Organization, role: str) -> OrganizationWithRole:
    return OrganizationWithRole(
        **OrganizationOut.model_validate(organization).model_dump(),
        role=role,
    )


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    rows = db.execute(_user_organizations(db, user).order_by(Organization.created_at)).all()
    return MeOut(id=user.id, email=user.email, organizations=[_with_role(o, r) for o, r in rows])


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(
    body: OrganizationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Organization:
    org_id = uuid.uuid4()
    set_rls(db, auth_subject=user.auth_provider_id, user_id=user.id, tenant_id=org_id)
    organization = Organization(id=org_id, name=body.name, slug=body.slug, owner_id=user.id)
    db.add(organization)
    try:
        db.flush()
        db.add(Membership(organization_id=org_id, user_id=user.id, role="owner"))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug is already in use") from exc
    return organization


@router.get("/organizations", response_model=Page[OrganizationWithRole])
def list_organizations(
    limit: Limit = 50,
    offset: Offset = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[OrganizationWithRole]:
    query = _user_organizations(db, user)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(Organization.created_at).limit(limit).offset(offset)).all()
    return Page(items=[_with_role(o, r) for o, r in rows], total=total, limit=limit, offset=offset)


def _member_out(membership: Membership, email: str) -> MemberOut:
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=email,
        role=membership.role,
        status=membership.status,
    )


def _active_owner_count(db: Session, org_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.organization_id == org_id,
            Membership.role == "owner",
            Membership.status == "active",
        )
    )


@router.get("/organizations/{org_id}/members", response_model=Page[MemberOut])
def list_members(
    limit: Limit = 50,
    offset: Offset = 0,
    tenant: TenantContext = Depends(require(Permission.MEMBERS_VIEW)),
    db: Session = Depends(get_db),
) -> Page[MemberOut]:
    scope = Membership.organization_id == tenant.organization_id
    total = db.scalar(select(func.count()).select_from(Membership).where(scope))
    rows = db.execute(
        select(Membership, User.email)
        .join(User, User.id == Membership.user_id)
        .where(scope)
        .order_by(Membership.created_at)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=[_member_out(m, e) for m, e in rows], total=total, limit=limit, offset=offset)


@router.post("/organizations/{org_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    body: MemberAdd,
    tenant: TenantContext = Depends(require(Permission.MEMBERS_MANAGE)),
    db: Session = Depends(get_db),
) -> MemberOut:
    if body.role == "owner" and tenant.role != "owner":
        raise HTTPException(status_code=403, detail="only an owner can grant the owner role")
    user_id = db.scalar(text("SELECT find_user_id_by_email(:email)"), {"email": body.email})
    if user_id is None:
        raise HTTPException(status_code=404, detail="no account with that email; they must sign up first")
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == tenant.organization_id, Membership.user_id == user_id
        )
    )
    if membership is not None and membership.status == "active":
        raise HTTPException(status_code=409, detail="already a member")
    if membership is not None and membership.role == "owner" and tenant.role != "owner":
        raise HTTPException(status_code=403, detail="only an owner can change an owner")
    if membership is None:
        membership = Membership(organization_id=tenant.organization_id, user_id=user_id, role=body.role)
        db.add(membership)
    else:
        membership.role, membership.status = body.role, "active"
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="already a member") from exc
    return _member_out(membership, body.email)


@router.patch("/organizations/{org_id}/members/{member_id}", response_model=MemberOut)
def update_member(
    member_id: uuid.UUID,
    body: MemberUpdate,
    tenant: TenantContext = Depends(require(Permission.MEMBERS_MANAGE)),
    db: Session = Depends(get_db),
) -> MemberOut:
    row = db.execute(
        select(Membership, User.email)
        .join(User, User.id == Membership.user_id)
        .where(Membership.id == member_id, Membership.organization_id == tenant.organization_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="member not found")
    membership, email = row
    new_role = body.role or membership.role
    new_status = body.status or membership.status
    touches_owner = membership.role == "owner" or new_role == "owner"
    if touches_owner and tenant.role != "owner":
        raise HTTPException(status_code=403, detail="only an owner can change an owner")
    loses_owner = (
        membership.role == "owner"
        and membership.status == "active"
        and (new_role != "owner" or new_status != "active")
    )
    if loses_owner and _active_owner_count(db, tenant.organization_id) <= 1:
        raise HTTPException(status_code=409, detail="an organization must keep at least one owner")
    membership.role, membership.status = new_role, new_status
    db.commit()
    return _member_out(membership, email)
