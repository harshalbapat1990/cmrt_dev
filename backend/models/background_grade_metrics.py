import uuid as _uuid
from sqlalchemy import Boolean, Column, Numeric, SmallInteger, String, Text, TIMESTAMP
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class BackgroundGradeMetric(Base):
    __tablename__ = "background_grade_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    grade_id = Column(SmallInteger, ForeignKey("grade_definitions.id"), nullable=False)
    jurisdiction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id"),
        nullable=True,
    )
    mastertype_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_mastertypes.id"), nullable=True)
    typecast_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_typecasts.id"), nullable=True)
    emissions_category_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=True)
    emissions_subcategory_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=True)
    emissions_source = Column(String, nullable=True)
    lifecycle_module_code = Column(String, ForeignKey("lifecycle_modules.code"), nullable=True)
    ghg_scope_id = Column(SmallInteger, ForeignKey("ghg_scopes.id"), nullable=True)
    metric_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("metric_types.id"),
        nullable=False,
    )
    band_code = Column(String, ForeignKey("value_bands.code"), nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    value = Column(Numeric, nullable=True)
    assumed_quantity_default = Column(Numeric, nullable=True)
    source = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
