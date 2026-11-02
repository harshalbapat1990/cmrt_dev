from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
# from core.database import get_session
# from core.auth import get_current_principal
# from core.models import Principal
from core.rbac import require_stage_access
from core.authorization_policy import AccessLevel

from crud.project_stage_config import (
    list_project_stage_configs,
    get_project_stage_config,
)
from crud.project_stage_instances import (
    get_project_stage_instance_by_project_and_stage,
)

from schemas.project_stage_config import ProjectStageConfigOut


router = APIRouter(
    prefix="/api/project-stage-configs",
    tags=["Project Stage Config"],
)


@router.get(
    "",
    response_model=list[ProjectStageConfigOut],
)
async def get_project_stage_configs(
    project_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    """
    Return stage configurations visible to the current user.

    Authorization is stage-based:

        PROJECT_ADMIN
            -> all stages in the project

        PROJECT_EDITOR
            -> only assigned stages

        PROJECT_VIEWER
            -> only assigned stages

        ORG_ADMIN
            -> all stages in projects belonging to the organisation

        SUPER_ADMIN
            -> no automatic project access

    Disabled stages are not returned to ordinary stage users because
    disabled stages no longer provide stage access.
    """

    configs = await list_project_stage_configs(
        db=db,
        skip=skip,
        limit=limit,
        project_id=project_id,
    )

    visible_configs = []

    for config in configs:
        # A configuration record corresponds to a stage instance
        # through project_id + stage.
        stage_instance = await get_project_stage_instance_by_project_and_stage(
            db=db,
            project_id=config.project_id,
            stage=config.stage,
        )

        if stage_instance is None:
            continue

        try:
            await require_stage_access(
                db=db,
                principal=principal,
                project_id=config.project_id,
                stage_instance_id=stage_instance.id,
                minimum_access=AccessLevel.VIEW,
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                continue
            raise

        visible_configs.append(config)

    return visible_configs


@router.get(
    "/{id}",
    response_model=ProjectStageConfigOut,
)
async def get_project_stage_config_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    """
    Return one stage configuration if the current user has VIEW
    access to the corresponding project stage.
    """

    config = await get_project_stage_config(
        db=db,
        config_id=id,
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project stage configuration not found",
        )

    stage_instance = await get_project_stage_instance_by_project_and_stage(
        db=db,
        project_id=config.project_id,
        stage=config.stage,
    )

    if stage_instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project stage instance not found",
        )

    await require_stage_access(
        db=db,
        principal=principal,
        project_id=config.project_id,
        stage_instance_id=stage_instance.id,
        minimum_access=AccessLevel.VIEW,
    )

    return config