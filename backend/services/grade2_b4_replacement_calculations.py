# """
# services/grade2_b4_replacement_calculations.py

# Service for Grade 2 Component Level Replacement (B4) emissions calculations.

# Mirrors the Excel formula in tbl_component_lvl_calcs14 (MVP - Grade 1234 sheet):

#   replacement_cycles = ROUNDDOWN((operations_end_year - operations_start_year) / life_years, 0)
#   emissions_b4_tco2e = replacement_cycles
#                        × XLOOKUP(Emissions Source, tbl_component_lvl_calcs[Emissions Source],
#                                   tbl_component_lvl_calcs[Emissions (tCO2e)], "")

# Where tbl_component_lvl_calcs[Emissions (tCO2e)] is the Grade 2 total Scope 3
# (A1-3 + A4 + A5) looked up from v_grade2_component_level.
# """

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper

from models.project import Project
from models.grade2_component_level_view import Grade2ComponentLevel


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class Grade2B4ReplacementRequest(BaseModel):
    """Input parameters for the Component Level Replacement (B4) calculation."""

    # Project to source jurisdiction and operational period from
    project_id: UUID

    # Grade 2 lookup keys
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    quantity: float = Field(..., gt=0)
    source: Optional[str] = None

    # B4-specific user input — component life (not the project operational life)
    life_years: float = Field(..., gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "emissions_category": "Surface and Underground Drainage",
                "emissions_sub_category": "Stormwater Drainage Pipe",
                "emissions_source": "375mm Class 3 RRJ",
                "quantity": 100,
                "life_years": 50,
            }
        }


class Grade2B4ReplacementResponse(BaseModel):
    """Response with the B4 replacement emissions result."""

    # Echoed inputs
    jurisdiction: str
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    quantity: float
    uom: Optional[str] = None
    source_comments: Optional[str] = None
    life_years: float
    operations_start_year: int
    operations_end_year: int

    # Grade 2 intermediate values
    factor_a1_a3: Optional[float] = None
    factor_a4: Optional[float] = None
    factor_a5: Optional[float] = None
    grade2_total_scope3_tco2e: float

    # B4 result
    replacement_cycles: int
    total_emissions_tco2e: float


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────

class Grade2B4ReplacementCalculator:
    """
    Calculates Component Level Replacement (B4) emissions for Grade 2 (and 3) projects.

    Steps:
      1. Look up Grade 2 emission factors from v_grade2_component_level.
      2. Compute grade2_total_scope3_tco2e = (A1-3 + A4 + A5) × quantity.
      3. reference_period = MIN(operational_period, 50 years constant cap)
      4. replacement_cycles = ROUNDDOWN(reference_period / life_years, 0)
         — uses int() truncation toward zero, exactly matching Excel ROUNDDOWN(..., 0).
      5. emissions_b4_tco2e = replacement_cycles × grade2_total_scope3_tco2e.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: Grade2B4ReplacementRequest,
    ) -> Grade2B4ReplacementResponse:
        """
        Perform B4 replacement calculation.

        Raises:
            ValueError: when the project is not found, required project fields
                        (commencement_of_operations, operational_life_years) are
                        missing, or no matching Grade 2 row is found in the view.
        """
        project = await self._fetch_project_data(db, request.project_id)

        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, request.project_id)

        if project.commencement_of_operations is None:
            raise ValueError(
                f"Project '{request.project_id}' is missing commencement_of_operations."
            )
        if project.operational_life_years is None:
            raise ValueError(
                f"Project '{request.project_id}' is missing operational_life_years."
            )

        operations_start_year = project.commencement_of_operations.year
        operations_end_year = operations_start_year + project.operational_life_years

        lookup = await self._fetch_grade2_lookup(
            db, request, jurisdiction=jurisdiction
        )

        if not lookup:
            raise ValueError(
                f"No Grade 2 data found for: "
                f"Jurisdiction='{jurisdiction}', "
                f"Emissions Category='{request.emissions_category}', "
                f"Emissions Sub-Category='{request.emissions_sub_category}', "
                f"Emissions Source='{request.emissions_source}'"
            )

        qty = float(request.quantity)
        factor_a1_a3 = self._as_float(lookup.factor_a1_a3) or 0.0
        factor_a4    = self._as_float(lookup.factor_a4) or 0.0
        factor_a5    = self._as_float(lookup.factor_a5) or 0.0

        grade2_total_scope3 = (factor_a1_a3 + factor_a4 + factor_a5) * qty

        # ROUNDDOWN(MIN(reference_period, design_life) / life_years, 0)
        # Reference period is capped at 50 years (constant).
        # Design life is the project's operational life (end_year - start_year).
        # int() truncates toward zero, matching Excel ROUNDDOWN for both positive and zero values.
        design_life = operations_end_year - operations_start_year
        reference_period = min(design_life, 50)
        replacement_cycles = int(reference_period / request.life_years)

        emissions_b4 = replacement_cycles * grade2_total_scope3

        return Grade2B4ReplacementResponse(
            jurisdiction=jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            quantity=qty,
            uom=lookup.uom,
            source_comments=lookup.source_comments,
            life_years=request.life_years,
            operations_start_year=operations_start_year,
            operations_end_year=operations_end_year,
            factor_a1_a3=factor_a1_a3 if factor_a1_a3 != 0.0 else None,
            factor_a4=factor_a4 if factor_a4 != 0.0 else None,
            factor_a5=factor_a5 if factor_a5 != 0.0 else None,
            grade2_total_scope3_tco2e=round_result(grade2_total_scope3),
            replacement_cycles=replacement_cycles,
            total_emissions_tco2e=round_result(emissions_b4),
        )

    async def _fetch_project_data(self, db: AsyncSession, project_id: UUID) -> Project:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        return project

    async def _fetch_grade2_lookup(
        self,
        db: AsyncSession,
        request: Grade2B4ReplacementRequest,
        *,
        jurisdiction: str,
    ) -> Optional[Grade2ComponentLevel]:
        stmt = (
            select(Grade2ComponentLevel)
            .where(
                Grade2ComponentLevel.jurisdiction == jurisdiction,
                Grade2ComponentLevel.emissions_category == request.emissions_category,
                Grade2ComponentLevel.emissions_sub_category == request.emissions_sub_category,
                Grade2ComponentLevel.emissions_source == request.emissions_source,
            )
        )
        if request.source is not None:
            stmt = stmt.where(Grade2ComponentLevel.source_comments == request.source)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def _as_float(value) -> Optional[float]:
        if value is None:
            return None
        return float(value)


# Singleton instance used by the router
calculator = Grade2B4ReplacementCalculator()
