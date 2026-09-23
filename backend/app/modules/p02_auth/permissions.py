"""P02 — roles and permissions (MID §11 P02: read / recommend / execute; execute off by default).

Roles are fixed in code so they are versioned and reviewed like any other change.
`execute` is deliberately NOT part of any role: it is a separate per-user switch
(`users.execute_enabled`, default False) that can only be set from the CLI, never via the API.
"""
from enum import StrEnum


class Permission(StrEnum):
    READ = "read"            # view dashboards, data, reports
    RECOMMEND = "recommend"  # run audits/AI, create drafts and recommendations
    APPROVE = "approve"      # approve/reject recommendations (P16)
    ADMIN = "admin"          # manage users
    EXECUTE = "execute"      # push approved changes to Google Ads (P17) — per-user switch only


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": frozenset({Permission.READ}),
    "analyst": frozenset({Permission.READ, Permission.RECOMMEND}),
    "approver": frozenset({Permission.READ, Permission.RECOMMEND, Permission.APPROVE}),
    "admin": frozenset({Permission.READ, Permission.RECOMMEND, Permission.APPROVE, Permission.ADMIN}),
}
ROLES = tuple(ROLE_PERMISSIONS)


def permissions_for(role: str, execute_enabled: bool) -> frozenset[Permission]:
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return perms | {Permission.EXECUTE} if execute_enabled else perms
