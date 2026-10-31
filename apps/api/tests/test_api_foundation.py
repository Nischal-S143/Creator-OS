"""Identity, organization, member and brand APIs on the real cluster, including attacks between tenants."""

import uuid

import pytest

from app.main import app
from tests.helpers import unique


def api(path: str) -> str:
    return f"/api/v1{path}"


def new_org(client, headers) -> str:
    r = client.post(api("/organizations"), json={"name": "Agency", "slug": unique("org")}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def new_brand(client, headers, org) -> str:
    r = client.post(
        api(f"/organizations/{org}/brands"), json={"name": "Acme", "slug": unique("b")}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_member(client, owner, org, person, role) -> dict:
    email = client.get(api("/me"), headers=person).json()["email"]
    r = client.post(api(f"/organizations/{org}/members"), json={"email": email, "role": role}, headers=owner)
    assert r.status_code == 201, r.text
    return r.json()


def test_every_tenant_route_refuses_anonymous_callers(client):
    fake = uuid.uuid4()
    for method, path in [
        ("get", "/me"),
        ("get", "/organizations"),
        ("post", "/organizations"),
        ("get", f"/organizations/{fake}/members"),
        ("post", f"/organizations/{fake}/members"),
        ("patch", f"/organizations/{fake}/members/{fake}"),
        ("get", f"/organizations/{fake}/brands"),
        ("post", f"/organizations/{fake}/brands"),
        ("get", f"/organizations/{fake}/brands/{fake}"),
        ("patch", f"/organizations/{fake}/brands/{fake}"),
    ]:
        assert getattr(client, method)(api(path), headers={}).status_code == 401, path


def test_no_route_is_left_unprotected(client):
    public = {
        "/health/db",
        "/api/v1/ai/test",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/oauth2-redirect",
    }
    paths = client.get("/openapi.json").json()["paths"]
    for path, methods in paths.items():
        if path in public:
            continue
        for operation in methods.values():
            assert operation.get("security"), f"{path} has no bearer requirement"


def test_first_request_creates_the_user_once(client, make_user):
    headers = make_user()
    first = client.get(api("/me"), headers=headers).json()
    second = client.get(api("/me"), headers=headers).json()
    assert first["id"] == second["id"] and first["organizations"] == []


def test_invalid_token_is_refused(client):
    assert client.get(api("/me"), headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_two_accounts_cannot_claim_one_email(client, make_user):
    email = f"{unique('shared')}@example.com"
    assert client.get(api("/me"), headers=make_user(email=email)).status_code == 200
    assert client.get(api("/me"), headers=make_user(email=email)).status_code == 409


def test_signup_to_brand_flow(client, make_user):
    owner = make_user()
    org = new_org(client, owner)
    me = client.get(api("/me"), headers=owner).json()
    assert [o["id"] for o in me["organizations"]] == [org]
    assert me["organizations"][0]["role"] == "owner"
    brand = new_brand(client, owner, org)
    page = client.get(api(f"/organizations/{org}/brands"), headers=owner).json()
    assert [b["id"] for b in page["items"]] == [brand] and page["total"] == 1
    r = client.patch(
        api(f"/organizations/{org}/brands/{brand}"),
        json={"industry": "Fitness", "website_url": "https://acme.example/"},
        headers=owner,
    )
    assert r.status_code == 200 and r.json()["industry"] == "Fitness"


def test_pagination_limits(client, make_user):
    owner = make_user()
    org = new_org(client, owner)
    for _ in range(3):
        new_brand(client, owner, org)
    page = client.get(api(f"/organizations/{org}/brands?limit=2&offset=1"), headers=owner).json()
    assert len(page["items"]) == 2 and page["total"] == 3 and page["offset"] == 1
    assert client.get(api(f"/organizations/{org}/brands?limit=1000"), headers=owner).status_code == 422


def test_duplicate_slugs_conflict(client, make_user):
    owner = make_user()
    slug = unique("dup")
    body = {"name": "A", "slug": slug}
    assert client.post(api("/organizations"), json=body, headers=owner).status_code == 201
    assert client.post(api("/organizations"), json=body, headers=make_user()).status_code == 409


# --- Attacks between tenants ---


@pytest.fixture
def two_tenants(client, make_user):
    a, b = make_user(), make_user()
    a_org, b_org = new_org(client, a), new_org(client, b)
    return a, a_org, new_brand(client, a, a_org), b, b_org, new_brand(client, b, b_org)


def test_non_member_gets_404_on_every_route_of_another_org(client, two_tenants):
    a, _, _, _, b_org, b_brand = two_tenants
    base = f"/organizations/{b_org}"
    for method, path, body in [
        ("get", f"{base}/members", None),
        ("post", f"{base}/members", {"email": "x@example.com", "role": "owner"}),
        ("patch", f"{base}/members/{uuid.uuid4()}", {"role": "owner"}),
        ("get", f"{base}/brands", None),
        ("post", f"{base}/brands", {"name": "x", "slug": "xx"}),
        ("get", f"{base}/brands/{b_brand}", None),
        ("patch", f"{base}/brands/{b_brand}", {"name": "hacked"}),
    ]:
        kwargs = {"json": body} if body else {}
        assert getattr(client, method)(api(path), headers=a, **kwargs).status_code == 404, path


def test_cannot_reach_another_tenants_brand_through_own_org_path(client, two_tenants):
    a, a_org, _, _, _, b_brand = two_tenants
    path = api(f"/organizations/{a_org}/brands/{b_brand}")
    assert client.get(path, headers=a).status_code == 404
    assert client.patch(path, json={"name": "hacked"}, headers=a).status_code == 404


def test_cannot_reach_another_tenants_member_through_own_org_path(client, two_tenants):
    a, a_org, _, b, b_org, _ = two_tenants
    members = client.get(api(f"/organizations/{b_org}/members"), headers=b).json()["items"]
    r = client.patch(
        api(f"/organizations/{a_org}/members/{members[0]['id']}"), json={"status": "removed"}, headers=a
    )
    assert r.status_code == 404


def test_listings_never_include_another_tenant(client, two_tenants):
    a, a_org, a_brand, _, b_org, _ = two_tenants
    orgs = client.get(api("/organizations"), headers=a).json()["items"]
    assert {o["id"] for o in orgs} == {a_org} and b_org not in str(orgs)
    brands = client.get(api(f"/organizations/{a_org}/brands"), headers=a).json()["items"]
    assert {b["id"] for b in brands} == {a_brand}


@pytest.mark.parametrize(
    "extra",
    [{"organization_id": str(uuid.uuid4())}, {"meko_datapack_id": "stolen"}, {"owner_id": str(uuid.uuid4())}],
    ids=["organization_id", "meko_datapack_id", "owner_id"],
)
def test_client_cannot_set_protected_brand_fields(client, two_tenants, extra):
    a, a_org, _, _, _, _ = two_tenants
    r = client.post(
        api(f"/organizations/{a_org}/brands"), json={"name": "x", "slug": unique("b"), **extra}, headers=a
    )
    assert r.status_code == 422


def test_client_cannot_set_datapack_on_update(client, two_tenants):
    a, a_org, a_brand, _, _, _ = two_tenants
    r = client.patch(
        api(f"/organizations/{a_org}/brands/{a_brand}"), json={"meko_datapack_id": "stolen"}, headers=a
    )
    assert r.status_code == 422


def test_cannot_hand_a_brand_to_someone_outside_the_org(client, two_tenants):
    a, a_org, a_brand, b, _, _ = two_tenants
    b_id = client.get(api("/me"), headers=b).json()["id"]
    r = client.patch(api(f"/organizations/{a_org}/brands/{a_brand}"), json={"owner_id": b_id}, headers=a)
    assert r.status_code == 422


# --- Roles ---


@pytest.mark.parametrize(
    "role,view,create,edit,members",
    [
        ("admin", 200, 201, 200, 200),
        ("manager", 200, 403, 200, 200),
        ("editor", 200, 403, 200, 403),
        ("analyst", 200, 403, 403, 403),
        ("client_approver", 403, 403, 403, 403),
    ],
)
def test_role_enforcement_over_http(client, make_user, role, view, create, edit, members):
    owner, person = make_user(), make_user()
    org = new_org(client, owner)
    brand = new_brand(client, owner, org)
    add_member(client, owner, org, person, role)
    base = f"/organizations/{org}"
    assert client.get(api(f"{base}/brands/{brand}"), headers=person).status_code == view
    assert (
        client.post(
            api(f"{base}/brands"), json={"name": "N", "slug": unique("b")}, headers=person
        ).status_code
        == create
    )
    assert client.patch(api(f"{base}/brands/{brand}"), json={"name": "N"}, headers=person).status_code == edit
    assert client.get(api(f"{base}/members"), headers=person).status_code == members


def test_admin_cannot_grant_or_change_owner(client, make_user):
    owner, admin, other = make_user(), make_user(), make_user()
    org = new_org(client, owner)
    add_member(client, owner, org, admin, "admin")
    email = client.get(api("/me"), headers=other).json()["email"]
    base = api(f"/organizations/{org}/members")
    assert client.post(base, json={"email": email, "role": "owner"}, headers=admin).status_code == 403
    items = client.get(base, headers=owner).json()["items"]
    owner_row = next(m for m in items if m["role"] == "owner")
    admin_row = next(m for m in items if m["role"] == "admin")
    assert (
        client.patch(f"{base}/{owner_row['id']}", json={"status": "removed"}, headers=admin).status_code
        == 403
    )
    assert client.patch(f"{base}/{admin_row['id']}", json={"role": "owner"}, headers=admin).status_code == 403


def test_last_owner_cannot_leave_or_be_demoted(client, make_user):
    owner = make_user()
    org = new_org(client, owner)
    base = api(f"/organizations/{org}/members")
    row = client.get(base, headers=owner).json()["items"][0]
    assert client.patch(f"{base}/{row['id']}", json={"status": "removed"}, headers=owner).status_code == 409
    assert client.patch(f"{base}/{row['id']}", json={"role": "editor"}, headers=owner).status_code == 409


def test_removed_member_loses_access_immediately(client, make_user):
    owner, person = make_user(), make_user()
    org = new_org(client, owner)
    brand = new_brand(client, owner, org)
    member = add_member(client, owner, org, person, "editor")
    path = api(f"/organizations/{org}/brands/{brand}")
    assert client.get(path, headers=person).status_code == 200
    r = client.patch(
        api(f"/organizations/{org}/members/{member['id']}"), json={"status": "removed"}, headers=owner
    )
    assert r.status_code == 200
    assert client.get(path, headers=person).status_code == 404
    assert client.get(api("/me"), headers=person).json()["organizations"] == []


def test_auth_not_configured_fails_closed(client, make_user):
    from app.security.tokens import get_token_verifier

    headers = make_user()
    app.dependency_overrides[get_token_verifier] = lambda: None
    assert client.get(api("/me"), headers=headers).status_code == 503
