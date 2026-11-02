"""
core/access_context.py
======================
Centralises dataset-visibility decisions so they are defined in one place
regardless of how many routes or services query them.

Currently returns a typed enum value only – NO dataset queries are performed
here yet. When org/project-specific dataset selection is implemented, this
module will be the single place that decides which "dataset tier" is visible.

Dataset visibility rules (to implement later):
  SUPER_ADMIN   → DEFAULT   (global / platform default datasets)
  ORG_ADMIN     → ORG       (org-scoped dataset overrides of the owning org)
  PROJECT_*     → PROJECT   (project-scoped dataset overrides)
  No match      → DEFAULT   (read-only public view)
"""

from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import (
    SUPER_ADMIN,
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    get_effective_role_names,
)
from core.security import Principal


class DatasetVisibility(str, enum.Enum):
    DEFAULT = "DEFAULT"   # Platform global datasets (SA or unauthenticated public)
    ORG = "ORG"           # Org-level dataset overrides
    PROJECT = "PROJECT"   # Project-level dataset overrides


async def get_dataset_visibility_context(
    principal: Principal,
    db: AsyncSession,
    project_id: Optional[uuid.UUID] = None,
) -> DatasetVisibility:
    """
    Determine which dataset tier the principal can see for a given project.

    Called by dataset-related endpoints (once implemented) to filter query
    results to the correct tier without duplicating logic in every route.
    """
    effective_roles = await get_effective_role_names(
        db, principal.user_id, project_id=project_id
    )

    if SUPER_ADMIN in effective_roles:
        return DatasetVisibility.DEFAULT

    if ORG_ADMIN in effective_roles:
        return DatasetVisibility.ORG

    if effective_roles.intersection({PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER}):
        return DatasetVisibility.PROJECT

    # Default: show only platform-level data
    return DatasetVisibility.DEFAULT
