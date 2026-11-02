"""
schemas/user_emissions_aus_small.py

Pydantic schemas for the AUS small-project user-emissions (B8) calculation.

Frontend vehicle types (4) map to ATAP vehicle classes:
  Light vehicle       → Medium Car           (VEPM equivalent: light)
  Medium vehicle      → Courier Van-Utility  (VEPM equivalent: medium)
  Heavy vehicle       → Heavy Rigid          (VEPM equivalent: heavy rigid)
  Super heavy vehicle → B-Double             (VEPM equivalent: articulated)

Road parameters are fixed defaults for small projects:
  gradient_m_per_km   = 0
  curvature_deg_per_km = 20
  iri_m_per_km        = 2.0

VKT and speed inputs are passed in on every call — NOT stored by the backend
(the frontend stores them in activity_data).

Reference period is derived from project.commencement_of_operations +
project.operational_life_years (same as NZ).
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Per-year result (DB read)
# ─────────────────────────────────────────────────────────────────────────────

class UserEmissionsAusSmallResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: UUID
    assessment_year: int

    light_vehicle_intensity_gco2e_km:       Optional[Decimal] = None
    medium_vehicle_intensity_gco2e_km:      Optional[Decimal] = None
    heavy_vehicle_intensity_gco2e_km:       Optional[Decimal] = None
    super_heavy_vehicle_intensity_gco2e_km: Optional[Decimal] = None

    light_vehicle_emissions_tco2e:          Optional[Decimal] = None
    medium_vehicle_emissions_tco2e:         Optional[Decimal] = None
    heavy_vehicle_emissions_tco2e:          Optional[Decimal] = None
    super_heavy_vehicle_emissions_tco2e:    Optional[Decimal] = None

    total_annual_emissions_tco2e:           Optional[Decimal] = None
    created_at:                             Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# Calculation request
# ─────────────────────────────────────────────────────────────────────────────

class AusSmallEmissionsCalculateRequest(BaseModel):
    """
    Trigger a full (re)calculation for one AUS small-project option.

    Road Users inputs (VKT + average speed per vehicle type) are passed in on
    every call — the backend does NOT persist them.

    The Australian state / grid region is resolved automatically from:
      project.proponent_org_id → organization.region_id → jurisdictions.name

    base_case_emissions_tco2e:
      The interim absolute emissions of the base-case option (tCO2e).
      Pass None when calculating the base case itself.
    """
    project_id:              UUID
    project_stage_instance_id: UUID
    project_option_id:       UUID

    # Note: EV uptake scenario is always "Step Change" for small projects (not a user input)

    # Light vehicle (→ Medium Car)
    light_vehicle_vkt:       Optional[Decimal] = None
    light_vehicle_speed_kmh: Optional[Decimal] = None

    # Medium vehicle (→ Courier Van-Utility)
    medium_vehicle_vkt:       Optional[Decimal] = None
    medium_vehicle_speed_kmh: Optional[Decimal] = None

    # Heavy vehicle (→ Heavy Rigid)
    heavy_vehicle_vkt:       Optional[Decimal] = None
    heavy_vehicle_speed_kmh: Optional[Decimal] = None

    # Super heavy vehicle (→ B-Double)
    super_heavy_vehicle_vkt:       Optional[Decimal] = None
    super_heavy_vehicle_speed_kmh: Optional[Decimal] = None

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_stage_instance_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_option_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "light_vehicle_vkt": 50000,
                "light_vehicle_speed_kmh": 52,
                "medium_vehicle_vkt": 20000,
                "medium_vehicle_speed_kmh": 52,
                "heavy_vehicle_vkt": 30000,
                "heavy_vehicle_speed_kmh": 52,
                "super_heavy_vehicle_vkt": 40000,
                "super_heavy_vehicle_speed_kmh": 52,
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Annual row in the calculation response
# ─────────────────────────────────────────────────────────────────────────────

class AusSmallEmissionsAnnualRow(BaseModel):
    year: int

    light_vehicle_intensity_gco2e_km:       Optional[Decimal] = None
    medium_vehicle_intensity_gco2e_km:      Optional[Decimal] = None
    heavy_vehicle_intensity_gco2e_km:       Optional[Decimal] = None
    super_heavy_vehicle_intensity_gco2e_km: Optional[Decimal] = None

    light_vehicle_emissions_tco2e:          Optional[Decimal] = None
    medium_vehicle_emissions_tco2e:         Optional[Decimal] = None
    heavy_vehicle_emissions_tco2e:          Optional[Decimal] = None
    super_heavy_vehicle_emissions_tco2e:    Optional[Decimal] = None

    total_annual_emissions_tco2e:           Optional[Decimal] = None


# ─────────────────────────────────────────────────────────────────────────────
# Calculation response
# ─────────────────────────────────────────────────────────────────────────────

class AusSmallEmissionsCalculateResponse(BaseModel):
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
    annual_rows: List[AusSmallEmissionsAnnualRow] = []


# ─────────────────────────────────────────────────────────────────────────────
# Summary (one row per option in a stage instance)
# ─────────────────────────────────────────────────────────────────────────────

class AusSmallOptionSummary(BaseModel):
    project_option_id:             UUID
    option_label:                  Optional[str]     = None
    is_base_case:                  bool              = False
    interim_total_emissions_tco2e: Optional[Decimal] = None
    final_user_emissions_tco2e:    Optional[Decimal] = None


class AusSmallEmissionsSummaryResponse(BaseModel):
    project_id:                UUID
    project_stage_instance_id: UUID
    options:                   List[AusSmallOptionSummary]
