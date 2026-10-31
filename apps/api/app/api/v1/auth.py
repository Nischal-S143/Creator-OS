from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AfterValidator, StringConstraints
from pydantic import BaseModel as PydanticBase

from app.schemas.core import Request
from app.security.local_auth import (
    TOKEN_SECONDS,
    AccountExists,
    AuthStoreError,
    InvalidCredentials,
    JsonAccountStore,
    LoginThrottle,
    TooManyAttempts,
    get_account_store,
    get_login_throttle,
    get_signing_key,
    issue_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    local, _, domain = value.partition("@")
    if not local or "." not in domain or " " in value:
        raise ValueError("must be an email address")
    return value


Email = Annotated[str, StringConstraints(max_length=320), AfterValidator(_normalize_email)]


class SignupRequest(Request):
    email: Email
    password: Annotated[str, StringConstraints(min_length=10, max_length=200)]


class LoginRequest(Request):
    email: Email
    password: Annotated[str, StringConstraints(max_length=200)]


class TokenResponse(PydanticBase):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int = TOKEN_SECONDS


unavailable = HTTPException(status_code=503, detail="sign-in is temporarily unavailable")


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, store: JsonAccountStore = Depends(get_account_store)) -> TokenResponse:
    try:
        account = store.create(body.email, body.password)
    except AccountExists as exc:
        raise HTTPException(status_code=409, detail="an account with this email already exists") from exc
    except AuthStoreError as exc:
        raise unavailable from exc
    return TokenResponse(access_token=issue_token(account, get_signing_key()))


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    store: JsonAccountStore = Depends(get_account_store),
    throttle: LoginThrottle = Depends(get_login_throttle),
) -> TokenResponse:
    try:
        throttle.check(body.email)
        account = store.authenticate(body.email, body.password)
    except TooManyAttempts as exc:
        raise HTTPException(status_code=429, detail="too many attempts; try again later") from exc
    except InvalidCredentials as exc:
        throttle.record_failure(body.email)
        raise HTTPException(status_code=401, detail="incorrect email or password") from exc
    except AuthStoreError as exc:
        raise unavailable from exc
    throttle.clear(body.email)
    return TokenResponse(access_token=issue_token(account, get_signing_key()))
