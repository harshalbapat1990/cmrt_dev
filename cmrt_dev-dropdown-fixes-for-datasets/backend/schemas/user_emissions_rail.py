"""
schemas/user_emissions_rail.py

Pydantic schemas for the Rail user-emissions (B8) calculation.

One API call per row (one rail type / terrain / freight quantity combination).
Applies to both AUS and NZ projects. Jurisdiction is resolved server-side
from the project's proponent organisation region.

Train types (as stored in freight_rail_factors):
  Container Train | General purpose train | Grain train | Heavy haul mineral

Terrain values: Flat | Curvy | Hilly | Mountain

Excel output columns mapped to response fields:
  Diesel fuel consumption (L per thousand GTK)          → fuel_consumption_l_per_000gtk
  Diesel fuel (kL)                                      → fuel_kl
  Diesel emissions intensity (tCO2e/kL)                 → emissions_intensity_tco2e_kl
  Diesel emissions (tCO2e)                              → emissions_annual_tco2e
  Diesel emissions - total reference period (tCO2e)     → emissions_total_ref_period_tco2e
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────────────────
# Calculation request  (one row at a time)
# ─────────────────────────────────────────────────────────────────────────────

class RailEmissionsCalculateRequest(BaseModel):
    """
    Single-row rail user-emissions calculation request.

    freight_quantity_gtk_per_year:
        Freight quantity in actual GTK/year (e.g. 45000000 for 45,000,000 GTK/year).
        Matches the Excel column "Freight quantity (GTK/year)".

    rail_type must match train_type values stored in freight_rail_factors:
        Container Train | General purpose train | Grain train | Heavy haul mineral
    """

    project_id: UUID
    rail_type: str
    terrain: str
    freight_quantity_gtk_per_year: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "rail_type": "Container Train",
                "terrain": "Flat",
                "freight_quantity_gtk_per_year": 45000000,
                "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Calculation response  (flat, one row)
# ─────────────────────────────────────────────────────────────────────────────

class RailEmissionsCalculateResponse(BaseModel):
    # ── Project parameters ───────────────────────────────────────────────────
    project_id: UUID
    operational_life_years: int
    jurisdiction: str

    # ── Inputs echoed back ───────────────────────────────────────────────────
    rail_type: str
    terrain: str
    freight_quantity_gtk_per_year: Decimal

    # ── Supporting / lookup fields ───────────────────────────────────────────
    # Fuel type used for EF lookup (supporting field, not displayed as output)
    fuel_source: str   # "Diesel oil" (AUS) or "Diesel" (NZ)

    # ── Calculated outputs (Excel column names, fuel-type prefix removed) ────
    # Diesel fuel consumption (L per thousand GTK)
    fuel_consumption_l_per_000gtk: Decimal
    # Diesel fuel (kL)
    fuel_kl: Decimal
    # Diesel emissions intensity (tCO2e/kL)
    emissions_intensity_tco2e_kl: Decimal
    # Diesel emissions (tCO2e)
    emissions_annual_tco2e: Decimal
    # Diesel emissions - total reference period (tCO2e)
    emissions_total_ref_period_tco2e: Decimal
