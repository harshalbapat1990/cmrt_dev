from sqlalchemy import Boolean, Column, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class OperationalEquipment(Base):
    __tablename__ = "operational_equipment"

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
    group_name = Column(String(255), nullable=False)
    item = Column(String(500), nullable=False)
    power_kw = Column(Numeric(12, 6), nullable=False)
    hours_per_day = Column(Numeric(8, 4), nullable=False)
    days_per_year = Column(Numeric(8, 4), nullable=False)
    source = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    __table_args__ = (
        Index(
            "uq_op_eq_global_item",
            "item",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL AND is_active = TRUE"),
        ),
        Index(
            "uq_op_eq_revision_item",
            "dataset_revision_id",
            "item",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL AND is_active = TRUE"),
        ),
    )
