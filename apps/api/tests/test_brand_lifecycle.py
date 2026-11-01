"""Deleting a client archives it: hidden and blocked, but its records are not destroyed."""

import uuid

from tests.helpers import unique
from tests.test_api_foundation import add_member, api, new_brand, new_org


def test_delete_hides_the_brand_and_blocks_new_actions(client, make_user):
    headers = make_user()
    org = new_org(client, headers)
    brand = new_brand(client, headers, org)
    base = f"/organizations/{org}/brands/{brand}"

    assert client.get(api(base), headers=headers).status_code == 200
    deleted = client.delete(api(base), headers=headers)
    assert deleted.status_code == 204

    assert client.get(api(base), headers=headers).status_code == 404
    listed = client.get(api(f"/organizations/{org}/brands"), headers=headers).json()
    assert brand not in {item["id"] for item in listed["items"]}
    assert client.patch(api(base), json={"name": "New name"}, headers=headers).status_code == 404

    # Routes that share the same lookup are blocked too, so a deleted client cannot be used for anything new.
    upload = client.post(api(f"{base}/documents"), files={"file": ("g.txt", b"guidelines")}, headers=headers)
    assert upload.status_code == 404
    campaign = client.post(api(f"{base}/campaigns"), json={"name": "C", "objective": "Grow"}, headers=headers)
    assert campaign.status_code == 404


def test_deleting_twice_is_not_found_the_second_time(client, make_user):
    headers = make_user()
    org = new_org(client, headers)
    brand = new_brand(client, headers, org)
    base = api(f"/organizations/{org}/brands/{brand}")
    assert client.delete(base, headers=headers).status_code == 204
    assert client.delete(base, headers=headers).status_code == 404


def test_only_owner_or_admin_can_delete_a_client(client, make_user):
    owner = make_user()
    org = new_org(client, owner)
    brand = new_brand(client, owner, org)
    path = api(f"/organizations/{org}/brands/{brand}")
    for role in ("manager", "editor", "analyst"):
        person = make_user()
        add_member(client, owner, org, person, role)
        assert client.delete(path, headers=person).status_code == 403
    admin = make_user()
    add_member(client, owner, org, admin, "admin")
    assert client.delete(path, headers=admin).status_code == 204


def test_cannot_delete_another_tenants_client(client, make_user):
    a = make_user()
    a_org = new_org(client, a)
    a_brand = new_brand(client, a, a_org)
    b = make_user()
    b_org = new_org(client, b)
    # Even through B's own organization path, A's brand id is never found.
    forged = api(f"/organizations/{b_org}/brands/{a_brand}")
    assert client.delete(forged, headers=b).status_code == 404
    assert client.get(api(f"/organizations/{a_org}/brands/{a_brand}"), headers=a).status_code == 200


def test_fresh_brand_with_the_same_slug_can_be_created_after_deletion(client, make_user):
    headers = make_user()
    org = new_org(client, headers)
    slug = unique("coffee")
    first = client.post(
        api(f"/organizations/{org}/brands"), json={"name": "Peak Trail", "slug": slug}, headers=headers
    )
    assert first.status_code == 201
    client.delete(api(f"/organizations/{org}/brands/{first.json()['id']}"), headers=headers)
    # Deleting frees the slug, so the same name can be used again.
    again = client.post(
        api(f"/organizations/{org}/brands"), json={"name": "Peak Trail II", "slug": slug}, headers=headers
    )
    assert again.status_code == 201, again.text


def test_nonexistent_brand_delete_is_not_found(client, make_user):
    headers = make_user()
    org = new_org(client, headers)
    path = api(f"/organizations/{org}/brands/{uuid.uuid4()}")
    assert client.delete(path, headers=headers).status_code == 404
