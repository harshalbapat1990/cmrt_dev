from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class RenewableEnergyClassification(Base):
    __tablename__ = "renewable_energy_classifications"

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
    emissions_source = Column(String, nullable=False, index=True)
    classification = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    __table_args__ = (
        Index(
            "uq_rec_global_source",
            "emissions_source",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_rec_revision_source",
            "emissions_source",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NOT NULL"),
        ),
    )
