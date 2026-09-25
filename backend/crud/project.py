from uuid import UUID
from typing import List, Optional
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.project import Project, ProjectClass
from models.project_stage_config import ProjectStageConfig, ProjectStage, ReportFrequency
from models.project_organizations import ProjectOrganization, OrgRole
from models.postcode import ProjectPostcode, PostcodeReference, AreaClass
from models.project_type import ProjectType
from models.benchmark_mastertypes import BenchmarkMastertype
from models.benchmark_typecasts import BenchmarkTypecast
from models.organizations import Organization, Organization_Type
from models.project_stage_instances import (
    ProjectStageInstance as StageInstanceModel,
    ProjectStage as StageInstanceProjectStage,
)
from models.project_reporting_boundary import ProjectReportingBoundary
from models.activity_data import ActivityData
from models.user_roles import UserRole
from models.roles import Role as RoleModel
from models.users import User
from sqlalchemy import and_, or_
from schemas.project import ProjectCreate, ProjectRoleEnum, ProjectUpdate
from crud.project_access import (
    assign_user_to_project_stages,
    deactivate_all_project_stage_access,
)

_ROLE_TO_ORG_TYPE = {
    OrgRole.DELIVERY: Organization_Type.CONTRACTORS,
    OrgRole.DESIGNER: Organization_Type.DESIGNERS,
}


async def _resolve_org_id(db: AsyncSession, link) -> UUID:
    """Return an org UUID for an OrgLinkIn — uses existing ID or finds/creates by uppercased name."""
    if link.organization_id:
        return link.organization_id
    name = (link.org_name or "").strip().upper()
    if not name:
        raise HTTPException(status_code=400, detail="org_name must not be empty when organization_id is omitted")
    role = OrgRole(link.role)
    org_type = _ROLE_TO_ORG_TYPE.get(role, Organization_Type.CONTRACTORS)
    existing = (await db.execute(
        select(Organization).where(
            Organization.name == name,
            Organization.organization_type == org_type,
        )
    )).scalars().first()
    if existing:
        return existing.id
    new_org = Organization(name=name, organization_type=org_type, is_proponent=False, is_active=True)
    db.add(new_org)
    await db.flush()
    return new_org.id



                
async def _enrich(db: AsyncSession, projects: list) -> None:
    if not projects:
        return

    type_id_set: set = set()
    typecast_id_set: set = set()
    org_id_set: set = set()
    for p in projects:
        # Try to parse project_type as UUID (for backward compatibility)
        try:
            type_id_set.add(UUID(str(p.project_type)))
        except (ValueError, AttributeError):
            pass
        # Add project_type_id if it exists
        if p.project_type_id:
            type_id_set.add(p.project_type_id)
        # Add project_typecast_id if it exists
        if p.project_typecast_id:
            typecast_id_set.add(p.project_typecast_id)
        # Collect org IDs
        if p.proponent_org_id:
            org_id_set.add(p.proponent_org_id)
        for link in (p.org_links or []):
            if link.organization_id:
                org_id_set.add(link.organization_id)

    # Fetch type names from ProjectType table (legacy)
    type_map: dict = {}
    if type_id_set:
        rows = (await db.execute(
            select(ProjectType.id, ProjectType.name).where(ProjectType.id.in_(list(type_id_set)))
        )).all()
        type_map = {str(r.id): r.name for r in rows}

    # Fetch BenchmarkMastertype objects
    mastertype_map: dict = {}
    mastertype_objs: dict = {}
    if type_id_set:
        rows = (await db.execute(
            select(BenchmarkMastertype).where(BenchmarkMastertype.id.in_(list(type_id_set)))
        )).scalars().all()
        for row in rows:
            mastertype_map[str(row.id)] = row.name
            mastertype_objs[str(row.id)] = row

    # Fetch BenchmarkTypecast objects
    typecast_map: dict = {}
    typecast_objs: dict = {}
    if typecast_id_set:
        rows = (await db.execute(
            select(BenchmarkTypecast).where(BenchmarkTypecast.id.in_(list(typecast_id_set)))
        )).scalars().all()
        for row in rows:
            typecast_map[str(row.id)] = row.name
            typecast_objs[str(row.id)] = row

    # Fetch organizations
    org_map: dict = {}
    if org_id_set:
        rows = (await db.execute(
            select(Organization.id, Organization.name).where(Organization.id.in_(list(org_id_set)))
        )).all()
        org_map = {str(r.id): r.name for r in rows}

    # Fetch member accesses.
    #
    # Project admins remain PROJECT-scoped.
    # Editors/viewers are now STAGE-scoped.
    #
    # For the existing ProjectOut.member_accesses response shape, aggregate
    # stage assignments back to the project level:
    #
    #   any EDIT stage -> PROJECT_EDITOR
    #   otherwise any VIEW stage -> PROJECT_VIEWER
    #
    # The detailed stage assignments are provided by the dedicated
    # project-access API.
    member_access_map: dict = {}

    if projects:
        project_ids = [
            p.id
            for p in projects
        ]

        # --------------------------------------------------------------
        # Project administrators
        # --------------------------------------------------------------

        project_admin_rows = await db.execute(
            select(
                UserRole.user_id,
                UserRole.scope_id,
                RoleModel.name,
                User.email,
            )
            .join(
                RoleModel,
                RoleModel.id == UserRole.role_id,
            )
            .outerjoin(
                User,
                User.id == UserRole.user_id,
            )
            .where(
                UserRole.scope_id.in_(project_ids),
                UserRole.scope_type == "PROJECT",
                UserRole.is_active == True,
                RoleModel.name == "PROJECT_ADMIN",
            )
        )

        # --------------------------------------------------------------
        # Stage-level editor/viewer assignments
        # --------------------------------------------------------------

        stage_rows = await db.execute(
            select(
                UserRole.user_id,
                StageInstanceModel.project_id,
                RoleModel.name,
                User.email,
            )
            .join(
                StageInstanceModel,
                StageInstanceModel.id
                == UserRole.scope_id,
            )
            .join(
                RoleModel,
                RoleModel.id == UserRole.role_id,
            )
            .outerjoin(
                User,
                User.id == UserRole.user_id,
            )
            .where(
                StageInstanceModel.project_id.in_(
                    project_ids
                ),
                UserRole.scope_type == "STAGE",
                UserRole.is_active == True,
                RoleModel.name.in_(
                    [
                        "PROJECT_EDITOR",
                        "PROJECT_VIEWER",
                    ]
                ),
            )
        )

        # user/project -> effective role
        aggregate: dict[
            tuple[UUID, UUID],
            dict,
        ] = {}

        for row in project_admin_rows.all():

            key = (
                row.scope_id,
                row.user_id,
            )

            aggregate[key] = {
                "user_id": str(row.user_id),
                "role": "PROJECT_ADMIN",
                "user_email": row.email or "",
            }

        for row in stage_rows.all():

            key = (
                row.project_id,
                row.user_id,
            )

            existing = aggregate.get(key)

            # Editor takes precedence over viewer when a user has
            # different access levels on different stages.
            if (
                existing is not None
                and existing["role"]
                == "PROJECT_ADMIN"
            ):
                continue

            if (
                existing is None
                or (
                    existing["role"]
                    == "PROJECT_VIEWER"
                    and row.name
                    == "PROJECT_EDITOR"
                )
            ):
                aggregate[key] = {
                    "user_id": str(row.user_id),
                    "role": row.name,
                    "user_email": row.email or "",
                }

        for (project_id, _user_id), member in aggregate.items():

            project_key = str(project_id)

            member_access_map.setdefault(
                project_key,
                [],
            )

            member_access_map[
                project_key
            ].append(member)

    _project_ids = [p.id for p in projects]
    _has_entries_rows = await db.execute(
        select(ActivityData.project_id)
        .where(ActivityData.project_id.in_(_project_ids))
        .distinct()
    )
    _has_entries_set = {str(r) for r in _has_entries_rows.scalars().all()}

    # Enrich projects with resolved data
    for p in projects:
        # Legacy: Try to parse project_type as UUID
        try:
            p.project_type_id = UUID(str(p.project_type))
        except (ValueError, AttributeError):
            pass
        
        # Set type names from both sources
        if p.project_type_id:
            p.project_type_name = mastertype_map.get(str(p.project_type_id)) or type_map.get(str(p.project_type_id))
            p.benchmark_mastertype = mastertype_objs.get(str(p.project_type_id))
        
        # Set typecast names and objects
        if p.project_typecast_id:
            p.project_typecast_name = typecast_map.get(str(p.project_typecast_id))
            p.benchmark_typecast = typecast_objs.get(str(p.project_typecast_id))
        
        # Set organization names
        p.proponent_org_name = org_map.get(str(p.proponent_org_id)) if p.proponent_org_id else None
        for link in (p.org_links or []):
            link.organization_name = org_map.get(str(link.organization_id)) if link.organization_id else None
        
        # Set member accesses
        p.member_accesses = member_access_map.get(str(p.id), [])

        p.has_entries = str(p.id) in _has_entries_set


async def _validate_small_large(payload: ProjectCreate | ProjectUpdate):
    missing = []
    if getattr(payload, "commencement_of_operations", None) is None:
        missing.append("commencement_of_operations")
    if getattr(payload, "operational_life_years", None) is None:
        missing.append("operational_life_years")
    if getattr(payload, "project_capex_million", None) is None:
        missing.append("project_capex_million")
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields for Small/Large: {', '.join(missing)}")


async def _validate_recurring(payload: ProjectCreate | ProjectUpdate):
    if not getattr(payload, "first_submission_month", None):
        raise HTTPException(status_code=400, detail="first_submission_month is required for maintenance/recurring projects")
    for f in ("construction_start_date", "construction_end_date", "commencement_of_operations", "operational_life_years"):
        if getattr(payload, f, None) is not None:
            raise HTTPException(status_code=400, detail="Construction/operation fields are not allowed for recurring/maintenance projects")


async def _validate_postcodes(
    db: AsyncSession,
    postcodes: List[str],
    proponent_org_id: Optional[UUID] = None,
) -> List[tuple[str, AreaClass, object]]:
    rows = (await db.execute(
        select(PostcodeReference).where(PostcodeReference.postcode.in_(postcodes))
    )).scalars().all()
    mapping = {r.postcode: (r.area_class, r.jurisdiction_id) for r in rows}
    missing = [pc for pc in postcodes if pc not in mapping]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown postcode(s): {', '.join(missing)}. Upload reference data first.")

    # Validate each postcode belongs to the proponent org's jurisdiction/region
    # if proponent_org_id is not None:
    #     org_result = await db.execute(
    #         select(Organization).where(Organization.id == proponent_org_id)
    #     )
    #     org = org_result.scalars().first()
    #     if org is not None:
    #         # Determine the expected jurisdiction id for postcode matching.
    #         # AU orgs: region_id points to the state record ("NSW", "VIC", etc.)
    #         #           which is what postcode_reference.jurisdiction_id uses.
    #         # NZ orgs: region_id is typically null; fall back to jurisdiction_id.
    #         expected_jid = org.region_id or org.jurisdiction_id
    #         expected_name = (
    #             (org.region.name if org.region else None)
    #             or (org.jurisdiction.name if org.jurisdiction else None)
    #             or "the organisation's region"
    #         )
    #         if expected_jid is not None:
    #             invalid = [
    #                 pc for pc in postcodes
    #                 if mapping[pc][1] != expected_jid
    #             ]
    #             if invalid:
    #                 raise HTTPException(
    #                     status_code=400,
    #                     detail=(
    #                         f"Postcode(s) {', '.join(invalid)} do not belong to "
    #                         f"{expected_name}. Only postcodes within that region are permitted."
    #                     ),
    #                 )

    return [(pc, mapping[pc][0], mapping[pc][1]) for pc in postcodes]


async def create_project(db: AsyncSession, payload: ProjectCreate) -> Project:
    exists = (await db.execute(select(Project).where(Project.project_name == payload.project_name))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Project name already exists")

    if payload.project_class in ("SMALL", "LARGE"):
        await _validate_small_large(payload)
    elif payload.project_class == "RECURRING":
        await _validate_recurring(payload)

    sc_map = {sc.stage: sc for sc in payload.stage_configs}
    if (sc := sc_map.get("CONSTRUCTION")) and sc.enabled and not sc.frequency:
        raise HTTPException(status_code=400, detail="Construction stage requires frequency when enabled")

    if (sc := sc_map.get("DESIGN")) and sc.enabled and not payload.project_type_id:
        raise HTTPException(status_code=400, detail="Project Type is required when Design stage is enabled.")

    pc_pairs = await _validate_postcodes(db, [p.postcode for p in payload.postcodes], proponent_org_id=payload.proponent_org_id)


    obj = Project(
        project_name=payload.project_name,
        project_type_id=payload.project_type_id,
        project_typecast_id=payload.project_typecast_id or None,
        description=payload.description,
        is_active=payload.is_active,

        project_class=ProjectClass(payload.project_class),
        simple_carbon_assessment=payload.simple_carbon_assessment or False,
        contract_number=payload.contract_number or "",
        design_contract_number=payload.design_contract_number,
        construction_contract_number=payload.construction_contract_number,
        program_name=payload.program_name,
        location_text=payload.location_text,

        construction_start_date=payload.construction_start_date,
        construction_end_date=payload.construction_end_date,
        commencement_of_operations=payload.commencement_of_operations,
        operational_life_years=payload.operational_life_years,
        project_capex_million=payload.project_capex_million,
        project_opex=payload.project_opex,

        declared_unit_value=payload.declared_unit_value,
        declared_unit_type=payload.declared_unit_type,

        first_submission_month=payload.first_submission_month,
        maintenance_region=payload.maintenance_region,

        proponent_org_id=payload.proponent_org_id,
        created_by_user_id=payload.created_by_user_id,
        last_updated_by_user_id=payload.created_by_user_id,
    )
    db.add(obj)
    await db.flush()

    for sc in payload.stage_configs:
        db.add(ProjectStageConfig(
            project_id=obj.id,
            stage=ProjectStage(sc.stage),
            enabled=sc.enabled,
            num_reports_required=sc.num_reports_required,
            frequency=ReportFrequency(sc.frequency) if sc.frequency else None,
            min_requirements=sc.min_requirements
        ))

    if payload.project_class != "RECURRING":
        for sc in payload.stage_configs:
            if sc.enabled:
                db.add(StageInstanceModel(
                    project_id=obj.id,
                    stage=sc.stage.value,
                    approval_status="draft",
                    sequence={"BUSINESS_CASE": 1, "DESIGN": 2, "CONSTRUCTION": 3}.get(sc.stage.value, 99),
                    num_reports_required=sc.num_reports_required,
                    frequency=sc.frequency.value if sc.frequency else None,
                ))

    if payload.project_class == "RECURRING":
        db.add(StageInstanceModel(
            project_id=obj.id,
            stage="RECURRING",
            approval_status="draft",
            sequence=0,
        ))

    for link in payload.org_links:
        org_id = await _resolve_org_id(db, link)
        db.add(ProjectOrganization(
            project_id=obj.id,
            organization_id=org_id,
            role=OrgRole(link.role),
        ))


    for pc, area, jid in pc_pairs:
        db.add(ProjectPostcode(project_id=obj.id, postcode=pc, area_class=area, jurisdiction_id=jid))

    for idx, rb in enumerate(payload.reporting_boundaries or []):
        db.add(ProjectReportingBoundary(
            project_id=obj.id,
            stage_or_activity=rb.stage_or_activity,
            category=rb.category,
            sub_category=rb.sub_category,
            source=rb.source,
            sort_order=idx,
        ))

    await db.flush()

    if payload.member_accesses:
        from models.user_roles import UserRole
        from models.roles import Role as RoleModel

        role_names = {
            ma.role
            for ma in payload.member_accesses
        }

        roles_result = await db.execute(
            select(RoleModel).where(
                RoleModel.name.in_(role_names),
                RoleModel.is_active == True,
            )
        )

        role_map = {
            role.name: role.id
            for role in roles_result.scalars().all()
        }

        for member_access in payload.member_accesses:

            # --------------------------------------------------------------
            # PROJECT_ADMIN remains project-scoped.
            # --------------------------------------------------------------

            if member_access.role == ProjectRoleEnum.PROJECT_ADMIN:
                role_id = role_map.get(
                    ProjectRoleEnum.PROJECT_ADMIN
                )
                if role_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Role PROJECT_ADMIN not found",
                    )
                # Keep PROJECT_ADMIN project-scoped.
                db.add(
                    UserRole(
                        user_id=member_access.user_id,
                        role_id=role_id,
                        scope_type="PROJECT",
                        scope_id=obj.id,
                        is_active=True,
                    )
                )

            elif member_access.role in {
                ProjectRoleEnum.PROJECT_EDITOR,
                ProjectRoleEnum.PROJECT_VIEWER,
            }:
                await assign_user_to_project_stages(
                    db=db,
                    user_id=member_access.user_id,
                    project_id=obj.id,
                    role_name=member_access.role.value,
                )


    await db.flush()
    await db.refresh(obj)
    return obj


async def get_project(db: AsyncSession, project_id: UUID) -> Project | None:
    query = (
        select(Project)
        .where(Project.id == project_id)
        .options(*_PROJECT_EAGER)
    )
    result = await db.execute(query)
    project = result.scalars().first()
    if project:
        await _enrich(db, [project])
    return project


async def list_projects(db: AsyncSession, skip: int = 0, limit: int = 50, is_active: Optional[bool] = None) -> list[Project]:
    query = select(Project)
    if is_active is not None:
        query = query.where(Project.is_active == is_active)
    query = (
        query.options(*_PROJECT_EAGER)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    projects = result.scalars().all()
    await _enrich(db, list(projects))
    return projects


async def _sync_project_stage_instances(
    db: AsyncSession,
    *,
    project: Project,
    stage_configs,
) -> None:
    """
    Synchronize persistent ProjectStageInstance records with the
    supplied ProjectStageConfig records.

    Stage instances are historical business entities and must not
    be deleted/recreated when configuration changes.

    Rules:
    - Existing enabled stage -> preserve instance ID.
    - Newly enabled stage -> create instance.
    - Disabled stage -> retain instance.
    - Disabled stage -> deactivate ordinary stage access.
    - Re-enabled stage -> reuse existing instance.
    - Configuration changes -> update existing instance.
    - RECURRING is handled separately by update_project().
    """

    def _enum_value(value):
        return (
            value.value
            if hasattr(value, "value")
            else str(value)
        )

    stage_config_map = {
        _enum_value(sc.stage): sc
        for sc in stage_configs
    }

    result = await db.execute(
        select(StageInstanceModel).where(
            StageInstanceModel.project_id == project.id
        )
    )

    existing_instances = {
        _enum_value(instance.stage): instance
        for instance in result.scalars().all()
    }

    configurable_stages = (
        "BUSINESS_CASE",
        "DESIGN",
        "CONSTRUCTION",
    )

    stage_sequences = {
        "BUSINESS_CASE": 1,
        "DESIGN": 2,
        "CONSTRUCTION": 3,
    }

    # Resolve ordinary stage roles once.
    role_result = await db.execute(
        select(RoleModel.id).where(
            RoleModel.name.in_(
                [
                    "PROJECT_EDITOR",
                    "PROJECT_VIEWER",
                ]
            )
        )
    )

    stage_role_ids = list(
        role_result.scalars().all()
    )

    for stage_name in configurable_stages:

        config = stage_config_map.get(stage_name)

        enabled = bool(
            config is not None
            and config.enabled
        )

        existing_instance = existing_instances.get(
            stage_name
        )

        if enabled:

            if existing_instance is None:

                existing_instance = StageInstanceModel(
                    project_id=project.id,
                    stage=StageInstanceProjectStage(
                        stage_name
                    ),
                    sequence=stage_sequences[
                        stage_name
                    ],
                    num_reports_required=(
                        config.num_reports_required
                    ),
                    frequency=(
                        config.frequency.value
                        if hasattr(
                            config.frequency,
                            "value",
                        )
                        else config.frequency
                    ),
                    approval_status="draft",
                )

                db.add(existing_instance)

            else:

                # IMPORTANT:
                # Do not replace the instance.
                # Preserve its ID and historical fields.
                existing_instance.sequence = (
                    stage_sequences[stage_name]
                )

                existing_instance.num_reports_required = (
                    config.num_reports_required
                )

                existing_instance.frequency = (
                    config.frequency.value
                    if hasattr(
                        config.frequency,
                        "value",
                    )
                    else config.frequency
                )

                db.add(existing_instance)

        else:

            # Disabled stages are retained for history/audit.
            # Only their ordinary stage access is removed.
            if (
                existing_instance is not None
                and stage_role_ids
            ):

                access_result = await db.execute(
                    select(UserRole).where(
                        UserRole.scope_type == "STAGE",
                        UserRole.scope_id
                        == existing_instance.id,
                        UserRole.role_id.in_(
                            stage_role_ids
                        ),
                        UserRole.is_active == True,
                    )
                )

                for user_role in (
                    access_result.scalars().all()
                ):
                    user_role.is_active = False
                    db.add(user_role)

    await db.flush()


async def update_project(db: AsyncSession, obj: Project, payload: ProjectUpdate) -> Project:
    data = payload.dict(exclude_unset=True)
    nested = {"stage_configs", "org_links", "postcodes", "member_accesses", "reporting_boundaries"}
    fk_fields = {"project_type_id", "project_typecast_id"}
    for k in list(data.keys()):
        if k in nested or k in fk_fields:
            data.pop(k)

    for k, v in data.items():
        setattr(obj, k, v)
    
    # Handle FK fields separately
    if payload.project_type_id is not None:
        obj.project_type_id = payload.project_type_id
    if payload.project_typecast_id is not None:
        obj.project_typecast_id = payload.project_typecast_id
    
    obj.updated_on = datetime.utcnow()

    if "project_class" in payload.dict(exclude_unset=True):
        if payload.project_class in ("SMALL", "LARGE"):
            await _validate_small_large(payload)
        elif payload.project_class == "RECURRING":
            await _validate_recurring(payload)
    
    if payload.stage_configs is not None:

        def _stage_value(value):
            return (
                value.value
                if hasattr(value, "value")
                else str(value)
            )

        sc_map = {
            _stage_value(sc.stage): sc
            for sc in payload.stage_configs
        }

        if (
            (sc := sc_map.get("CONSTRUCTION"))
            and sc.enabled
            and not sc.frequency
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Construction stage requires "
                    "frequency when enabled"
                ),
            )

        if (
            (sc := sc_map.get("DESIGN"))
            and sc.enabled
        ):
            project_type_id = (
                payload.project_type_id
                if payload.project_type_id is not None
                else obj.project_type_id
            )

            if not project_type_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Project Type is required "
                        "when Design stage is enabled."
                    ),
                )

        # --------------------------------------------------------------
        # Update ProjectStageConfig in place.
        #
        # Do NOT delete/recreate existing configuration records.
        # --------------------------------------------------------------

        existing_configs = {
            _stage_value(existing.stage): existing
            for existing in list(obj.stage_configs)
        }

        for stage_name, sc in sc_map.items():

            existing = existing_configs.get(
                stage_name
            )

            if existing is None:

                db.add(
                    ProjectStageConfig(
                        project_id=obj.id,
                        stage=ProjectStage(stage_name),
                        enabled=sc.enabled,
                        num_reports_required=(
                            sc.num_reports_required
                        ),
                        frequency=(
                            ReportFrequency(sc.frequency)
                            if sc.frequency
                            else None
                        ),
                        min_requirements=(
                            sc.min_requirements
                        ),
                    )
                )

            else:

                existing.enabled = sc.enabled

                existing.num_reports_required = (
                    sc.num_reports_required
                )

                existing.frequency = (
                    ReportFrequency(sc.frequency)
                    if sc.frequency
                    else None
                )

                existing.min_requirements = (
                    sc.min_requirements
                )

                existing.updated_on = datetime.utcnow()

                db.add(existing)

        # Keep the existing behaviour for configuration entries
        # omitted from the incoming payload.
        incoming_stages = set(sc_map)

        for stage_name, existing in existing_configs.items():

            if stage_name not in incoming_stages:
                await db.delete(existing)

        await db.flush()

        # --------------------------------------------------------------
        # Synchronize persistent stage instances.
        # --------------------------------------------------------------

        await _sync_project_stage_instances(
            db,
            project=obj,
            stage_configs=payload.stage_configs,
        )
        
    if payload.org_links is not None:
        for existing in list(obj.org_links):
            await db.delete(existing)
        for link in payload.org_links:
            org_id = await _resolve_org_id(db, link)
            db.add(ProjectOrganization(
                project_id=obj.id,
                organization_id=org_id,
                role=OrgRole(link.role)
            ))

    if payload.postcodes is not None:
        pc_pairs = await _validate_postcodes(
            db,
            [p.postcode for p in payload.postcodes],
            proponent_org_id=obj.proponent_org_id,
        )
        for existing in list(obj.postcodes):
            await db.delete(existing)
        for pc, area, jid in pc_pairs:
            db.add(ProjectPostcode(project_id=obj.id, postcode=pc, area_class=area, jurisdiction_id=jid))

    if payload.reporting_boundaries is not None:
        for existing in list(obj.reporting_boundaries):
            await db.delete(existing)
        for idx, rb in enumerate(payload.reporting_boundaries):
            db.add(ProjectReportingBoundary(
                project_id=obj.id,
                stage_or_activity=rb.stage_or_activity,
                category=rb.category,
                sub_category=rb.sub_category,
                source=rb.source,
                sort_order=idx,
            ))

    if payload.member_accesses is not None:
        from models.user_roles import UserRole
        from models.roles import Role as RoleModel

        # Make sure any stage configuration changes have been flushed
        # before resolving the project's stage instances.
        await db.flush()

        # --------------------------------------------------------------
        # 1. Remove existing ordinary stage access for this project.
        #
        # PROJECT_ADMIN is deliberately NOT touched here.
        # --------------------------------------------------------------

        await deactivate_all_project_stage_access(
            db,
            project_id=obj.id,
        )

        # --------------------------------------------------------------
        # 2. Re-create the submitted member assignments.
        # --------------------------------------------------------------

        role_names = {
            member_access.role
            for member_access in payload.member_accesses
        }

        if role_names:
            roles_result = await db.execute(
                select(RoleModel).where(
                    RoleModel.name.in_(role_names),
                    RoleModel.is_active == True,
                )
            )

            role_map = {
                role.name: role.id
                for role in roles_result.scalars().all()
            }
        else:
            role_map = {}

        for member_access in payload.member_accesses:

            # ----------------------------------------------------------
            # PROJECT_ADMIN remains project scoped.
            # ----------------------------------------------------------

            if member_access.role == "PROJECT_ADMIN":

                role_id = role_map.get(
                    "PROJECT_ADMIN"
                )

                if role_id is None:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "PROJECT_ADMIN role "
                            "does not exist"
                        ),
                    )

                # Avoid duplicate project-admin assignment.
                existing_admin = await db.execute(
                    select(UserRole).where(
                        UserRole.user_id
                        == member_access.user_id,
                        UserRole.role_id
                        == role_id,
                        UserRole.scope_type
                        == "PROJECT",
                        UserRole.scope_id
                        == obj.id,
                    )
                )

                admin_role = (
                    existing_admin.scalars().first()
                )

                if admin_role is not None:
                    admin_role.is_active = True
                    db.add(admin_role)
                else:
                    db.add(
                        UserRole(
                            user_id=member_access.user_id,
                            role_id=role_id,
                            scope_type="PROJECT",
                            scope_id=obj.id,
                            is_active=True,
                        )
                    )

            # ----------------------------------------------------------
            # Ordinary editor/viewer access is stage scoped.
            # ----------------------------------------------------------

            elif member_access.role in {
                "PROJECT_EDITOR",
                "PROJECT_VIEWER",
            }:

                await assign_user_to_project_stages(
                    db,
                    project_id=obj.id,
                    user_id=member_access.user_id,
                    role_name=member_access.role,
                )

    if (
        getattr(obj, "project_class", None)
        and obj.project_class.name == "RECURRING"
    ):
        from models.project_stage_instances import (
            ProjectStage as StageInstanceProjectStage,
        )

        existing_recurring = await db.execute(
            select(StageInstanceModel).where(
                StageInstanceModel.project_id == obj.id,
                StageInstanceModel.stage
                == StageInstanceProjectStage.RECURRING,
            )
        )

        if not existing_recurring.scalars().first():
            db.add(
                StageInstanceModel(
                    project_id=obj.id,
                    stage=StageInstanceProjectStage.RECURRING,
                    approval_status="draft",
                    sequence=0,
                )
            )

    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project(db: AsyncSession, project_id: UUID) -> bool:
    obj = await get_project(db, project_id)
    if obj:
        await db.delete(obj)
        return True
    return False


_PROJECT_EAGER = [
    selectinload(Project.stage_configs),
    selectinload(Project.org_links),
    selectinload(Project.postcodes).selectinload(ProjectPostcode.jurisdiction),
    selectinload(Project.stage_instances),
    selectinload(Project.project_parties),
    selectinload(Project.reporting_boundaries),
    selectinload(Project.benchmark_mastertype),
    selectinload(Project.benchmark_typecast),
]


async def list_projects_for_org(
    db: AsyncSession,
    organisation_id: UUID,
) -> list[Project]:
    query = (
        select(Project)
        .where(Project.proponent_org_id == organisation_id)
        .options(*_PROJECT_EAGER)
    )
    result = await db.execute(query)
    projects = result.scalars().all()
    await _enrich(db, projects)
    return projects


async def list_projects_for_user_roles(
    db: AsyncSession,
    user_id: UUID,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Project]:

    # --------------------------------------------------------------
    # Project administrators
    # --------------------------------------------------------------

    project_admin_subquery = (
        select(UserRole.scope_id)
        .join(
            RoleModel,
            RoleModel.id == UserRole.role_id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == "PROJECT",
            RoleModel.name == "PROJECT_ADMIN",
        )
    )

    # --------------------------------------------------------------
    # Organisation administrators
    # --------------------------------------------------------------

    org_admin_project_subquery = (
        select(Project.id)
        .join(
            UserRole,
            UserRole.scope_id == Project.proponent_org_id,
        )
        .join(
            RoleModel,
            RoleModel.id == UserRole.role_id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == "ORGANISATION",
            RoleModel.name == "ORG_ADMIN",
        )
    )

    # --------------------------------------------------------------
    # Stage-level project membership
    #
    # A user belongs to a project if they have an active
    # PROJECT_EDITOR or PROJECT_VIEWER role on at least one
    # currently enabled stage belonging to that project.
    #
    # Disabled historical stages do not provide membership.
    # --------------------------------------------------------------

    stage_project_subquery = (
        select(StageInstanceModel.project_id)
        .join(
            UserRole,
            UserRole.scope_id == StageInstanceModel.id,
        )
        .join(
            RoleModel,
            RoleModel.id == UserRole.role_id,
        )
        .join(
            Project,
            Project.id == StageInstanceModel.project_id,
        )
        .outerjoin(
            ProjectStageConfig,
            and_(
                ProjectStageConfig.project_id
                == StageInstanceModel.project_id,
                ProjectStageConfig.stage
                == StageInstanceModel.stage,
            ),
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == "STAGE",
            RoleModel.name.in_(
                (
                    "PROJECT_EDITOR",
                    "PROJECT_VIEWER",
                )
            ),
            or_(
                and_(
                    StageInstanceModel.stage
                    != StageInstanceProjectStage.RECURRING,
                    ProjectStageConfig.enabled == True,
                ),
                and_(
                    StageInstanceModel.stage
                    == StageInstanceProjectStage.RECURRING,
                    Project.project_class == "RECURRING",
                ),
            ),
        )
    )

    project_ids_query = select(Project.id).where(
        or_(
            Project.id.in_(project_admin_subquery),
            Project.id.in_(org_admin_project_subquery),
            Project.id.in_(stage_project_subquery),
        )
    )

    if is_active is not None:
        project_ids_query = project_ids_query.where(
            Project.is_active == is_active
        )

    project_ids_result = await db.execute(
        project_ids_query
    )

    project_ids = list(
        project_ids_result.scalars().all()
    )

    if not project_ids:
        return []

    query = (
        select(Project)
        .where(Project.id.in_(project_ids))
        .options(*_PROJECT_EAGER)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)

    projects = result.scalars().all()

    await _enrich(
        db,
        projects,
    )

    return projects


async def touch_project(db: AsyncSession, project_id: UUID) -> None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    obj = result.scalar_one_or_none()
    if obj:
        obj.updated_on = datetime.utcnow()
        db.add(obj)


async def get_jurisdiction_name_for_project(
    db: AsyncSession, project_id: UUID
) -> Optional[str]:
    """Return the jurisdiction name for a project via proponent org's jurisdiction_id FK.
    Falls back to 'Australia' if jurisdiction is not set.
    """
   
    from models.jurisdictions import Jurisdiction
    stmt = (
        select(Jurisdiction.name)
        .select_from(Project)
        .join(Organization, Project.proponent_org_id == Organization.id)
        .outerjoin(Jurisdiction, Jurisdiction.id == Organization.jurisdiction_id)
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    jurisdiction_name = result.scalar_one_or_none()
    
    final_result = jurisdiction_name or "Australia"
     
    return final_result


async def get_reporting_boundaries(
    db: AsyncSession, project_id: UUID
) -> list[ProjectReportingBoundary]:
    result = await db.execute(
        select(ProjectReportingBoundary)
        .where(ProjectReportingBoundary.project_id == project_id)
        .order_by(ProjectReportingBoundary.sort_order)
    )
    return list(result.scalars().all())