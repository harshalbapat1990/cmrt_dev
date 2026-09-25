import uuid as _uuid

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class UserEmissionsAusLargeRoadResult(Base):
    """
    Per-year AUS large-project road user-emissions (B8) results.

    One row per (project_option_id, vehicle_type, assessment_year).

    Supports all 20 ATAP vehicle classes. VKT and speed are interpolated /
    extrapolated server-side from the user-supplied modelled-year anchor points.

    Road parameters (gradient, curvature, roughness) are stored per row because
    the user can supply different values per vehicle type for large projects.
    """

    __tablename__ = "user_emissions_aus_large_road_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    project_id = Column(
        UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False
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

    # Vehicle class exactly as returned by fn_veh_emissions_intensity_aus
    vehicle_type = Column(String(100), nullable=False)

    assessment_year = Column(Integer, nullable=False)

    # Interpolated / extrapolated inputs for this year
    vkt_calc            = Column(Numeric(20, 6), nullable=True)
    speed_kph_calc      = Column(Numeric(10, 4), nullable=True)

    # Road parameters (stored for audit; same across all years for one vehicle type)
    gradient_m_per_km     = Column(Numeric(10, 4), nullable=True)
    curvature_deg_per_km  = Column(Numeric(10, 4), nullable=True)
    iri_m_per_km          = Column(Numeric(10, 4), nullable=True)

    # Results
    emissions_intensity_gco2e_vkt = Column(Numeric(20, 6), nullable=True)
    emissions_tco2e               = Column(Numeric(20, 10), nullable=True)

    created_at = Column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "project_option_id", "vehicle_type", "assessment_year",
            name="uq_aus_large_road_option_vehicle_year",
        ),
        Index("ix_aus_large_road_option_id", "project_option_id"),
    )
