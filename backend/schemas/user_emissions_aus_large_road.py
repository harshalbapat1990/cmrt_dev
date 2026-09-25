"""
schemas/user_emissions_aus_large_road.py

Pydantic schemas for the AUS large-project road user-emissions (B8) calculation.

Large-project difference vs. small:
  - User supplies VKT + average speed for SPECIFIC modelled years (anchor points).
  - The backend interpolates (between anchors) and extrapolates (beyond last anchor)
    to fill all years in the reference period.
  - User selects road parameters (gradient / curvature / roughness) explicitly.
  - All 20 ATAP vehicle classes are supported; one API call per vehicle type.
  - EV scenario is always "Step Change" (same as small projects).

Interpolation / extrapolation rules (matching Excel formulas):
  Before first anchor year : flat at first anchor values (carry-back)
  Between two anchors      : piecewise linear interpolation
  After last anchor year   : linear extrapolation from the last two anchors

If only one anchor year is supplied: flat value used for all reference period years.

Road parameter mappings (text → numeric for fn_veh_emissions_intensity_aus):
  gradient  : Flat=0, Rolling=40, Moderate=60, Hilly=80  (m/km)
  curvature : Straight=20, Gentle=40, Moderate=60, Curvy=80  (deg/km)
  roughness : Smooth=2.0, Average=4.0, Rough=6.0  (IRI m/km)
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Anchor year (user-supplied modelled year data point)
# ─────────────────────────────────────────────────────────────────────────────

class VehicleAnchorData(BaseModel):
    """Per-vehicle data within one anchor year."""
    vehicle_type:       str
    vkt:                Decimal
    average_speed_kph:  Decimal


class AnchorYear(BaseModel):
    """One user-entered modelled year with data for one or more vehicle types."""
    year:     int
    vehicles: List[VehicleAnchorData]


# ─────────────────────────────────────────────────────────────────────────────
# Calculation request (one vehicle type per call)
# ─────────────────────────────────────────────────────────────────────────────

class AusLargeRoadCalculateRequest(BaseModel):
    """
    Trigger a full (re)calculation for one or more vehicle types in an AUS large-project option.

    anchor_years:
        User-supplied data points — at least one year is required.
        Each anchor year contains a list of vehicles, each with vehicle_type, vkt, average_speed_kph.
        Years do not need to be in order; the service sorts them per vehicle type.

    gradient / curvature / roughness:
        Drop-down selections from the 'User emissions variables' sheet.
        Gradient  : Flat | Moderate | Steep | Very steep
        Curvature : Straight | Gently curved | Very winding
        Roughness : Very smooth | Smooth | Moderate | Rough | Very rough | Severely Rough

    vehicle_type:
        Must exactly match an ATAP VehicleClass in fn_veh_emissions_intensity_aus.
        Examples: Small Car | Medium Car | Large Car | Courier Van-Utility |
                  4WD Mid Size Petrol | Light Rigid | Medium Rigid | Heavy Rigid |
                  Heavy Bus | Artic 4 Axle | Artic 5 Axle | Artic 6 Axle |
                  Rigid + 5 Axle Dog | B-Double | Twin steer + 5 Axle Dog |
                  A-Double | B Triple | A B Combination | A-Triple | Double B-Double
    """

    project_id:               UUID
    project_stage_instance_id: UUID
    project_option_id:        UUID

    gradient:     str   # "Flat" | "Moderate" | "Steep" | "Very steep"
    curvature:    str   # "Straight" | "Gently curved" | "Very winding"
    roughness:    str   # "Very smooth" | "Smooth" | "Moderate" | "Rough" | "Very rough" | "Severely Rough"

    # EV uptake scenario — selectable from the front-end dropdown.
    # Defaults to "Step Change" if not supplied.
    ev_uptake_scenario: str = "Step Change"

    anchor_years: List[AnchorYear]

    @field_validator("anchor_years")
    @classmethod
    def at_least_one_anchor(cls, v: List[AnchorYear]) -> List[AnchorYear]:
        if not v:
            raise ValueError("anchor_years must contain at least one entry.")
        for ay in v:
            if not ay.vehicles:
                raise ValueError(
                    f"anchor_years entry for year {ay.year} must contain at least one vehicle."
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_stage_instance_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "project_option_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "gradient": "Flat",
                "curvature": "Straight",
                "roughness": "Smooth",
                "ev_uptake_scenario": "Step Change",
                "anchor_years": [
                    {
                        "year": 2038,
                        "vehicles": [
                            {"vehicle_type": "Small Car", "vkt": 11000, "average_speed_kph": 72},
                            {"vehicle_type": "Medium Car", "vkt": 11000, "average_speed_kph": 72},
                        ],
                    },
                    {
                        "year": 2045,
                        "vehicles": [
                            {"vehicle_type": "Small Car", "vkt": 13000, "average_speed_kph": 72},
                            {"vehicle_type": "Medium Car", "vkt": 13000, "average_speed_kph": 72},
                        ],
                    },
                ],
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Per-year result row (in response + DB read)
# ─────────────────────────────────────────────────────────────────────────────

class AusLargeRoadAnnualRow(BaseModel):
    assessment_year:              int
    vkt_calc:                     Decimal
    speed_kph_calc:               Decimal
    emissions_intensity_gco2e_vkt: Optional[Decimal] = None
    emissions_tco2e:              Optional[Decimal] = None


class VehicleTypeAnnualResult(BaseModel):
    """Annual rows for one vehicle type — part of a multi-vehicle response."""
    vehicle_type: str
    annual_rows:  List[AusLargeRoadAnnualRow] = []


# ─────────────────────────────────────────────────────────────────────────────
# Per-year DB result (read endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class UserEmissionsAusLargeRoadResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                           UUID
    project_id:                   UUID
    project_stage_instance_id:    UUID
    project_option_id:            UUID
    vehicle_type:                 str
    assessment_year:              int
    vkt_calc:                     Optional[Decimal] = None
    speed_kph_calc:               Optional[Decimal] = None
    gradient_m_per_km:            Optional[Decimal] = None
    curvature_deg_per_km:         Optional[Decimal] = None
    iri_m_per_km:                 Optional[Decimal] = None
    emissions_intensity_gco2e_vkt: Optional[Decimal] = None
    emissions_tco2e:              Optional[Decimal] = None
    created_at:                   Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# Calculation response
# ─────────────────────────────────────────────────────────────────────────────

class AusLargeRoadCalculateResponse(BaseModel):
    """
    Result for all submitted vehicle types, with option-level accumulated totals.

    interim_total_tco2e:
        Cumulative sum of emissions across ALL vehicle types submitted so far
        for this project option (re-read from DB after upsert).
        Matches the "Interim absolute emissions (tCO2e) for Option X" display.

    base_case_emissions_tco2e:
        Cumulative sum of emissions across ALL vehicle types for the base-case
        option (is_default=true). 0 when the base case has not been calculated yet.

    final_user_emissions_tco2e:
        interim_total_tco2e − base_case_emissions_tco2e.
        0 when the base case has not been calculated yet.
    """

    project_id:               UUID
    project_option_id:        UUID
    gradient:                 str
    curvature:                str
    roughness:                str
    ev_uptake_scenario:       str

    anchor_years:             List[AnchorYear]             = Field(default_factory=list)
    vehicle_results:          List[VehicleTypeAnnualResult] = Field(default_factory=list, exclude=True)

    interim_total_tco2e:         Decimal
    base_case_option_id:         Optional[UUID]    = None
    base_case_emissions_tco2e:   Decimal           = Decimal("0")
    final_user_emissions_tco2e:  Decimal           = Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# Summary response (all vehicle types for an option)
# ─────────────────────────────────────────────────────────────────────────────

class AusLargeRoadOptionSummary(BaseModel):
    project_option_id:             UUID
    interim_total_tco2e:           Decimal
    base_case_emissions_tco2e:     Optional[Decimal] = None
    final_user_emissions_tco2e:    Optional[Decimal] = None


class AusLargeRoadSummaryResponse(BaseModel):
    project_stage_instance_id: UUID
    options: List[AusLargeRoadOptionSummary]
