"""added new table concrete_mix_production

Revision ID: 9ef9cc7aa311
Revises: cr01_concrete_register
Create Date: 2026-05-04 22:13:06.780203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '9ef9cc7aa311'
down_revision: Union[str, Sequence[str], None] = 'cr01_concrete_register'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Seed data (from AusLCI Concrete Unit Processes / NGA 2025) ─────────────
_SEED_ROWS = [
    {
        "emissions_source": "Diesel",
        "use_per_m3": 22.7,
        "units": "MJ",
        "ef_kgco2e_per_unit": 0.08771,
        "emissions_kgco2e_m3": 1.991017,
        "use_source": (
            "AusLCI Concrete Unit Processes - Diesel, burned in building machine"
            "/GLO U/AusSD/Link U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 1,
    },
    {
        "emissions_source": "Electricity from national grid",
        "use_per_m3": 4.36,
        "units": "kWh",
        "ef_kgco2e_per_unit": 0.69,
        "emissions_kgco2e_m3": 3.0084,
        "use_source": (
            "AusLCI Concrete Unit Processes - electricity, low voltage, Australian"
            "/AU U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 2,
    },
    {
        "emissions_source": "Heavy fuel oil",
        "use_per_m3": 3.09,
        "units": "MJ",
        "ef_kgco2e_per_unit": 0.0916,
        "emissions_kgco2e_m3": 0.283044,
        "use_source": (
            "AusLCI Concrete Unit Processes - Heavy fuel oil, burned in industrial"
            " furnace 1MW, non-modulating/CH U/AusSD U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 3,
    },
    {
        "emissions_source": "Light fuel oil",
        "use_per_m3": 13.3,
        "units": "MJ",
        "ef_kgco2e_per_unit": 0.0916,
        "emissions_kgco2e_m3": 1.21828,
        "use_source": (
            "AusLCI Concrete Unit Processes - Light fuel oil, burned in industrial"
            " furnace 1MW, non-modulating/CH U/AusSD U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 4,
    },
    {
        "emissions_source": "Lubricating oil",
        "use_per_m3": 0.0119,
        "units": "kg",
        "ef_kgco2e_per_unit": 0.0319,
        "emissions_kgco2e_m3": 0.00037961,
        "use_source": (
            "AusLCI Concrete Unit Processes - Lubricating oil, at plant/RER U/AusSD U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 5,
    },
    {
        "emissions_source": "Natural gas distributed in a pipeline",
        "use_per_m3": 1.16,
        "units": "MJ",
        "ef_kgco2e_per_unit": 0.0654,
        "emissions_kgco2e_m3": 0.075864,
        "use_source": (
            "AusLCI Concrete Unit Processes - natural gas, burned in tangential"
            " fired boiler /AU U"
        ),
        "ef_source": "NGA 2025, as per Sheet 1.3 Fuel EFs and Conversion",
        "sort_order": 6,
    },
    {
        "emissions_source": "Wastewater treatment of concrete production effluent",
        "use_per_m3": 0.0143,
        "units": "m3",
        "ef_kgco2e_per_unit": 1.8564666,
        "emissions_kgco2e_m3": 0.026547472,
        "use_source": (
            "AusLCI Concrete Unit Processes - Treatment, concrete production"
            " effluent, to wastewater treatment, class 3/CH U/AusSD U"
        ),
        "ef_source": "AusLCI 1.45 (2025) - water and wastewater",
        "sort_order": 7,
    },
    {
        "emissions_source": "Disposal, concrete, 5% water, to inert material landfill",
        "use_per_m3": 16.9,
        "units": "kg",
        "ef_kgco2e_per_unit": 0.014333333,
        "emissions_kgco2e_m3": 0.242233333,
        "use_source": (
            "AusLCI Concrete Unit Processes - Disposal, concrete, 5% water,"
            " to inert material landfill/CH U/AusSD U"
        ),
        "ef_source": (
            "NABERS National Emission Factor Database v2025.1 (2025) - inert rubble,"
            " as per Sheet 1.6 Waste treatment Efs"
        ),
        "sort_order": 8,
    },
    {
        "emissions_source": "Waste treatment of inert waste at landfill",
        "use_per_m3": 0.0951,
        "units": "kg",
        "ef_kgco2e_per_unit": 0.014333333,
        "emissions_kgco2e_m3": 0.0013631,
        "use_source": (
            "AusLCI Concrete Unit Processes - waste treatment, inert waste,"
            " at landfill/AU U"
        ),
        "ef_source": (
            "NABERS National Emission Factor Database v2025.1 (2025) - inert rubble,"
            " as per Sheet 1.6 Waste treatment Efs"
        ),
        "sort_order": 9,
    },
]

def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    production_table = op.create_table(
        "concrete_mix_production",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("emissions_source", sa.String(300), nullable=False),
        sa.Column("use_per_m3", sa.Numeric(14, 6), nullable=False),
        sa.Column("units", sa.String(20), nullable=False),
        sa.Column("ef_kgco2e_per_unit", sa.Numeric(14, 8), nullable=False),
        # Pre-computed: use_per_m3 × ef_kgco2e_per_unit
        sa.Column("emissions_kgco2e_m3", sa.Numeric(14, 8), nullable=False),
        sa.Column("use_source", sa.Text(), nullable=True),
        sa.Column("ef_source", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_on",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_on", sa.TIMESTAMP(timezone=False), nullable=True),
    )

    # Seed the 9 production-stage EF rows
    op.bulk_insert(
        production_table,
        [
            {**row, "is_active": True}
            for row in _SEED_ROWS
        ],
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("concrete_mix_production")
    # ### end Alembic commands ###
