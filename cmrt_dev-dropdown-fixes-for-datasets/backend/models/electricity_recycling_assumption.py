from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from core.base import Base, TimestampMixin


class ElectricityRecyclingAssumption(Base, TimestampMixin):
    """BAU electricity and recycling assumption rows per jurisdiction and dataset revision."""

    __tablename__ = "electricity_recycling_assumptions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=func.gen_random_uuid(),
    )
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    metric_code = Column(String(64), nullable=False)
    metric_label = Column(Text, nullable=False)
    default_bau_pct = Column(Numeric(8, 6), nullable=False, server_default=text("0"))
    is_calculated = Column(Boolean, nullable=False, server_default=text("false"))
    display_order = Column(Integer, nullable=False, server_default=text("0"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    jurisdiction = relationship("Jurisdiction", lazy="joined")

    __table_args__ = (
        Index(
            "uq_electricity_recycling_assumptions_global",
            "jurisdiction_id",
            "metric_code",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL AND is_active = TRUE"),
        ),
        Index(
            "uq_electricity_recycling_assumptions_revision",
            "dataset_revision_id",
            "jurisdiction_id",
            "metric_code",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL AND is_active = TRUE"),
        ),
        Index(
            "ix_electricity_recycling_assumptions_jur_order",
            "dataset_revision_id",
            "jurisdiction_id",
            "display_order",
        ),
    )
