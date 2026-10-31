"""Token validation with locally generated keys. No network."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.security.tokens import InvalidToken, KeysUnavailable, TokenVerifier

ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"
KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_PEM = KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)


def claims(**overrides) -> dict:
    base = {
        "sub": "user-1",
        "email": "Person@Example.com",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 300,
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def sign(payload: dict, key=KEY, algorithm="ES256") -> str:
    return jwt.encode(payload, key, algorithm=algorithm)


VERIFIER = TokenVerifier(ISSUER, AUDIENCE, lambda _token: KEY.public_key())


def test_valid_token_is_accepted_and_email_normalized():
    result = VERIFIER.verify(sign(claims()))
    assert result.subject == "user-1" and result.email == "person@example.com"


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 300},
        {"iss": "https://evil.example/auth/v1"},
        {"aud": "anon"},
        {"sub": None},
        {"exp": None},
        {"iss": None},
        {"aud": None},
        {"email": None},
        {"email": "not-an-email"},
    ],
    ids=[
        "expired",
        "wrong-issuer",
        "wrong-audience",
        "no-sub",
        "no-exp",
        "no-iss",
        "no-aud",
        "no-email",
        "bad-email",
    ],
)
def test_bad_claims_are_refused(overrides):
    with pytest.raises(InvalidToken):
        VERIFIER.verify(sign(claims(**overrides)))


def test_token_signed_by_another_key_is_refused():
    with pytest.raises(InvalidToken):
        VERIFIER.verify(sign(claims(), key=OTHER_KEY))


def test_tampered_payload_is_refused():
    header, payload, signature = sign(claims()).split(".")
    forged = jwt.utils.base64url_encode(b'{"sub":"admin","email":"a@b.c"}').decode()
    with pytest.raises(InvalidToken):
        VERIFIER.verify(f"{header}.{forged}.{signature}")


def test_unsigned_token_is_refused():
    with pytest.raises(InvalidToken):
        VERIFIER.verify(jwt.encode(claims(), None, algorithm="none"))


def test_hmac_key_confusion_is_refused():
    header = jwt.utils.base64url_encode(b'{"alg":"HS256","typ":"JWT"}').decode()
    import hashlib
    import hmac
    import json

    body = jwt.utils.base64url_encode(json.dumps(claims()).encode()).decode()
    mac = hmac.new(PUBLIC_PEM, f"{header}.{body}".encode(), hashlib.sha256).digest()
    forged = f"{header}.{body}.{jwt.utils.base64url_encode(mac).decode()}"
    verifier = TokenVerifier(ISSUER, AUDIENCE, lambda _token: PUBLIC_PEM)
    with pytest.raises(InvalidToken):
        verifier.verify(forged)


def test_garbage_is_refused():
    with pytest.raises(InvalidToken):
        VERIFIER.verify("not.a.token")


def test_unknown_key_id_is_refused():
    def resolve(_token):
        raise jwt.PyJWKClientError("no matching key")

    with pytest.raises(InvalidToken):
        TokenVerifier(ISSUER, AUDIENCE, resolve).verify(sign(claims()))


def test_unreachable_key_endpoint_is_reported_separately():
    def resolve(_token):
        raise jwt.PyJWKClientConnectionError("down")

    with pytest.raises(KeysUnavailable):
        TokenVerifier(ISSUER, AUDIENCE, resolve).verify(sign(claims()))
