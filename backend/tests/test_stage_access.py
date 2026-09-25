"""
Tests for stage-level project authorization.

Coverage:
    - stage role -> access level mapping
    - SUPER_ADMIN does not automatically receive project/stage access
    - PROJECT_ADMIN receives ADMIN access to project stages
    - ORG_ADMIN receives ADMIN access to project stages
    - PROJECT_EDITOR receives EDIT access only on assigned stages
    - PROJECT_VIEWER receives VIEW access only on assigned stages
    - stage access is tied to ProjectStageInstance.id
    - mismatched project/stage combinations return NONE
    - unknown/non-stage roles do not grant stage access
    - stage access management policy
    - role scope policy
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from core.authorization_policy import (
    AccessLevel,
    ROLE_ALLOWED_SCOPES,
    STAGE_ACCESS_MANAGERS,
    can_manage_stage_access,
    stage_access_for_role,
)

from core.rbac import (
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    SUPER_ADMIN,
    get_stage_access_level,
)


# ============================================================================
# Policy: role -> stage access
# ============================================================================


def test_project_viewer_maps_to_view():
    assert (
        stage_access_for_role(PROJECT_VIEWER)
        == AccessLevel.VIEW
    )


def test_project_editor_maps_to_edit():
    assert (
        stage_access_for_role(PROJECT_EDITOR)
        == AccessLevel.EDIT
    )


# def test_project_admin_maps_to_admin():
#     assert (
#         stage_access_for_role(PROJECT_ADMIN)
#         == AccessLevel.ADMIN
#     )


# def test_org_admin_maps_to_admin():
#     assert (
#         stage_access_for_role(ORG_ADMIN)
#         == AccessLevel.ADMIN
#     )


def test_super_admin_does_not_map_to_stage_access():
    """
    SUPER_ADMIN is not automatic project/stage membership.
    """
    assert (
        stage_access_for_role(SUPER_ADMIN)
        == AccessLevel.NONE
    )


def test_unknown_role_has_no_stage_access():
    assert (
        stage_access_for_role("UNKNOWN_ROLE")
        == AccessLevel.NONE
    )


# ============================================================================
# Policy: stage access management
# ============================================================================


def test_only_org_admin_manages_stage_access():
    assert can_manage_stage_access(
        {ORG_ADMIN}
    ) is True


def test_project_admin_cannot_manage_stage_access():
    assert can_manage_stage_access(
        {PROJECT_ADMIN}
    ) is False


def test_super_admin_cannot_manage_stage_access():
    assert can_manage_stage_access(
        {SUPER_ADMIN}
    ) is False


def test_mixed_roles_with_org_admin_can_manage_stage_access():
    assert can_manage_stage_access(
        {
            PROJECT_VIEWER,
            ORG_ADMIN,
        }
    ) is True


# ============================================================================
# Policy: role scopes
# ============================================================================


def test_stage_roles_are_stage_scoped():
    assert ROLE_ALLOWED_SCOPES[
        PROJECT_EDITOR
    ] == {"STAGE"}

    assert ROLE_ALLOWED_SCOPES[
        PROJECT_VIEWER
    ] == {"STAGE"}


def test_project_admin_is_project_scoped():
    assert ROLE_ALLOWED_SCOPES[
        PROJECT_ADMIN
    ] == {"PROJECT"}


def test_org_admin_is_organisation_scoped():
    assert ROLE_ALLOWED_SCOPES[
        ORG_ADMIN
    ] == {"ORGANISATION"}


def test_super_admin_is_global_scoped():
    assert ROLE_ALLOWED_SCOPES[
        SUPER_ADMIN
    ] == {"GLOBAL"}


def test_stage_access_manager_policy_matches_central_config():
    assert STAGE_ACCESS_MANAGERS == {
        ORG_ADMIN
    }


# ============================================================================
# get_stage_access_level()
#
# These tests deliberately mock the database-dependent helpers.
# This lets us test the authorization logic independently of the DB fixture.
# ============================================================================


class _FakeRowResult:
    def __init__(self, *values):
        self.values = values

    def one_or_none(self):
        if not self.values:
            return None

        return self.values


class _FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    """
    Minimal AsyncSession stand-in.

    Each get_stage_access_level() call performs:

        1. ProjectStageInstance lookup
           -> project_id + stage

        2. Stage enablement lookup
           -> enabled

        3. Project.project_class lookup only for RECURRING

    The query sequence therefore resets logically for every
    get_stage_access_level() invocation.
    """

    def __init__(
        self,
        stage_project_id,
        *,
        stage=None,
        stage_enabled=True,
        project_class="STANDARD",
    ):
        self.stage_project_id = stage_project_id
        self.stage = stage
        self.stage_enabled = stage_enabled
        self.project_class = project_class

        self._stage_query = True

    async def execute(self, _query):
        # --------------------------------------------------------------
        # Stage lookup
        # --------------------------------------------------------------
        if self._stage_query:
            self._stage_query = False

            if self.stage_project_id is None:
                return _FakeRowResult()

            from models.project_stage_instances import ProjectStage

            stage = self.stage or ProjectStage.DESIGN

            return _FakeRowResult(
                self.stage_project_id,
                stage,
            )

        # --------------------------------------------------------------
        # Stage enablement lookup
        # --------------------------------------------------------------
        self._stage_query = True

        return _FakeScalarResult(
            self.stage_enabled
        )

@pytest.mark.asyncio
async def test_project_viewer_gets_view_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return set()

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return {
            PROJECT_VIEWER
        }

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.VIEW


@pytest.mark.asyncio
async def test_project_editor_gets_edit_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return set()

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return {
            PROJECT_EDITOR
        }

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.EDIT


@pytest.mark.asyncio
async def test_project_admin_gets_admin_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return {
            PROJECT_ADMIN
        }

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return set()

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.ADMIN


@pytest.mark.asyncio
async def test_org_admin_gets_admin_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return {
            ORG_ADMIN
        }

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return set()

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.ADMIN


@pytest.mark.asyncio
async def test_super_admin_does_not_get_stage_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return {
            SUPER_ADMIN
        }

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return set()

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.NONE


@pytest.mark.asyncio
async def test_user_without_stage_role_gets_no_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return set()

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return set()

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.NONE


@pytest.mark.asyncio
async def test_stage_role_only_applies_to_assigned_stage(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()

    assigned_stage_id = uuid4()
    different_stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return set()

    async def mock_stage_roles(
        _db,
        _user_id,
        stage_instance_id,
    ):
        if stage_instance_id == assigned_stage_id:
            return {
                PROJECT_EDITOR
            }

        return set()

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    assigned_access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=assigned_stage_id,
    )

    different_access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=different_stage_id,
    )

    assert assigned_access == AccessLevel.EDIT
    assert different_access == AccessLevel.NONE


@pytest.mark.asyncio
async def test_stage_from_different_project_returns_no_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    different_project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return {
            PROJECT_ADMIN
        }

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return {
            PROJECT_EDITOR
        }

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    # The stage actually belongs to a different project.
    db = _FakeDB(
        stage_project_id=different_project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.NONE


@pytest.mark.asyncio
async def test_nonexistent_stage_returns_no_access(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return {
            PROJECT_ADMIN
        }

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return {
            PROJECT_EDITOR
        }

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    # None means the ProjectStageInstance does not exist.
    db = _FakeDB(
        stage_project_id=None
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.NONE


@pytest.mark.asyncio
async def test_editor_and_viewer_on_same_stage_resolve_to_edit(
    monkeypatch,
):
    import core.rbac as rbac

    user_id = uuid4()
    project_id = uuid4()
    stage_id = uuid4()

    async def mock_effective_roles(
        _db,
        _user_id,
        project_id=None,
    ):
        return set()

    async def mock_stage_roles(
        _db,
        _user_id,
        _stage_id,
    ):
        return {
            PROJECT_VIEWER,
            PROJECT_EDITOR,
        }

    monkeypatch.setattr(
        rbac,
        "get_effective_role_names",
        mock_effective_roles,
    )

    monkeypatch.setattr(
        rbac,
        "get_stage_role_names",
        mock_stage_roles,
    )

    db = _FakeDB(
        stage_project_id=project_id
    )

    access = await get_stage_access_level(
        db,
        user_id=user_id,
        project_id=project_id,
        stage_instance_id=stage_id,
    )

    assert access == AccessLevel.EDIT