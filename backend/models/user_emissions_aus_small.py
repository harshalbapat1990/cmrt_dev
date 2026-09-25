import uuid as _uuid

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class UserEmissionsAusSmallResult(Base):
    """
    Per-year AUS small-project user-emissions (B8) results.

    One row per (project_option_id, assessment_year).

    The four frontend vehicle types map to these ATAP vehicle classes:
      Light vehicle       → Medium Car
      Medium vehicle      → Courier Van-Utility
      Heavy vehicle       → Heavy Rigid
      Super heavy vehicle → B-Double

    Intensities are derived from fn_veh_emissions_intensity_aus called with
    default road parameters (gradient=0, curvature=20, IRI=2.0) for small
    projects.  VKT/speed inputs are NOT stored here — they are owned by the
    frontend via activity_data.
    """

    __tablename__ = "user_emissions_aus_small_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    project_stage_instance_id = Column(UUID(as_uuid=True), ForeignKey("project_stage_instances.id", ondelete="CASCADE"), nullable=False)
    project_option_id = Column(UUID(as_uuid=True), ForeignKey("project_options.id", ondelete="CASCADE"), nullable=False)

    assessment_year = Column(Integer, nullable=False)

    # Emissions intensities (gCO2e/km) per vehicle type
    light_vehicle_intensity_gco2e_km        = Column(Numeric(20, 6), nullable=True)
    medium_vehicle_intensity_gco2e_km       = Column(Numeric(20, 6), nullable=True)
    heavy_vehicle_intensity_gco2e_km        = Column(Numeric(20, 6), nullable=True)
    super_heavy_vehicle_intensity_gco2e_km  = Column(Numeric(20, 6), nullable=True)

    # Annual emissions (tCO2e) per vehicle type
    light_vehicle_emissions_tco2e           = Column(Numeric(20, 10), nullable=True)
    medium_vehicle_emissions_tco2e          = Column(Numeric(20, 10), nullable=True)
    heavy_vehicle_emissions_tco2e           = Column(Numeric(20, 10), nullable=True)
    super_heavy_vehicle_emissions_tco2e     = Column(Numeric(20, 10), nullable=True)

    # Sum of all vehicle-type annual emissions
    total_annual_emissions_tco2e            = Column(Numeric(20, 10), nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "project_option_id",
            "assessment_year",
            name="uq_user_emissions_aus_small_results",
        ),
        Index("ix_user_emissions_aus_small_stage",  "project_stage_instance_id"),
        Index("ix_user_emissions_aus_small_option",  "project_option_id"),
    )
