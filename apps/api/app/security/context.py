import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db, set_rls
from app.models import Membership, User
from app.security.permissions import Permission, has_permission
from app.security.tokens import (
    InvalidToken,
    KeysUnavailable,
    TokenClaims,
    TokenVerifier,
    get_token_verifier,
)

_bearer = HTTPBearer(auto_error=False)


def get_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    verifier: TokenVerifier | None = Depends(get_token_verifier),
) -> TokenClaims:
    unauthenticated = HTTPException(
        status_code=401, detail="not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthenticated
    if verifier is None:
        raise HTTPException(status_code=503, detail="authentication is not configured")
    try:
        return verifier.verify(credentials.credentials)
    except KeysUnavailable as exc:
        raise HTTPException(status_code=503, detail="authentication is unavailable") from exc
    except InvalidToken as exc:
        raise unauthenticated from exc


def get_current_user(claims: TokenClaims = Depends(get_claims), db: Session = Depends(get_db)) -> User:
    set_rls(db, auth_subject=claims.subject)
    user = db.scalar(select(User).where(User.auth_provider_id == claims.subject))
    if user is None:
        user = User(auth_provider_id=claims.subject, email=claims.email)
        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            # Either a concurrent first request created this user, or the email belongs to another account.
            user = db.scalar(select(User).where(User.auth_provider_id == claims.subject))
            if user is None:
                raise HTTPException(status_code=409, detail="email is already in use") from exc
    elif user.email != claims.email:
        user.email = claims.email
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="email is already in use") from exc
    set_rls(db, auth_subject=claims.subject, user_id=user.id)
    return user


@dataclass(frozen=True)
class TenantContext:
    user: User
    organization_id: uuid.UUID
    role: str


def get_tenant(
    org_id: uuid.UUID = Path(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Sets the tenant only after confirming an active membership. Non-members see 404, not 403."""
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user.id,
            Membership.status == "active",
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="organization not found")
    set_rls(db, auth_subject=user.auth_provider_id, user_id=user.id, tenant_id=org_id)
    return TenantContext(user=user, organization_id=org_id, role=membership.role)


def require(permission: Permission) -> Callable[..., TenantContext]:
    def dependency(tenant: TenantContext = Depends(get_tenant)) -> TenantContext:
        if not has_permission(tenant.role, permission):
            raise HTTPException(status_code=403, detail="forbidden")
        return tenant

    return dependency
