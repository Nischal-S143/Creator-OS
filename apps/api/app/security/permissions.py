from enum import StrEnum


class Permission(StrEnum):
    ORG_VIEW = "org.view"
    ORG_MANAGE = "org.manage"
    MEMBERS_VIEW = "members.view"
    MEMBERS_MANAGE = "members.manage"
    BRAND_VIEW = "brand.view"
    BRAND_CREATE = "brand.create"
    BRAND_EDIT = "brand.edit"
    PROFILE_APPROVE = "profile.approve"
    CAMPAIGN_VIEW = "campaign.view"
    CAMPAIGN_EDIT = "campaign.edit"
    CONTENT_APPROVE = "content.approve"


_P = Permission

# Client approvers get brand access only once per-brand assignment exists, so they start with none.
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),
    "admin": frozenset(Permission),
    "manager": frozenset(
        {
            _P.ORG_VIEW,
            _P.MEMBERS_VIEW,
            _P.BRAND_VIEW,
            _P.BRAND_EDIT,
            _P.PROFILE_APPROVE,
            _P.CAMPAIGN_VIEW,
            _P.CAMPAIGN_EDIT,
            _P.CONTENT_APPROVE,
        }
    ),
    "editor": frozenset({_P.ORG_VIEW, _P.BRAND_VIEW, _P.BRAND_EDIT, _P.CAMPAIGN_VIEW, _P.CAMPAIGN_EDIT}),
    "analyst": frozenset({_P.ORG_VIEW, _P.BRAND_VIEW, _P.CAMPAIGN_VIEW}),
    "client_approver": frozenset({_P.ORG_VIEW}),
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
