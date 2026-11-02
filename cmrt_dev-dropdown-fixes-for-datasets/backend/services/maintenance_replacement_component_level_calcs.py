# """
# services/maintenance_replacement_component_level_calcs.py
#
# Service for Component Level - Maintenance (B2-5) Stage (Cell B227) emissions calculations.
#
# Based on Excel formulas from the 'MVP - Grade 1234' sheet,
# table: tbl_maintenance_replacement_component_level
#
# === FORMULA REFERENCE ===
#
# Number of occurrences
#   = IFERROR(FLOOR($C$225 / [@[Frequency (years)]], 1), 0)
#   where $C$225 = reference_period (project input — passed as API parameter)
#
# Scope 3 Emissions (tCO2e)
#   = [@[Number of occurrences]]
#     * [@Quantity]
#     * INDEX(tbl_maintenance_replacement_component_level[Emissions intensity (tCO2e/UoM)],
#             MATCH([@Item], tbl_maintenance_replacement_component_level[Item], 0))
#
# Emissions (tCO2e)
#   = [@[Scope 3 Emissions (tCO2e)]]
#
# === DB VIEW USED ===
#   v_maintenance_replacement_component_level
#     Columns: "Jurisdiction", "Activity Type", "Item", "Unit",
#              "Emissions intensity (tCO2e/UoM)", "Default frequency (years)", "Source/Comments"
# """

import math
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class MaintenanceCalcRequest(BaseModel):
    """
    Input for a single Component Level - Maintenance (B2-5) Stage row.
    Matches user-entered columns from tbl_maintenance_replacement_component_level.
    """
    jurisdiction: str = Field(..., description="e.g. 'Australia' or 'New Zealand'")
    activity_type: str = Field(..., description="e.g. 'Road resurface', 'Road reconstruction'")
    item: str = Field(..., description="e.g. 'Local road - rural'")
    unit: str = Field(..., description="Unit of measure, e.g. 'm2'")
    quantity: float = Field(..., gt=0, description="Quantity per maintenance event in the stated unit")
    reference_period: float = Field(
        ..., gt=0, description="Reference period in years (cell $C$225 in Excel)"
    )
    frequency_years: float = Field(
        ..., gt=0, description="Maintenance interval in years — [@[Frequency (years)]] in Excel"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "activity_type": "Road resurface",
                "item": "Local road - rural",
                "unit": "m2",
                "quantity": 5000,
                "reference_period": 100,
                "frequency_years": 10,
            }
        }
    }


class MaintenanceCalcResponse(BaseModel):
    """
    Output matching the tbl_maintenance_replacement_component_level calculation columns.
    """
    # ── Inputs echoed back ───────────────────────────────────────────────────
    jurisdiction: str
    activity_type: str
    item: str
    unit: str
    quantity: float
    reference_period: float

    # ── Looked-up factors ────────────────────────────────────────────────────
    emissions_intensity_tco2e_per_uom: Optional[float] = Field(
        None, description="Emissions intensity (tCO2e/UoM) from v_maintenance_replacement_component_level"
    )
    default_frequency_years: Optional[int] = Field(
        None, description="Default maintenance frequency from view"
    )
    frequency_years_used: float = Field(
        ..., description="Frequency used in calculation (user-supplied)"
    )
    source_comments: Optional[str] = None

    # ── Calculated columns ───────────────────────────────────────────────────
    number_of_occurrences: int = Field(
        ..., description="FLOOR(reference_period / frequency, 1) — mirrors Excel IFERROR/FLOOR"
    )
    scope3_emissions_tco2e: float = Field(
        ..., description="number_of_occurrences × quantity × emissions_intensity"
    )
    total_emissions_tco2e: float = Field(
        ..., description="scope3_emissions_tco2e (as per Excel formula)"
    )

    # ── Warnings ─────────────────────────────────────────────────────────────
    data_warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal data warnings, e.g. missing lookup rows.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────

class MaintenanceReplacementCalculator:
    """
    Calculates Component Level - Maintenance (B2-5) Stage emissions for one table row.
    Mirrors the Excel structured table formulas exactly.
    """

    @staticmethod
    def _f(value) -> Optional[float]:
        """Safely coerce a DB value (Decimal / None / str) to float."""
        if value is None:
            return None
        try:
            return float(Decimal(str(value)))
        except Exception:
            return None

    async def _fetch_factor_row(
        self,
        db: AsyncSession,
        jurisdiction: str,
        activity_type: str,
        item: str,
    ) -> Optional[dict]:
        """
        Fetch one row from v_maintenance_replacement_component_level.
        Matches on Jurisdiction + Activity Type + Item.
        """
        sql = text(
            """
            SELECT
                "Emissions intensity (tCO2e/UoM)",
                "Default frequency (years)",
                "Unit",
                "Source/Comments"
            FROM v_maintenance_replacement_component_level
            WHERE "Jurisdiction"   = :jurisdiction
              AND "Activity Type"  = :activity_type
              AND "Item"           = :item
            LIMIT 1
            """
        )
        result = await db.execute(
            sql,
            {
                "jurisdiction": jurisdiction,
                "activity_type": activity_type,
                "item": item,
            },
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None

    async def calculate(
        self,
        db: AsyncSession,
        request: MaintenanceCalcRequest,
    ) -> MaintenanceCalcResponse:
        data_warnings: list[str] = []

        # ── 1. Fetch factor row from view ─────────────────────────────────────
        factor_row = await self._fetch_factor_row(
            db,
            request.jurisdiction,
            request.activity_type,
            request.item,
        )

        if not factor_row:
            data_warnings.append(
                f"No row found in v_maintenance_replacement_component_level for "
                f"Jurisdiction='{request.jurisdiction}', "
                f"Activity Type='{request.activity_type}', "
                f"Item='{request.item}'. "
                f"Emissions intensity defaulted to 0."
            )

        emissions_intensity = self._f(
            factor_row.get("Emissions intensity (tCO2e/UoM)") if factor_row else None
        )
        default_freq = factor_row.get("Default frequency (years)") if factor_row else None
        source_comments = factor_row.get("Source/Comments") if factor_row else None

        # ── 2. Frequency is a required input ─────────────────────────────────
        # Excel: [@[Frequency (years)]] — always provided by the user.
        freq_used = request.frequency_years

        # ── 3. Number of occurrences ──────────────────────────────────────────
        # Excel: =IFERROR(FLOOR($C$225 / [@[Frequency (years)]], 1), 0)
        # IFERROR traps division by zero; frequency is gt=0 so this only
        # fires in the rare case of a floating-point exception.
        try:
            occurrences = int(math.floor(request.reference_period / freq_used))
        except Exception:
            occurrences = 0

        # ── 4. Scope 3 Emissions ──────────────────────────────────────────────
        # Excel: =occurrences * Quantity * EI
        ei = emissions_intensity if emissions_intensity is not None else 0.0
        scope3 = occurrences * request.quantity * ei

        # ── 5. Total Emissions (tCO2e) ────────────────────────────────────────
        # Excel: =[@[Scope 3 Emissions (tCO2e)]]
        total = scope3

        return MaintenanceCalcResponse(
            jurisdiction=request.jurisdiction,
            activity_type=request.activity_type,
            item=request.item,
            unit=request.unit,
            quantity=request.quantity,
            reference_period=request.reference_period,
            emissions_intensity_tco2e_per_uom=emissions_intensity,
            default_frequency_years=int(default_freq) if default_freq is not None else None,
            frequency_years_used=freq_used,
            source_comments=source_comments,
            number_of_occurrences=occurrences,
            scope3_emissions_tco2e=round_result(scope3),
            total_emissions_tco2e=round_result(total),
            data_warnings=data_warnings,
        )


# Singleton
calculator = MaintenanceReplacementCalculator()
