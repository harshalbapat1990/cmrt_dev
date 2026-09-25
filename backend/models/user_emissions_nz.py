"""
models/user_emissions_nz.py

Stores per-year NZ user-emissions (B8) calculation results.

  user_emissions_nz_results — one row per (project option, assessment year).

Inputs (VKT, speeds) are NOT stored here — they live in the activity_data
table managed by the frontend.  The frontend passes them directly to the
/calculate endpoint each time.

Reference period is derived from project.commencement_of_operations
and project.operational_life_years (NOT hardcoded to 50 years).

Interim absolute emissions  = SUM(total_annual_emissions_tco2e) for an option.
Final user emissions         = option interim − base-case interim.
"""

import uuid as _uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, Numeric, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class UserEmissionsNzResult(Base):
    __tablename__ = "user_emissions_nz_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_stage_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_option_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_options.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The calendar year this row covers (e.g. 2029, 2030, … 2078)
    assessment_year = Column(Integer, nullable=False)

    # ── Emissions intensity looked up from vepm_factors (gCO2e/km) ─────────────
    general_fleet_intensity_gco2e_km  = Column(Numeric(12, 6), nullable=True)
    light_vehicle_intensity_gco2e_km  = Column(Numeric(12, 6), nullable=True)
    heavy_vehicle_intensity_gco2e_km  = Column(Numeric(12, 6), nullable=True)
    bus_intensity_gco2e_km            = Column(Numeric(12, 6), nullable=True)

    # ── Annual emissions per vehicle type (tCO2e) — VKT × intensity / 10^6 ───
    general_fleet_emissions_tco2e = Column(Numeric(18, 6), nullable=True)
    light_vehicle_emissions_tco2e = Column(Numeric(18, 6), nullable=True)
    heavy_vehicle_emissions_tco2e = Column(Numeric(18, 6), nullable=True)
    bus_emissions_tco2e            = Column(Numeric(18, 6), nullable=True)

    # ── Sum of the vehicle-type annual emissions ─────────────────────────────
    total_annual_emissions_tco2e = Column(Numeric(18, 6), nullable=True)

    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "project_option_id", "assessment_year",
            name="uq_user_emissions_nz_results",
        ),
        Index("ix_uenz_results_stage", "project_stage_instance_id"),
        Index("ix_uenz_results_option", "project_option_id"),
    )
