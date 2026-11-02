"""
Central authorization policy for project/stage access.

This module is intentionally configuration-first. Authorization decisions should
use the constants/helpers here rather than scattering role names and access rules
through individual routers.

Important product rule:
    SUPER_ADMIN is a platform administrator, not an automatic project/stage
    member. A SUPER_ADMIN therefore does not receive project/stage access merely
    because they hold the SUPER_ADMIN role.

When the product's access model changes, update this policy first and then adjust
only the specific enforcement points that need different behaviour.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final

from core.rbac import (
    GENERAL_USER,
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    SUPER_ADMIN,
)


class AccessLevel(IntEnum):
    """Effective access to a project stage."""

    NONE = 0
    VIEW = 10
    EDIT = 20
    ADMIN = 30


# Stable string values used by API responses and the frontend.
ACCESS_LEVEL_NAMES: Final[dict[AccessLevel, str]] = {
    AccessLevel.NONE: "NONE",
    AccessLevel.VIEW: "VIEW",
    AccessLevel.EDIT: "EDIT",
    AccessLevel.ADMIN: "ADMIN",
}


# ---------------------------------------------------------------------------
# Stage access
# ---------------------------------------------------------------------------
#
# These roles only grant stage access when assigned at STAGE scope.
#
# Example:
#
#   PROJECT_EDITOR + STAGE + <Design stage ID>
#
# means:
#
#   Design = EDIT
#
STAGE_ROLE_ACCESS: Final[dict[str, AccessLevel]] = {
    PROJECT_VIEWER: AccessLevel.VIEW,
    PROJECT_EDITOR: AccessLevel.EDIT,
}


# ---------------------------------------------------------------------------
# Project-wide administrative access
# ---------------------------------------------------------------------------
#
# These roles inherit administrative access to every stage within their
# applicable scope.
#
# SUPER_ADMIN is deliberately NOT included.
#
# A SUPER_ADMIN is a platform administrator, not automatically a project
# member.
#
PROJECT_ADMIN_ROLES: Final[frozenset[str]] = frozenset(
    {
        ORG_ADMIN,
        PROJECT_ADMIN,
    }
)


# ---------------------------------------------------------------------------
# Who may manage stage access?
# ---------------------------------------------------------------------------
#
# Phase 1 requirement:
#
#   ORG_ADMIN -> can manage stage access
#
# Project Admin delegation can be enabled later by changing this set.
#
STAGE_ACCESS_MANAGERS: Final[frozenset[str]] = frozenset(
    {
        ORG_ADMIN,
    }
)


# ---------------------------------------------------------------------------
# Which scopes are valid for each role?
# ---------------------------------------------------------------------------
#
# This is intentionally centralized so role/scope rules don't get duplicated
# across individual routers.
#
ROLE_ALLOWED_SCOPES: Final[dict[str, frozenset[str]]] = {
    SUPER_ADMIN: frozenset({"GLOBAL"}),
    ORG_ADMIN: frozenset({"ORGANISATION"}),
    PROJECT_ADMIN: frozenset({"PROJECT"}),
    PROJECT_EDITOR: frozenset({"STAGE"}),
    PROJECT_VIEWER: frozenset({"STAGE"}),
    GENERAL_USER: frozenset({"GLOBAL"}),
}


def stage_access_for_role(role_name: str) -> AccessLevel:
    """
    Return the stage access granted by a role when that role is
    assigned at STAGE scope.

    Roles such as ORG_ADMIN and PROJECT_ADMIN are handled separately
    because their access comes from a broader scope.
    """
    return STAGE_ROLE_ACCESS.get(
        role_name,
        AccessLevel.NONE,
    )


def access_name(level: AccessLevel) -> str:
    """Return the stable string representation used by APIs/UI."""
    return ACCESS_LEVEL_NAMES[level]


def can_manage_stage_access(role_names: set[str]) -> bool:
    """Return whether any effective role can manage stage assignments."""
    return bool(role_names.intersection(STAGE_ACCESS_MANAGERS))