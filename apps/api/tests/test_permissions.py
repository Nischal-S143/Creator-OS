import pytest

from app.models.identity import ROLES
from app.security.permissions import ROLE_PERMISSIONS, Permission, has_permission

P = Permission
EXPECTED = {
    "owner": set(P),
    "admin": set(P),
    "manager": {
        P.ORG_VIEW,
        P.MEMBERS_VIEW,
        P.BRAND_VIEW,
        P.BRAND_EDIT,
        P.PROFILE_APPROVE,
        P.CAMPAIGN_VIEW,
        P.CAMPAIGN_EDIT,
        P.CONTENT_APPROVE,
    },
    "editor": {P.ORG_VIEW, P.BRAND_VIEW, P.BRAND_EDIT, P.CAMPAIGN_VIEW, P.CAMPAIGN_EDIT},
    "analyst": {P.ORG_VIEW, P.BRAND_VIEW, P.CAMPAIGN_VIEW},
    "client_approver": {P.ORG_VIEW},
}


def test_every_role_is_defined():
    assert set(ROLE_PERMISSIONS) == set(ROLES) == set(EXPECTED)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("permission", list(P))
def test_permission_matrix(role, permission):
    assert has_permission(role, permission) is (permission in EXPECTED[role])


def test_unknown_role_has_no_permissions():
    assert not any(has_permission("superuser", p) for p in P)
