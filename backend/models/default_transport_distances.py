from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class DefaultTransportDistance(Base):
    __tablename__ = "default_transport_distances"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    emissions_category_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)

    truck_distance = Column(Numeric, nullable=True)
    rail_distance = Column(Numeric, nullable=True)
    sea_distance = Column(Numeric, nullable=True)
    distance_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)

    truck_transport_mode = Column(String, nullable=True)
    rail_transport_mode = Column(String, nullable=True)
    sea_transport_mode = Column(String, nullable=True)

    source = Column(Text, nullable=True)
    grade_applicability = Column(String, nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(material_id, emissions_category_id) = 1",
            name="chk_dtd_exactly_one_key",
        ),
        Index(
            "uq_dtd_global_category",
            "jurisdiction_id", "emissions_category_id",
            unique=True,
            postgresql_where=text(
                "emissions_category_id IS NOT NULL AND is_active = TRUE "
                "AND dataset_revision_id IS NULL"
            ),
        ),
        Index(
            "uq_dtd_global_material",
            "jurisdiction_id", "material_id",
            unique=True,
            postgresql_where=text(
                "material_id IS NOT NULL AND is_active = TRUE "
                "AND dataset_revision_id IS NULL"
            ),
        ),
        Index(
            "uq_dtd_revision_category",
            "jurisdiction_id", "emissions_category_id", "dataset_revision_id",
            unique=True,
            postgresql_where=text(
                "emissions_category_id IS NOT NULL AND is_active = TRUE "
                "AND dataset_revision_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_dtd_revision_material",
            "jurisdiction_id", "material_id", "dataset_revision_id",
            unique=True,
            postgresql_where=text(
                "material_id IS NOT NULL AND is_active = TRUE "
                "AND dataset_revision_id IS NOT NULL"
            ),
        ),
    )
