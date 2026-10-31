from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from app.security import local_auth

# Asymmetric only. HS256 stays excluded: accepting it invites key-confusion attacks.
ALLOWED_ALGORITHMS = ["ES256", "RS256"]


class InvalidToken(Exception):
    """The token is not acceptable. Callers respond with 401."""


class KeysUnavailable(Exception):
    """The provider's public keys could not be fetched. Callers respond with 503."""


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    email: str


class TokenVerifier:
    def __init__(self, issuer: str, audience: str, resolve_key: Callable[[str], Any]):
        self._issuer = issuer
        self._audience = audience
        self._resolve_key = resolve_key

    def verify(self, token: str) -> TokenClaims:
        try:
            key = self._resolve_key(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=ALLOWED_ALGORITHMS,
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise KeysUnavailable from exc
        except jwt.PyJWTError as exc:
            raise InvalidToken(type(exc).__name__) from exc
        subject, email = claims.get("sub"), claims.get("email")
        if not subject or not isinstance(email, str) or "@" not in email:
            raise InvalidToken("missing identity claims")
        return TokenClaims(subject=subject, email=email.strip().lower())


@lru_cache
def get_token_verifier() -> TokenVerifier | None:
    public_key = local_auth.get_signing_key().public_key()
    return TokenVerifier(local_auth.ISSUER, local_auth.AUDIENCE, lambda _token: public_key)
