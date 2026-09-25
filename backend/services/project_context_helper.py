"""
project_context_helper.py

Shared helpers to fetch project context (jurisdiction, operational years, region, dataset revision)
given a projectId. Used by all calculation services.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.project import Project
from models.organizations import Organization

class ProjectContextHelper:
    """Helper to fetch and resolve project details for calculations."""
    
    @staticmethod
    async def fetch_project(db: AsyncSession, project_id: UUID) -> Project:
        """
        Fetch project by ID with validation.
        
        Raises:
            ValueError: if project not found
        """
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()
        if project is None:
            raise ValueError(f"Project '{project_id}' not found")
        return project
    
    @staticmethod
    async def fetch_project_region(db: AsyncSession, project_id: UUID) -> str:
        """
        Fetch region name from the proponent organization linked to the project.

        Lookup chain:
            project.proponent_org_id → organization.region_id → jurisdictions.name

        Returns:
            str: region name from the jurisdictions table.
                 Falls back to "New South Wales" if not set.
        """
        project = await ProjectContextHelper.fetch_project(db, project_id)
        org_result = await db.execute(
            select(Organization).where(Organization.id == project.proponent_org_id)
        )
        org = org_result.scalars().first()
        if org and org.region:
            return org.region.name
        return "New South Wales"

    @staticmethod
    def get_operational_years(project: Project) -> tuple[int, int]:
        """
        Extract operational start and end years from project.
        
        Returns:
            tuple: (operations_start_year, operations_end_year)
            
        Raises:
            ValueError: if required fields missing
        """
        if project.commencement_of_operations is None:
            raise ValueError(
                f"Project '{project.id}' missing commencement_of_operations"
            )
        if project.operational_life_years is None:
            raise ValueError(
                f"Project '{project.id}' missing operational_life_years"
            )
        
        ops_start = project.commencement_of_operations.year
        ops_end = ops_start + project.operational_life_years
        
        return ops_start, ops_end
    
    @staticmethod
    async def fetch_jurisdiction(db: AsyncSession, project_id: UUID) -> str:
        """
        Fetch jurisdiction name from the proponent organization linked to the project.

        Lookup chain:
            project.proponent_org_id → organization.jurisdiction_id → jurisdictions.name

        Returns:
            str: jurisdiction name from the jurisdictions table.
                 Falls back to 'Australia' if not set.
        """
        project = await ProjectContextHelper.fetch_project(db, project_id)
        org_result = await db.execute(
            select(Organization).where(Organization.id == project.proponent_org_id)
        )
        org = org_result.scalars().first()
        if org and org.jurisdiction:
            return org.jurisdiction.name
        return "Australia"

    @staticmethod
    async def fetch_default_dataset_revision(db: AsyncSession) -> Optional[UUID]:
        """
        Fetch the DEFAULT dataset revision ID.

        Selects the most recent published DEFAULT dataset revision.
        Orders by created_at DESC to ensure deterministic behavior
        when multiple DEFAULT revisions exist.

        Returns:
            Optional[UUID]: The ID of the default dataset revision, or None if not found.
        """
        from models.dataset_revisions import DatasetRevision
        
        result = await db.execute(
            select(DatasetRevision.id)
            .where(
                (DatasetRevision.scope_type == "DEFAULT")
                & (DatasetRevision.status == "published")
            )
            .order_by(DatasetRevision.created_at.desc())
            .limit(1)
        )
        revision_id = result.scalars().first()
        return revision_id

    @staticmethod
    async def fetch_project_dataset_revision(db: AsyncSession, project_id: UUID) -> Optional[UUID]:
        """
        Fetch the assigned dataset revision ID for a project.

        Lookup chain:
            project.id → project_dataset_revisions.project_id → dataset_revision_id

        Falls back to DEFAULT dataset revision if no assignment exists.

        Returns:
            Optional[UUID]: The dataset revision ID assigned to the project,
                          or the DEFAULT revision ID, or None if neither exists.
        """
        from models.project_dataset_revisions import ProjectDatasetRevision
        
        # First, check if project has a specific dataset revision assigned
        result = await db.execute(
            select(ProjectDatasetRevision.dataset_revision_id)
            .where(ProjectDatasetRevision.project_id == project_id)
            .order_by(ProjectDatasetRevision.applied_at.desc())
            .limit(1)
        )
        revision_id = result.scalars().first()
        
        if revision_id is not None:
            return revision_id
        
        # Fall back to DEFAULT dataset revision
        return await ProjectContextHelper.fetch_default_dataset_revision(db)

    @staticmethod
    async def get_project_context(
        db: AsyncSession,
        project_id: UUID,
    ) -> dict:
        """
        Fetch complete project context for calculations.

        Returns:
            dict with keys:
                - jurisdiction: str (from organization's jurisdiction_id → jurisdictions table)
                - region: str (from organization's region_id → jurisdictions table)
                - operations_start_year: int
                - operations_end_year: int
                - dataset_revision_id: Optional[UUID] (assigned or DEFAULT)
        """
        project = await ProjectContextHelper.fetch_project(db, project_id)
        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
        region = await ProjectContextHelper.fetch_project_region(db, project_id)
        ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
        dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(db, project_id)

        return {
            "jurisdiction": jurisdiction,
            "region": region,
            "operations_start_year": ops_start,
            "operations_end_year": ops_end,
            "dataset_revision_id": dataset_revision_id,
        }