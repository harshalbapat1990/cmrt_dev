"""
schemas/user_emissions_nz_large_road.py

Pydantic schemas for the NZ large-project road user-emissions (B8) calculation.

Large-project difference vs. small (user_emissions_nz.py):
  - User supplies VKT + speed for SPECIFIC modelled years (anchor points).
  - One or more NZ vehicle types may be submitted per call (single or multiple).
  - The backend interpolates between anchors and extrapolates beyond the last
    anchor to fill all reference-period years.
  - No road parameters (gradient/curvature/roughness) — NZ VEPM lookup uses
    only year and speed_kmh.

Interpolation / extrapolation rules (identical to AUS Large):
  Before first anchor year : flat at first anchor values (carry-back)
  Between two anchors      : piecewise linear interpolation
  After last anchor year   : linear extrapolation from the last two anchors

Vehicle types:  general_fleet | light_vehicle | heavy_vehicle | bus

Emission formula (per year, per vehicle type):
  emissions_tco2e = VKT × intensity_gco2e_km / 1,000,000
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Accepted vehicle type strings
# ---------------------------------------------------------------------------

NZ_LARGE_VEHICLE_TYPES = frozenset(
    {"general_fleet", "light_vehicle", "heavy_vehicle", "bus"}
)


# ---------------------------------------------------------------------------
# Anchor year (user-supplied modelled year data point)
# ---------------------------------------------------------------------------

class NzVehicleAnchorData(BaseModel):
    """Per-vehicle data within one anchor year."""
    vehicle_type: str   # "general_fleet" | "light_vehicle" | "heavy_vehicle" | "bus"
    vkt:          Decimal
    speed_kmh:    Decimal


class NzLargeRoadAnchorYear(BaseModel):
    """One user-entered modelled year with data for one or more NZ vehicle types."""
    year:     int
    vehicles: List[NzVehicleAnchorData]


# ---------------------------------------------------------------------------
# Calculation request
# ---------------------------------------------------------------------------

class NzLargeRoadCalculateRequest(BaseModel):
    """
    Trigger a full (re)calculation for one or more NZ vehicle types in a large-project option.

    anchor_years:
        User-supplied data points — at least one year required.
        Each anchor year contains a list of vehicles, each with vehicle_type, vkt, speed_kmh.
        A vehicle type may be absent from some anchor years as long as it appears in at least one.
        Years do not need to be in order; the service sorts them per vehicle type.

    Valid vehicle types: general_fleet | light_vehicle | heavy_vehicle | bus
    Missing vehicle types produce no rows (no error).

    Re-calling with the same option overwrites previous results for the submitted vehicle types.
    Other vehicle types' stored rows are unaffected.
    """

    project_id:                UUID
    project_stage_instance_id: UUID
    project_option_id:         UUID

    anchor_years: List[NzLargeRoadAnchorYear]

    @field_validator("anchor_years")
    @classmethod
    def validate_anchor_years(cls, v: List[NzLargeRoadAnchorYear]) -> List[NzLargeRoadAnchorYear]:
        if not v:
            raise ValueError("anchor_years must contain at least one entry.")
        for ay in v:
            if not ay.vehicles:
                raise ValueError(
                    f"anchor_years entry for year {ay.year} must contain at least one vehicle."
                )
            for vd in ay.vehicles:
                if vd.vehicle_type not in NZ_LARGE_VEHICLE_TYPES:
                    raise ValueError(
                        f"Unknown vehicle_type '{vd.vehicle_type}' in anchor year {ay.year}. "
                        f"Valid values: {sorted(NZ_LARGE_VEHICLE_TYPES)}"
                    )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_stage_instance_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_option_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "anchor_years": [
                    {
                        "year": 2038,
                        "vehicles": [
                            {"vehicle_type": "general_fleet", "vkt": 1000000, "speed_kmh": 60},
                            {"vehicle_type": "light_vehicle",  "vkt": 500000,  "speed_kmh": 65},
                        ],
                    },
                    {
                        "year": 2045,
                        "vehicles": [
                            {"vehicle_type": "general_fleet", "vkt": 1200000, "speed_kmh": 62},
                            {"vehicle_type": "light_vehicle",  "vkt": 600000,  "speed_kmh": 67},
                        ],
                    },
                ],
            }
        }


# ---------------------------------------------------------------------------
# Per-year result row (in calculate response)
# ---------------------------------------------------------------------------

class NzLargeRoadAnnualRow(BaseModel):
    assessment_year:              int
    vkt_calc:                     Decimal
    speed_kph_calc:               Decimal
    emissions_intensity_gco2e_km: Optional[Decimal] = None
    emissions_tco2e:              Optional[Decimal] = None


class NzVehicleTypeAnnualResult(BaseModel):
    """Annual rows for one NZ vehicle type — part of a multi-vehicle response."""
    vehicle_type: str
    annual_rows:  List[NzLargeRoadAnnualRow] = []


# ---------------------------------------------------------------------------
# Per-year DB result (GET /results endpoint)
# ---------------------------------------------------------------------------

class UserEmissionsNzLargeRoadResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                            UUID
    project_id:                    UUID
    project_stage_instance_id:     UUID
    project_option_id:             UUID
    vehicle_type:                  str
    assessment_year:               int
    vkt_calc:                      Optional[Decimal] = None
    speed_kph_calc:                Optional[Decimal] = None
    emissions_intensity_gco2e_km:  Optional[Decimal] = None
    emissions_tco2e:               Optional[Decimal] = None
    created_at:                    Optional[datetime] = None


# ---------------------------------------------------------------------------
# Calculation response
# ---------------------------------------------------------------------------

class NzLargeRoadCalculateResponse(BaseModel):
    """
    Result for all submitted vehicle types, with option-level accumulated totals.

    vehicle_results:
        Per-vehicle-type annual rows (excluded from JSON serialization).
        Use GET /results to retrieve stored per-year rows.

    interim_total_tco2e:
        Cumulative sum of emissions across ALL vehicle types stored so far
        for this project option (re-read from DB after upsert).

    base_case_emissions_tco2e:
        Cumulative sum across ALL vehicle types for the base-case option
        (is_default=true).  0 when the base case has not been calculated yet.

    final_user_emissions_tco2e:
        interim_total_tco2e − base_case_emissions_tco2e.
        0 when the base case has not been calculated yet.
    """

    project_id:                    UUID
    project_option_id:             UUID

    anchor_years: List[NzLargeRoadAnchorYear] = Field(default_factory=list)
    vehicle_results: List[NzVehicleTypeAnnualResult] = Field(default_factory=list, exclude=True)

    interim_total_tco2e:           Decimal
    base_case_option_id:           Optional[UUID]  = None
    base_case_emissions_tco2e:     Decimal         = Decimal("0")
    final_user_emissions_tco2e:    Decimal         = Decimal("0")


# ---------------------------------------------------------------------------
# Summary schemas (GET /summary)
# ---------------------------------------------------------------------------

class NzLargeRoadOptionSummary(BaseModel):
    project_option_id:             UUID
    interim_total_tco2e:           Optional[Decimal] = None
    base_case_emissions_tco2e:     Optional[Decimal] = None
    final_user_emissions_tco2e:    Optional[Decimal] = None


class NzLargeRoadSummaryResponse(BaseModel):
    """
    Aggregated totals (across all vehicle types) per option in a stage instance.
    """
    project_stage_instance_id: UUID
    options: List[NzLargeRoadOptionSummary]
