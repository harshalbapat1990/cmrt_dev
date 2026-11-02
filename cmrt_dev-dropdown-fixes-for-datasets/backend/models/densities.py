from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.base import Base

from models.jurisdictions import Jurisdiction
from models.dataset_revisions import DatasetRevision
from models.emissions_categories_new import EmissionsCategoryRecord
from models.units import Unit


class Density(Base):
    __tablename__ = "densities"

    id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=func.gen_random_uuid(),
    )

    dataset_revision_id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    jurisdiction_id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("jurisdictions.id"),
        nullable=False,
    )

    dataset: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    record_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    emissions_category_id: Mapped[UUID | None] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("emissions_categories.id"),
        nullable=True,
    )

    emissions_sub_category_id: Mapped[UUID | None] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("emissions_categories.id"),
        nullable=True,
    )

    emissions_source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    density: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    unit_id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("units.id"),
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    jurisdiction: Mapped["Jurisdiction | None"] = relationship(
        "Jurisdiction",
        foreign_keys=[jurisdiction_id],
        lazy="selectin",
    )

    dataset_revision: Mapped["DatasetRevision | None"] = relationship(
        "DatasetRevision",
        foreign_keys=[dataset_revision_id],
        lazy="selectin",
    )

    emissions_category: Mapped["EmissionsCategoryRecord | None"] = relationship(
        "EmissionsCategoryRecord",
        foreign_keys=[emissions_category_id],
        primaryjoin="Density.emissions_category_id==EmissionsCategoryRecord.id",
        lazy="selectin",
    )

    emissions_sub_category: Mapped["EmissionsCategoryRecord | None"] = relationship(
        "EmissionsCategoryRecord",
        foreign_keys=[emissions_sub_category_id],
        primaryjoin="Density.emissions_sub_category_id==EmissionsCategoryRecord.id",
        lazy="selectin",
    )

    unit: Mapped["Unit"] = relationship(
        "Unit",
        foreign_keys=[unit_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "uq_densities_revision_key",
            "jurisdiction_id",
            "dataset",
            "record_key",
            "unit_id",
            "dataset_revision_id",
            unique=True,
        ),
    )
