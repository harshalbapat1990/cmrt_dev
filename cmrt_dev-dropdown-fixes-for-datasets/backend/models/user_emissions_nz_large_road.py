"""
models/user_emissions_nz_large_road.py

Stores per-year NZ large-project road user-emissions (B8) calculation results.

Table: user_emissions_nz_large_road_results
  One row per (project_option_id, vehicle_type, assessment_year).

Large-project difference vs. small (user_emissions_nz_results):
  - Vehicle type is explicit (separate rows per type instead of separate columns).
  - VKT and speed are interpolated/extrapolated server-side from user-supplied
    anchor years and stored here for audit purposes.
  - One API call per vehicle type; missing types produce no rows (no error).

Vehicle types accepted:
  general_fleet | light_vehicle | heavy_vehicle | bus

VEPM lookup: (dataset_revision_id, year, speed_kmh) → gCO2e/km
  — no road parameters (gradient/curvature/roughness) are used; NZ VEPM is
    speed-only, unlike the AUS fn_veh_emissions_intensity_aus function.
"""

import uuid as _uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class UserEmissionsNzLargeRoadResult(Base):
    __tablename__ = "user_emissions_nz_large_road_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=text("gen_random_uuid()"),
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

    # NZ vehicle type identifier
    vehicle_type = Column(String(50), nullable=False)

    # Calendar year this row covers
    assessment_year = Column(Integer, nullable=False)

    # Interpolated / extrapolated inputs stored for audit
    vkt_calc       = Column(Numeric(20, 6), nullable=True)
    speed_kph_calc = Column(Numeric(10, 4), nullable=True)

    # VEPM-derived intensity (gCO2e/km)
    emissions_intensity_gco2e_km = Column(Numeric(12, 6), nullable=True)

    # Annual emissions = VKT × intensity / 1,000,000 (tCO2e)
    emissions_tco2e = Column(Numeric(18, 6), nullable=True)

    created_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "project_option_id", "vehicle_type", "assessment_year",
            name="uq_nz_large_road_option_vehicle_year",
        ),
        Index("ix_nz_large_road_option_id",        "project_option_id"),
        Index("ix_nz_large_road_stage_instance_id", "project_stage_instance_id"),
    )
