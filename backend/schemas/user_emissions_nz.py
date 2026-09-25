"""
schemas/user_emissions_nz.py

Pydantic schemas for the NZ small-project user-emissions (B8) calculation.

Inputs (VKT, speeds) are passed directly to /calculate on every call —
they are NOT stored by the backend (the frontend stores them in activity_data).

Reference period is always derived from project.commencement_of_operations
and project.operational_life_years.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Per-year result (DB read)
# ─────────────────────────────────────────────────────────────────────────────

class UserEmissionsNzResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: UUID
    assessment_year: int

    general_fleet_intensity_gco2e_km: Optional[Decimal] = None
    light_vehicle_intensity_gco2e_km: Optional[Decimal] = None
    heavy_vehicle_intensity_gco2e_km: Optional[Decimal] = None
    bus_intensity_gco2e_km: Optional[Decimal] = None

    general_fleet_emissions_tco2e: Optional[Decimal] = None
    light_vehicle_emissions_tco2e: Optional[Decimal] = None
    heavy_vehicle_emissions_tco2e: Optional[Decimal] = None
    bus_emissions_tco2e: Optional[Decimal] = None

    total_annual_emissions_tco2e: Optional[Decimal] = None
    created_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# Calculation request / response
# ─────────────────────────────────────────────────────────────────────────────

class NzEmissionsCalculateRequest(BaseModel):
    """
    Trigger a full (re)calculation for one project option.

    Road Users inputs (VKT + average speed per vehicle type) are passed in on
    every call — the backend does NOT persist them (frontend owns that via
    activity_data).

    Reference period is always read from the project row:
      years = commencement_of_operations.year
              … commencement_of_operations.year + operational_life_years − 1

    base_case_emissions_tco2e:
      The interim absolute emissions of the base-case option (tCO2e), used to
      compute "Final user emissions = this option − base case".
      Pass None (or omit) when calculating the base-case option itself.
    """
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: UUID

    # Road Users inputs — passed in from activity_data / frontend each call
    general_fleet_vkt: Optional[Decimal] = None
    general_fleet_speed_kmh: Optional[Decimal] = None

    light_vehicle_vkt: Optional[Decimal] = None
    light_vehicle_speed_kmh: Optional[Decimal] = None

    heavy_vehicle_vkt: Optional[Decimal] = None
    heavy_vehicle_speed_kmh: Optional[Decimal] = None

    bus_vkt: Optional[Decimal] = None
    bus_speed_kmh: Optional[Decimal] = None

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_stage_instance_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_option_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "general_fleet_vkt": 1000000,
                "general_fleet_speed_kmh": 60,
                "light_vehicle_vkt": 800000,
                "light_vehicle_speed_kmh": 65,
                "heavy_vehicle_vkt": 200000,
                "heavy_vehicle_speed_kmh": 55,
                "bus_vkt": 150000,
                "bus_speed_kmh": 50,
            }
        }


class NzEmissionsAnnualRow(BaseModel):
    """One year's emissions for a single option."""
    assessment_year: int

    general_fleet_intensity_gco2e_km: Optional[Decimal] = None
    light_vehicle_intensity_gco2e_km: Optional[Decimal] = None
    heavy_vehicle_intensity_gco2e_km: Optional[Decimal] = None
    bus_intensity_gco2e_km: Optional[Decimal] = None

    general_fleet_emissions_tco2e: Optional[Decimal] = None
    light_vehicle_emissions_tco2e: Optional[Decimal] = None
    heavy_vehicle_emissions_tco2e: Optional[Decimal] = None
    bus_emissions_tco2e: Optional[Decimal] = None

    total_annual_emissions_tco2e: Optional[Decimal] = None


class NzEmissionsCalculateResponse(BaseModel):
    """
    Full calculation result for one project option.

    annual_rows                       — one entry per reference-period year
    interim_absolute_emissions_tco2e  — SUM(total_annual) across all years
                                        (Excel: "Interim absolute emissions for Option X")
    base_case_option_id               — the option marked as default (is_default=true)
    base_case_emissions_tco2e         — interim absolute emissions for the base case
    final_user_emissions_tco2e        — interim − base_case_emissions_tco2e
                                        (Excel: "Final user emissions for Option X")
                                        0 if option is itself the base case.
    """
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: UUID

    commencement_year: int
    operational_life_years: int

    interim_absolute_emissions_tco2e: Decimal
    base_case_option_id: UUID
    base_case_emissions_tco2e: Decimal
    final_user_emissions_tco2e: Decimal

    # Per-year breakdown — omitted from response for now; re-enable when needed
    annual_rows: List[NzEmissionsAnnualRow] = []


# ─────────────────────────────────────────────────────────────────────────────
# Summary (GET /summary — aggregate stored results for all options in a stage)
# ─────────────────────────────────────────────────────────────────────────────

class NzOptionSummary(BaseModel):
    project_option_id: UUID
    option_label: Optional[str] = None
    is_base_case: bool
    interim_absolute_emissions_tco2e: Optional[Decimal] = None
    # None for the base-case option itself
    final_user_emissions_tco2e: Optional[Decimal] = None


class NzEmissionsSummaryResponse(BaseModel):
    """
    Aggregates stored results for every option in a stage instance.
    final_user_emissions = option interim − base-case interim.
    """
    project_id: UUID
    project_stage_instance_id: UUID
    options: List[NzOptionSummary]
