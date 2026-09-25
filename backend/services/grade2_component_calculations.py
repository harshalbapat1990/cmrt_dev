# """
# services/grade2_component_calculations.py

# Service for Grade 2 component-level emissions calculations.

# Based on Excel XLOOKUP formulas:
#   Lookup key: Jurisdiction + Emissions Category + Emissions Sub-Category + Emissions Source
#   Lookup table: v_grade2_component_level (PostgreSQL view)

# Formulas:
#   A1-3 Emissions  = Product Stage (A1-3) (tCO2e/UoM)  × Quantity
#   A4 Emissions    = Transport Stage (A4) (tCO2e/UoM)   × Quantity
#   A5 Emissions    = Construction Stage (A5) (tCO2e/UoM) × Quantity
#   Total Scope 3   = A1-3 + A4 + A5
# """

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services._calc_utils import round_result


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

    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction": "Australia",
                "emissions_category": "Constructors' Site Overheads",
                "emissions_sub_category": "Principal's Project Accommodation",
                "emissions_source": "Establishment of Principals Project Site Buildings",
                "quantity": 100
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

    # Emission factors retrieved from view
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
    Queries v_grade2_component_level and applies factor × quantity formulas.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: Grade2CalculationRequest,
    ) -> Grade2CalculationResponse:
        """
        Perform Grade 2 calculation.

        Raises:
            ValueError: when no matching row is found in the view.
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

        factor_a1_a3 = self._as_float(lookup.get("Product Stage (A1-3) (tCO2e/UoM)"))
        factor_a4    = self._as_float(lookup.get("Transport Stage (A4) (tCO2e/UoM)"))
        factor_a5    = self._as_float(lookup.get("Construction Stage (A5) (tCO2e/UoM)"))

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
            uom=lookup.get("UoM"),
            source_comments=lookup.get("Source/Comments"),
            factor_a1_a3=factor_a1_a3,
            factor_a4=factor_a4,
            factor_a5=factor_a5,
            carbon_storage=self._as_float(lookup.get("Carbon Storage (tCO2e/UoM)")),
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
        Query v_grade2_component_level for the matching row.
        Optional source filter narrows to a specific Source/Comments value.
        """
        query = text("""
            SELECT
                "Jurisdiction",
                "Emissions Category",
                "Emissions Sub-Category",
                "Emissions Source",
                "Quantity",
                "UoM",
                "Carbon Storage (tCO2e/UoM)",
                "Product Stage (A1-3) (tCO2e/UoM)",
                "Transport Stage (A4) (tCO2e/UoM)",
                "Construction Stage (A5) (tCO2e/UoM)",
                "Source/Comments"
            FROM v_grade2_component_level
            WHERE "Jurisdiction"          = :jurisdiction
              AND "Emissions Category"    = :emissions_category
              AND "Emissions Sub-Category" = :emissions_sub_category
              AND "Emissions Source"      = :emissions_source
              AND (CAST(:source AS TEXT) IS NULL OR "Source/Comments" = :source)
            LIMIT 1
        """)

        result = await db.execute(
            query,
            {
                "jurisdiction":          request.jurisdiction,
                "emissions_category":    request.emissions_category,
                "emissions_sub_category": request.emissions_sub_category,
                "emissions_source":      request.emissions_source,
                "source":                request.source,
            },
        )

        row = result.fetchone()
        if row is None:
            return None

        lookup = dict(row._mapping)
        # Normalize Decimal → float for all numeric columns
        for key, val in lookup.items():
            if isinstance(val, Decimal):
                lookup[key] = float(val)
        return lookup

    @staticmethod
    def _as_float(value) -> Optional[float]:
        if value is None:
            return None
        return float(value)


# Singleton instance used by the router
calculator = Grade2ComponentCalculator()
