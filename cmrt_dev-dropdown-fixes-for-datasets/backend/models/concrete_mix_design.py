from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base, TimestampMixin

INPUT_COMPONENT_DEFINITIONS: list[tuple[str, str, int]] = [
    ("total_cementitious_content", "Total cementitious content",       10),
    ("silica_fume",                "Silica Fume",                      50),
    ("fine_aggregates",            "Fine Aggregates",                  60),
    ("coarse_aggregates",          "Coarse Aggregates",                70),
    ("recycled_aggregates",        "Recycled Aggregates",              80),
    ("manufactured_sand",          "Manufactured sand",                90),
    ("mains_water",                "Mains Water",                     100),
    ("onsite_recycled_water",      "Onsite Recycled / Captured Water", 110),
    ("admixture",                  "Admixture",                       120),
]

CALCULATED_COMPONENT_DEFINITIONS: list[tuple[str, str, int]] = [
    ("general_purpose_cement", "General purpose cement", 20),
    ("fly_ash",                "Fly ash",                30),
    ("ggbf_slag",              "GGBF slag",              40),
]

ALL_COMPONENT_DEFINITIONS: list[tuple[str, str, int]] = sorted(
    INPUT_COMPONENT_DEFINITIONS + CALCULATED_COMPONENT_DEFINITIONS,
    key=lambda x: x[2],
)

TOTAL_CEMENTITIOUS_CODE = "total_cementitious_content"

CALCULATED_COMPONENT_CODES: frozenset[str] = frozenset(
    code for code, _, _ in CALCULATED_COMPONENT_DEFINITIONS
)

STRENGTH_FIELDS: tuple[str, ...] = (
    "strength_20_kg_m3",
    "strength_25_kg_m3",
    "strength_32_kg_m3",
    "strength_40_kg_m3",
    "strength_50_kg_m3",
    "strength_65_kg_m3",
    "strength_80_kg_m3",
    "strength_100_kg_m3",
)


class ConcreteMixAssumption(Base, TimestampMixin):
    __tablename__ = "concrete_mix_assumptions"

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

    bau_scm_content_pct = Column(Numeric(6, 4), nullable=False, server_default=text("0"))
    default_max_fly_ash_pct = Column(Numeric(6, 4), nullable=False, server_default=text("0.30"))

    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    __table_args__ = (
        Index(
            "uq_concrete_mix_assumptions_global",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL AND is_active = TRUE"),
        ),
        Index(
            "uq_concrete_mix_assumptions_revision",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL AND is_active = TRUE"),
        ),
    )


class ConcreteMixDesign(Base, TimestampMixin):
    __tablename__ = "concrete_mix_designs"

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

    component_code = Column(String(64), nullable=False)
    component_label = Column(String(255), nullable=False)
    display_order = Column(Integer, nullable=False, server_default=text("0"))

    strength_20_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_25_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_32_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_40_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_50_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_65_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_80_kg_m3 = Column(Numeric(12, 4), nullable=True)
    strength_100_kg_m3 = Column(Numeric(12, 4), nullable=True)

    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    __table_args__ = (
        Index(
            "uq_concrete_mix_designs_global_component",
            "component_code",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL AND is_active = TRUE"),
        ),
        Index(
            "uq_concrete_mix_designs_revision_component",
            "dataset_revision_id",
            "component_code",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL AND is_active = TRUE"),
        ),
    )
