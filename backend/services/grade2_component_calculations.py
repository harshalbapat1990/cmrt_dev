# """
# services/grade2_component_calculations.py

# Service for Grade 2 component-level emissions calculations.

# Based on Excel XLOOKUP formulas:
#   Lookup key: Jurisdiction + Emissions Category + Emissions Sub-Category + Emissions Source
#   Lookup table: Grade 2 background metrics in the selected dataset revision

# Formulas:
#   A1-3 Emissions  = Product Stage (A1-3) (tCO2e/UoM)  × Quantity
#   A4 Emissions    = Transport Stage (A4) (tCO2e/UoM)   × Quantity
#   A5 Emissions    = Construction Stage (A5) (tCO2e/UoM) × Quantity
#   Total Scope 3   = A1-3 + A4 + A5
# """

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import aliased

from models.background_grade_metrics import BackgroundGradeMetric
from models.emissions_categories_new import EmissionsCategoryRecord
from models.jurisdictions import Jurisdiction
from models.metric_types import MetricType
from models.units import Unit

from services._calc_utils import round_result


async def fetch_grade2_revision_factors(
    db: AsyncSession,
    *,
    jurisdiction: str,
    emissions_category: str,
    emissions_sub_category: str,
    emissions_source: str,
    dataset_revision_id: UUID,
    source: Optional[str] = None,
) -> Optional[dict]:
    """Return the Grade 2 factor set for one key within one revision."""
    category = aliased(EmissionsCategoryRecord, name="grade2_category")
    subcategory = aliased(EmissionsCategoryRecord, name="grade2_subcategory")
    stmt = (
        select(
            MetricType.code.label("metric_type_code"),
            BackgroundGradeMetric.value,
            BackgroundGradeMetric.source.label("source_comments"),
            Unit.code.label("uom"),
        )
        .join(MetricType, MetricType.id == BackgroundGradeMetric.metric_type_id)
        .outerjoin(Unit, Unit.id == BackgroundGradeMetric.unit_id)
        .outerjoin(Jurisdiction, Jurisdiction.id == BackgroundGradeMetric.jurisdiction_id)
        .outerjoin(category, category.id == BackgroundGradeMetric.emissions_category_id)
        .outerjoin(subcategory, subcategory.id == BackgroundGradeMetric.emissions_subcategory_id)
        .where(
            BackgroundGradeMetric.grade_id == 2,
            BackgroundGradeMetric.dataset_revision_id == dataset_revision_id,
            BackgroundGradeMetric.is_active.is_(True),
            Jurisdiction.name == jurisdiction,
            category.name == emissions_category,
            subcategory.name == emissions_sub_category,
            BackgroundGradeMetric.emissions_source == emissions_source,
            MetricType.code.in_(
                ("carbon_storage", "emission_intensity_a1_a3", "emission_intensity_a4", "emission_intensity_a5")
            ),
        )
        .order_by(BackgroundGradeMetric.id)
    )
    if source is not None:
        stmt = stmt.where(BackgroundGradeMetric.source == source)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return None

    lookup = {
        "factor_a1_a3": None,
        "factor_a4": None,
        "factor_a5": None,
        "carbon_storage": None,
        "uom": None,
        "source_comments": None,
    }
    metric_keys = {
        "emission_intensity_a1_a3": "factor_a1_a3",
        "emission_intensity_a4": "factor_a4",
        "emission_intensity_a5": "factor_a5",
        "carbon_storage": "carbon_storage",
    }
    for row in rows:
        key = metric_keys.get(row.metric_type_code)
        if key:
            lookup[key] = float(row.value) if row.value is not None else None
        if lookup["uom"] is None:
            lookup["uom"] = row.uom
        if lookup["source_comments"] is None:
            lookup["source_comments"] = row.source_comments
    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class Grade2CalculationRequest(BaseModel):
    """Input parameters for Grade 2 component-level calculation."""
    jurisdiction: str
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    quantity: float = Field(..., gt=0)
    source: Optional[str] = None
    project_id: Optional[UUID] = None
    dataset_revision_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction": "Australia",
                "emissions_category": "Constructors' Site Overheads",
                "emissions_sub_category": "Principal's Project Accommodation",
                "emissions_source": "Establishment of Principals Project Site Buildings",
                "quantity": 100,
                "dataset_revision_id": "d8f12299-a0e2-4cc7-b879-04df57bda83a",
            }
        }


class Grade2CalculationResponse(BaseModel):
    """Response with emissions breakdown by lifecycle stage."""
    # Echo inputs
    jurisdiction: str
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    quantity: float
    uom: Optional[str] = None
    source_comments: Optional[str] = None

    # Emission factors retrieved from the selected dataset revision
    factor_a1_a3: Optional[float] = None
    factor_a4: Optional[float] = None
    factor_a5: Optional[float] = None
    carbon_storage: Optional[float] = None

    # Calculated emissions (tCO2e)
    product_stage_a1_a3_tco2e: float
    transport_stage_a4_tco2e: float
    construction_stage_a5_tco2e: float
    total_emissions_tco2e: float


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────

class Grade2ComponentCalculator:
    """
    Service for Grade 2 component-level calculations.
    Reads Grade 2 metric records from the requested dataset revision and applies
    factor × quantity formulas.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: Grade2CalculationRequest,
    ) -> Grade2CalculationResponse:
        """
        Perform Grade 2 calculation.

        Raises ValueError when no matching factors are found.
        """
        lookup = await self._fetch_lookup(db, request)

        if not lookup:
            raise ValueError(
                f"No Grade 2 data found for: "
                f"Jurisdiction='{request.jurisdiction}', "
                f"Emissions Category='{request.emissions_category}', "
                f"Emissions Sub-Category='{request.emissions_sub_category}', "
                f"Emissions Source='{request.emissions_source}'"
            )

        qty = float(request.quantity)

        factor_a1_a3 = self._as_float(lookup.get("factor_a1_a3"))
        factor_a4    = self._as_float(lookup.get("factor_a4"))
        factor_a5    = self._as_float(lookup.get("factor_a5"))

        a1_a3 = (factor_a1_a3 or 0.0) * qty
        a4    = (factor_a4    or 0.0) * qty
        a5    = (factor_a5    or 0.0) * qty
        total = a1_a3 + a4 + a5

        return Grade2CalculationResponse(
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            quantity=qty,
            uom=lookup.get("uom"),
            source_comments=lookup.get("source_comments"),
            factor_a1_a3=factor_a1_a3,
            factor_a4=factor_a4,
            factor_a5=factor_a5,
            carbon_storage=self._as_float(lookup.get("carbon_storage")),
            product_stage_a1_a3_tco2e=a1_a3,
            transport_stage_a4_tco2e=a4,
            construction_stage_a5_tco2e=a5,
            total_emissions_tco2e=round_result(total),
        )

    async def _fetch_lookup(
        self,
        db: AsyncSession,
        request: Grade2CalculationRequest,
    ) -> Optional[dict]:
        """
        Pivot Grade 2 background metrics for a single authorized revision.
        Optional source filter narrows to a specific source/comments value.
        """
        if request.dataset_revision_id is None:
            raise ValueError("dataset_revision_id is required for Grade 2 calculations")

        return await fetch_grade2_revision_factors(
            db,
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            dataset_revision_id=request.dataset_revision_id,
            source=request.source,
        )

    @staticmethod
    def _as_float(value) -> Optional[float]:
        if value is None:
            return None
        return float(value)


# Singleton instance used by the router
calculator = Grade2ComponentCalculator()
