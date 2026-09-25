import uuid as _uuid

from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class EmissionsResult(Base):
    __tablename__ = "emissions_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())

    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    project_stage_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
        nullable=False,
    )

    activity_data_id = Column(
        UUID(as_uuid=True),
        ForeignKey("activity_data.id", ondelete="CASCADE"),
        nullable=False,
    )

    value_key = Column(String(50), nullable=False)

    lifecycle_module_code = Column(String, ForeignKey("lifecycle_modules.code"), nullable=True)

    is_supplementary = Column(Boolean, nullable=False, default=False, server_default="FALSE")

    value = Column(Numeric, nullable=False)
    unit_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "activity_data_id", "value_key",
            name="emissions_results_activity_value_key",
        ),
    )
