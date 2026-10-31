"""JSON file accounts and token issue. Only the last test touches the database."""

import json
import threading

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.security import local_auth
from app.security.local_auth import (
    LOCKOUT_SECONDS,
    MAX_FAILURES,
    AccountExists,
    AuthStoreError,
    InvalidCredentials,
    JsonAccountStore,
    LoginThrottle,
    TooManyAttempts,
)
from app.security.tokens import InvalidToken, get_token_verifier

PASSWORD = "correct-horse-battery"  # noqa: S105


def _clear_caches() -> None:
    get_settings.cache_clear()
    local_auth.get_account_store.cache_clear()
    local_auth.get_signing_key.cache_clear()
    local_auth.get_login_throttle.cache_clear()
    get_token_verifier.cache_clear()


@pytest.fixture
def auth_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DATA_DIR", str(tmp_path))
    _clear_caches()
    yield tmp_path
    monkeypatch.undo()
    _clear_caches()


@pytest.fixture
def http(auth_dir):
    return TestClient(create_app())


def signup(http, email="person@example.com", password=PASSWORD):
    return http.post("/api/v1/auth/signup", json={"email": email, "password": password})


def login(http, email="person@example.com", password=PASSWORD):
    return http.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_file_never_contains_the_password(http, auth_dir):
    assert signup(http).status_code == 201
    raw = (auth_dir / "accounts.json").read_text()
    assert PASSWORD not in raw
    assert json.loads(raw)["person@example.com"]["password_hash"].startswith("scrypt$")


def test_signup_then_login_gives_a_token_the_api_accepts(http):
    created = signup(http).json()
    logged_in = login(http)
    assert logged_in.status_code == 200
    verifier = get_token_verifier()
    assert verifier.verify(created["access_token"]).email == "person@example.com"
    assert (
        verifier.verify(logged_in.json()["access_token"]).subject
        == verifier.verify(created["access_token"]).subject
    )


def test_email_is_case_insensitive(http):
    signup(http, email="Person@Example.com")
    assert login(http, email="PERSON@example.com").status_code == 200
    assert signup(http, email="person@EXAMPLE.com").status_code == 409


def test_wrong_password_and_unknown_email_look_identical(http):
    signup(http)
    wrong = login(http, password="wrong-password-here")
    unknown = login(http, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


@pytest.mark.parametrize(
    "body",
    [
        {"email": "person@example.com", "password": "short"},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "person@example.com", "password": PASSWORD, "role": "owner"},
    ],
    ids=["weak-password", "bad-email", "extra-field"],
)
def test_bad_signups_are_refused(http, body):
    assert http.post("/api/v1/auth/signup", json=body).status_code == 422


def test_lockout_after_repeated_failures_even_with_the_right_password(http):
    signup(http)
    for _ in range(MAX_FAILURES):
        assert login(http, password="wrong-password-here").status_code == 401
    assert login(http).status_code == 429


def test_success_clears_failures(http):
    signup(http)
    for _ in range(MAX_FAILURES - 1):
        login(http, password="wrong-password-here")
    assert login(http).status_code == 200
    assert login(http, password="wrong-password-here").status_code == 401
    assert login(http).status_code == 200


def test_lockout_expires():
    now = [0.0]
    throttle = LoginThrottle(clock=lambda: now[0])
    for _ in range(MAX_FAILURES):
        throttle.record_failure("a@b.c")
    with pytest.raises(TooManyAttempts):
        throttle.check("a@b.c")
    now[0] += LOCKOUT_SECONDS + 1
    throttle.check("a@b.c")


def test_corrupt_file_fails_closed(http, auth_dir):
    signup(http)
    (auth_dir / "accounts.json").write_text("{broken")
    assert login(http).status_code == 503
    assert signup(http, email="new@example.com").status_code == 503
    assert (auth_dir / "accounts.json").read_text() == "{broken"


def test_concurrent_signups_all_persist(tmp_path):
    store = JsonAccountStore(tmp_path / "accounts.json")
    errors = []

    def create(i):
        try:
            store.create(f"user{i}@example.com", PASSWORD)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=create, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(json.loads((tmp_path / "accounts.json").read_text())) == 6
    assert not list(tmp_path.glob("*.tmp"))


def test_duplicate_and_bad_password_at_store_level(tmp_path):
    store = JsonAccountStore(tmp_path / "accounts.json")
    store.create("a@example.com", PASSWORD)
    with pytest.raises(AccountExists):
        store.create("a@example.com", PASSWORD)
    with pytest.raises(InvalidCredentials):
        store.authenticate("a@example.com", "nope-nope-nope")
    (tmp_path / "accounts.json").write_text("[]")
    with pytest.raises(AuthStoreError):
        store.authenticate("a@example.com", PASSWORD)


def test_token_from_another_signing_key_is_refused(http, tmp_path):
    other = local_auth.load_signing_key(tmp_path / "other" / "key.pem")
    forged = local_auth.issue_token(local_auth.Account("attacker", "a@example.com"), other)
    with pytest.raises(InvalidToken):
        get_token_verifier().verify(forged)


def test_signing_key_survives_restart(auth_dir):
    first = local_auth.load_signing_key(auth_dir / "signing_key.pem")
    second = local_auth.load_signing_key(auth_dir / "signing_key.pem")
    assert first.private_numbers() == second.private_numbers()


def test_sign_up_stores_business_data_in_yugabyte(migrated, auth_dir):
    from app.main import app

    with TestClient(app) as http:
        token = signup(http).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = http.get("/api/v1/me", headers=headers)
        assert me.status_code == 200 and me.json()["email"] == "person@example.com"
        slug = f"org-{me.json()['id'][:8]}"
        org = http.post("/api/v1/organizations", json={"name": "Agency", "slug": slug}, headers=headers)
        assert org.status_code == 201
        assert [o["id"] for o in http.get("/api/v1/me", headers=headers).json()["organizations"]] == [
            org.json()["id"]
        ]
    assert "Agency" not in (auth_dir / "accounts.json").read_text()
