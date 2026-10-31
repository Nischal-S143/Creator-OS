"""Email and password accounts stored in a local JSON file.

The file holds only login details. All business data, including the matching users row, lives in
YugabyteDB. Writes are safe within one API process; running several processes needs a shared store.
"""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import get_settings

ISSUER = "creatoros"
AUDIENCE = "creatoros-api"
TOKEN_SECONDS = 3600
MAX_FAILURES = 5
LOCKOUT_SECONDS = 900

_SCRYPT = {"n": 2**15, "r": 8, "p": 1, "maxmem": 64 * 1024 * 1024, "dklen": 32}


class AccountExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class TooManyAttempts(Exception):
    pass


class AuthStoreError(Exception):
    """The accounts file is unreadable. Login fails closed rather than starting empty."""


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(candidate, bytes.fromhex(digest))


# Checked for unknown emails, so response time does not reveal whether an account exists.
_DUMMY_HASH = _hash_password(secrets.token_hex(16))


@dataclass(frozen=True)
class Account:
    subject: str
    email: str


class JsonAccountStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def _read(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise AuthStoreError("accounts file is unreadable") from exc
        if not isinstance(data, dict):
            raise AuthStoreError("accounts file is invalid")
        return data

    def _write(self, data: dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temporary, self._path)

    def create(self, email: str, password: str) -> Account:
        password_hash = _hash_password(password)
        with self._lock:
            data = self._read()
            if email in data:
                raise AccountExists
            subject = str(uuid.uuid4())
            data[email] = {
                "subject": subject,
                "password_hash": password_hash,
                "created_at": datetime.now(UTC).isoformat(),
            }
            self._write(data)
        return Account(subject=subject, email=email)

    def authenticate(self, email: str, password: str) -> Account:
        with self._lock:
            record = self._read().get(email)
        stored = record["password_hash"] if record else _DUMMY_HASH
        matches = _password_matches(password, stored)
        if record is None or not matches:
            raise InvalidCredentials
        return Account(subject=record["subject"], email=email)


class LoginThrottle:
    """Locks an email after repeated failures. In memory, so it resets when the API restarts."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}

    def _recent(self, email: str) -> list[float]:
        cutoff = self._clock() - LOCKOUT_SECONDS
        recent = [t for t in self._failures.get(email, []) if t > cutoff]
        if recent:
            self._failures[email] = recent
        else:
            self._failures.pop(email, None)
        return recent

    def check(self, email: str) -> None:
        with self._lock:
            if len(self._recent(email)) >= MAX_FAILURES:
                raise TooManyAttempts

    def record_failure(self, email: str) -> None:
        with self._lock:
            self._failures.setdefault(email, []).append(self._clock())

    def clear(self, email: str) -> None:
        with self._lock:
            self._failures.pop(email, None)


def load_signing_key(path: Path) -> ec.EllipticCurvePrivateKey:
    """Loads the token signing key, creating it on first use. The file must stay out of Git."""
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    key = ec.generate_private_key(ec.SECP256R1())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return key


def issue_token(account: Account, key: ec.EllipticCurvePrivateKey) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": account.subject,
            "email": account.email,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + TOKEN_SECONDS,
        },
        key,
        algorithm="ES256",
    )


@lru_cache
def get_account_store() -> JsonAccountStore:
    return JsonAccountStore(get_settings().auth_data_dir / "accounts.json")


@lru_cache
def get_signing_key() -> ec.EllipticCurvePrivateKey:
    return load_signing_key(get_settings().auth_data_dir / "signing_key.pem")


@lru_cache
def get_login_throttle() -> LoginThrottle:
    return LoginThrottle()
