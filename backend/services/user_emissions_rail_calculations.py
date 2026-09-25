"""
services/user_emissions_rail_calculations.py

Rail user-emissions (B8) calculation service.

Applies to both AUS and NZ projects; jurisdiction is resolved automatically
from the project's proponent organisation region.

Excel sheet reference: "B8 - User Emissions - Rail"

One API call per row — caller supplies rail_type + terrain + freight_quantity
for a single train type.

Formulas
--------
  fuel_consumption_l_per_000gtk  — lookup from freight_rail_factors
                                   (train_type, terrain, dataset_revision_id)

  fuel_kl = fuel_consumption_l_per_000gtk × freight_quantity_gtk_per_year / 1_000_000
    where freight_quantity_gtk_per_year is the actual GTK/year value.
    Excel equivalent: =(D157/1000)*E157/1000  (E157 = actual GTK)
    Verified: 4 × 45,000,000 / 1,000,000 = 180 kL (Container Train, Flat, 45,000,000 GTK/yr)

  emissions_intensity_tco2e_kl = scope1_ef + scope3_ef  from v_grade34_detailed_level
    AUS: Jurisdiction='Australia',   Emissions Source='Diesel oil', UoM='kL'
    NZ:  Jurisdiction='New Zealand', Emissions Source='Diesel',     UoM='kL'

  emissions_annual_tco2e           = fuel_kl × emissions_intensity_tco2e_kl
  emissions_total_ref_period_tco2e = emissions_annual_tco2e × operational_life_years
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.user_emissions_rail import (
    RailEmissionsCalculateRequest,
    RailEmissionsCalculateResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# Diesel EF lookup from v_grade34_detailed_level
# ─────────────────────────────────────────────────────────────────────────────

_DIESEL_EF_SQL = text("""
    SELECT
        COALESCE(emission_factor_scope1, 0) + COALESCE(emission_factor_scope3, 0)
            AS diesel_intensity_tco2e_kl
    FROM v_grade34_detailed_level
    WHERE "Jurisdiction"     = :jurisdiction
      AND "Emissions Source" = :source
      AND "UoM"              = 'kL'
    ORDER BY
        -- Prefer rows that have both scope1 and scope3 set
        (emission_factor_scope1 IS NOT NULL)::int
        + (emission_factor_scope3 IS NOT NULL)::int DESC,
        emission_factor_scope1 DESC NULLS LAST
    LIMIT 1
""")


# ─────────────────────────────────────────────────────────────────────────────
# Fuel consumption lookup from freight_rail_factors
# ─────────────────────────────────────────────────────────────────────────────

_FUEL_CONS_SQL = text("""
    SELECT fuel_consumption_l_per_000_gtk
    FROM freight_rail_factors
    WHERE dataset_revision_id = :rid
      AND LOWER(train_type)   = LOWER(:train_type)
      AND LOWER(terrain)      = LOWER(:terrain)
    LIMIT 1
""")


# ─────────────────────────────────────────────────────────────────────────────
# Project info helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get_project_info(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, str]:
    """
    Returns (operational_life_years, country_name).
    country_name is the top-level country jurisdiction linked via the
    proponent organisation (e.g. 'Australia', 'New Zealand').
    For Australian states the parent jurisdiction is resolved automatically.
    """
    row = (
        await db.execute(
            text(
                "SELECT p.operational_life_years,"
                "       j.name AS country_name"
                "  FROM project p"
                "  JOIN organization o ON o.id = p.proponent_org_id"
                "  LEFT JOIN jurisdictions j ON j.id = o.jurisdiction_id"
                " WHERE p.id = :pid"
            ),
            {"pid": str(project_id)},
        )
    ).mappings().first()

    if row is None:
        raise ValueError(f"Project {project_id} not found.")

    if row["operational_life_years"] is None:
        raise ValueError(
            "Project does not have an operational_life_years value set. "
            "Please set it before running the rail user-emissions calculation."
        )

    return int(row["operational_life_years"]), (row["country_name"] or "")


# ─────────────────────────────────────────────────────────────────────────────
# Dataset revision helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get_dataset_revision_id(db: AsyncSession) -> UUID:
    row = (
        await db.execute(
            text(
                "SELECT id FROM dataset_revisions "
                "WHERE status = 'published' "
                "ORDER BY created_at DESC LIMIT 1"
            )
        )
    ).mappings().first()
    if row is None:
        raise ValueError("No published dataset revision found.")
    return row["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Main calculation entry point
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_rail(
    db: AsyncSession,
    req: RailEmissionsCalculateRequest,
) -> RailEmissionsCalculateResponse:
    """
    Pure calculation — no DB writes.

    1. Resolve project operational life & jurisdiction.
    2. Determine AUS or NZ → select fuel source string.
    3. Fetch emissions intensity (scope1 + scope3) from v_grade34_detailed_level.
    4. Fetch fuel consumption from freight_rail_factors (rail_type + terrain).
    5. Calculate fuel_kl, annual emissions, total ref period emissions.
    6. Return flat response.
    """

    # ── 1. Project info ───────────────────────────────────────────────────────
    operational_life_years, jurisdiction_name = await _get_project_info(db, req.project_id)

    # ── 2. Dataset revision ───────────────────────────────────────────────────
    dataset_revision_id = await _get_dataset_revision_id(db)

    # ── 3. AUS vs NZ fuel source ──────────────────────────────────────────────
    #   NZ projects have jurisdiction_name = 'New Zealand'.
    #   All Australian state jurisdictions → use 'Diesel oil' (Australia EF).
    is_nz = jurisdiction_name == "New Zealand"
    fuel_source = "Diesel" if is_nz else "Diesel oil"
    grade34_jurisdiction = "New Zealand" if is_nz else "Australia"

    # ── 4. Emissions intensity from v_grade34_detailed_level ──────────────────
    ef_row = (
        await db.execute(
            _DIESEL_EF_SQL,
            {"jurisdiction": grade34_jurisdiction, "source": fuel_source},
        )
    ).mappings().first()

    if ef_row is None:
        raise ValueError(
            f"No emissions factor found in v_grade34_detailed_level for "
            f"Jurisdiction='{grade34_jurisdiction}', Source='{fuel_source}', UoM='kL'."
        )
    emissions_intensity = Decimal(str(ef_row["diesel_intensity_tco2e_kl"])).quantize(Decimal("0.000001"))

    # ── 5. Fuel consumption from freight_rail_factors ─────────────────────────
    fuel_row = (
        await db.execute(
            _FUEL_CONS_SQL,
            {
                "rid": str(dataset_revision_id),
                "train_type": req.rail_type,
                "terrain": req.terrain,
            },
        )
    ).mappings().first()

    if fuel_row is None or fuel_row["fuel_consumption_l_per_000_gtk"] is None:
        raise ValueError(
            f"No fuel consumption data found in freight_rail_factors for "
            f"rail_type='{req.rail_type}', terrain='{req.terrain}'."
        )

    fuel_consumption = Decimal(str(fuel_row["fuel_consumption_l_per_000_gtk"]))

    # ── 6. Calculations ───────────────────────────────────────────────────────
    # fuel_kl = fuel_consumption (L/1000 GTK) × freight_qty (actual GTK/yr) / 1,000,000
    # Excel: =(D157/1000)*E157/1000  → (4/1000) × 45,000,000 / 1000 = 180 kL
    # Verified: 4 × 45,000,000 / 1,000,000 = 180 kL (Container Train, Flat, 45M GTK/yr)
    fuel_kl = (fuel_consumption * req.freight_quantity_gtk_per_year / Decimal("1000000")).quantize(Decimal("0.000001"))
    emissions_annual = (fuel_kl * emissions_intensity).quantize(Decimal("0.000001"))
    emissions_total = (emissions_annual * Decimal(str(operational_life_years))).quantize(Decimal("0.000001"))

    return RailEmissionsCalculateResponse(
        project_id=req.project_id,
        operational_life_years=operational_life_years,
        jurisdiction=jurisdiction_name,
        rail_type=req.rail_type,
        terrain=req.terrain,
        freight_quantity_gtk_per_year=req.freight_quantity_gtk_per_year,
        fuel_source=fuel_source,
        fuel_consumption_l_per_000gtk=fuel_consumption,
        fuel_kl=fuel_kl,
        emissions_intensity_tco2e_kl=emissions_intensity,
        emissions_annual_tco2e=emissions_annual,
        emissions_total_ref_period_tco2e=emissions_total,
    )
