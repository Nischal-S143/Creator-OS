import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Brand
from app.schemas.core import BrandCreate, BrandOut, BrandUpdate, Limit, Offset, Page
from app.security.context import TenantContext, require
from app.security.permissions import Permission

router = APIRouter(prefix="/api/v1/organizations/{org_id}/brands", tags=["brands"])


def _get_brand(db: Session, tenant: TenantContext, brand_id: uuid.UUID) -> Brand:
    brand = db.scalar(
        select(Brand).where(Brand.id == brand_id, Brand.organization_id == tenant.organization_id)
    )
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")
    return brand


@router.post("", response_model=BrandOut, status_code=201)
def create_brand(
    body: BrandCreate,
    tenant: TenantContext = Depends(require(Permission.BRAND_CREATE)),
    db: Session = Depends(get_db),
) -> Brand:
    brand = Brand(
        organization_id=tenant.organization_id,
        name=body.name,
        slug=body.slug,
        industry=body.industry,
        website_url=str(body.website_url) if body.website_url else None,
        owner_id=tenant.user.id,
        created_by=tenant.user.id,
    )
    db.add(brand)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug is already in use") from exc
    return brand


@router.get("", response_model=Page[BrandOut])
def list_brands(
    limit: Limit = 50,
    offset: Offset = 0,
    tenant: TenantContext = Depends(require(Permission.BRAND_VIEW)),
    db: Session = Depends(get_db),
) -> Page[BrandOut]:
    scope = Brand.organization_id == tenant.organization_id
    total = db.scalar(select(func.count()).select_from(Brand).where(scope))
    items = db.scalars(select(Brand).where(scope).order_by(Brand.created_at).limit(limit).offset(offset))
    return Page(
        items=[BrandOut.model_validate(b) for b in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.BRAND_VIEW)),
    db: Session = Depends(get_db),
) -> Brand:
    return _get_brand(db, tenant, brand_id)


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    tenant: TenantContext = Depends(require(Permission.BRAND_EDIT)),
    db: Session = Depends(get_db),
) -> Brand:
    brand = _get_brand(db, tenant, brand_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("website_url") is not None:
        changes["website_url"] = str(changes["website_url"])
    for field, value in changes.items():
        setattr(brand, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="owner must be a member of this organization") from exc
    return brand
