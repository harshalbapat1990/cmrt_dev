"""add label column to units table

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the optional display label column
    op.add_column('units', sa.Column('label', sa.String(), nullable=True))

    # Populate labels for well-known unit codes
    op.execute("""
        UPDATE units SET label = CASE code
            -- Mass
            WHEN 'kg'   THEN 'kg'
            WHEN 't'    THEN 't'
            -- Length
            WHEN 'km'   THEN 'km'
            WHEN 'm'    THEN 'm'
            -- Area
            WHEN 'm2'   THEN 'm²'
            WHEN 'ha'   THEN 'ha'
            -- Volume
            WHEN 'm3'   THEN 'm³'
            WHEN 'L'    THEN 'L'
            WHEN 'kL'   THEN 'kL'
            WHEN 'ML'   THEN 'ML'
            -- Electrical energy
            WHEN 'W'    THEN 'W'
            WHEN 'J'    THEN 'J'
            WHEN 'Ws'   THEN 'Ws'
            WHEN 'Wh'   THEN 'Wh'
            WHEN 'kWh'  THEN 'kWh'
            WHEN 'MWh'  THEN 'MWh'
            WHEN 'GWh'  THEN 'GWh'
            -- Thermal energy
            WHEN 'kJ'   THEN 'kJ'
            WHEN 'MJ'   THEN 'MJ'
            WHEN 'GJ'   THEN 'GJ'
            -- Derived
            WHEN 'J/s'      THEN 'J/s'
            WHEN 't/item'   THEN 't/item'
            WHEN 't/each'   THEN 't/each'
            WHEN 't/m'      THEN 't/m'
            WHEN 't/tonne'  THEN 't/tonne'
            WHEN 't/t'      THEN 't/t'
            WHEN 't/week'   THEN 't/week'
            WHEN 't/litre'  THEN 't/litre'
            WHEN 't/m3'     THEN 't/m³'
            WHEN 't/kL'     THEN 't/kL'
            WHEN 'GJ/kL'    THEN 'GJ/kL'
            -- Emissions accounting
            WHEN 'tCO2e'            THEN 'tCO₂e'
            WHEN 'kgCO2e'           THEN 'kgCO₂e'
            WHEN 'gCO2e'            THEN 'gCO₂e'
            WHEN 'tCO2e/kWh'        THEN 'tCO₂e/kWh'
            WHEN 'kgCO2e/kWh'       THEN 'kgCO₂e/kWh'
            WHEN 'kgCO2e/km'        THEN 'kgCO₂e/km'
            WHEN 'tCO2e/km'         THEN 'tCO₂e/km'
            WHEN 'kgCO2e/L'         THEN 'kgCO₂e/L'
            WHEN 'tCO2e/MJ'         THEN 'tCO₂e/MJ'
            WHEN 'kgCO2e/MJ'        THEN 'kgCO₂e/MJ'
            WHEN 'tCO2e/GJ'         THEN 'tCO₂e/GJ'
            WHEN 'kgCO2e/GJ'        THEN 'kgCO₂e/GJ'
            WHEN 'gCO2e/km'         THEN 'gCO₂e/km'
            WHEN 'kg CO2e'          THEN 'kg CO₂e'
            WHEN 'g CO2e'           THEN 'g CO₂e'
            WHEN 'kg CO2e/km'       THEN 'kg CO₂e/km'
            WHEN 'kgCO2e/t.km'      THEN 'kgCO₂e/t·km'
            WHEN 'tCO2e/t.km'       THEN 'tCO₂e/t·km'
            -- Rates
            WHEN 'MJ/L'     THEN 'MJ/L'
            WHEN 'MJ/kg'    THEN 'MJ/kg'
            WHEN 'MJ/kWh'   THEN 'MJ/kWh'
            WHEN 'MJ/m3'    THEN 'MJ/m³'
            WHEN 'GJ/t'     THEN 'GJ/t'
            WHEN 'L/100km'  THEN 'L/100km'
            WHEN 'kWh/km'   THEN 'kWh/km'
            -- Benchmarks
            WHEN 'm2_gfa'             THEN 'm² GFA'
            WHEN 'lane_km'            THEN 'lane·km'
            WHEN 'aud_material_spend' THEN 'AUD material spend'
            WHEN 'm2_per_week'        THEN 'm²/week'
            WHEN 'each_per_week'      THEN 'each/week'
            -- Transport
            WHEN 'pkm'  THEN 'pkm'
            WHEN 'tkm'  THEN 'tkm'
            WHEN 'GTK'  THEN 'GTK'
            -- Density
            WHEN 't/m2'    THEN 't/m²'
            WHEN 't/kg'    THEN 't/kg'
            WHEN 't/bag'   THEN 't/bag'
            WHEN 't/metre' THEN 't/metre'
            WHEN 't/hour'  THEN 't/hour'
            WHEN 't/day'   THEN 't/day'
            WHEN 't/ea'    THEN 't/ea'
            WHEN 't/no'    THEN 't/no'
            WHEN 't/unit'  THEN 't/unit'
            WHEN 't/Unit'  THEN 't/Unit'
            ELSE NULL
        END
        WHERE code IN (
            'kg','t','km','m','m2','ha','m3','L','kL','ML',
            'W','J','Ws','Wh','kWh','MWh','GWh','kJ','MJ','GJ',
            'J/s','t/item','t/each','t/m','t/tonne','t/t','t/week','t/litre',
            't/m3','t/kL','GJ/kL',
            'tCO2e','kgCO2e','gCO2e',
            'tCO2e/kWh','kgCO2e/kWh','kgCO2e/km','tCO2e/km',
            'kgCO2e/L','tCO2e/MJ','kgCO2e/MJ','tCO2e/GJ','kgCO2e/GJ',
            'gCO2e/km','kg CO2e','g CO2e','kg CO2e/km',
            'kgCO2e/t.km','tCO2e/t.km',
            'MJ/L','MJ/kg','MJ/kWh','MJ/m3','GJ/t','L/100km','kWh/km',
            'm2_gfa','lane_km','aud_material_spend','m2_per_week','each_per_week',
            'pkm','tkm','GTK',
            't/m2','t/kg','t/bag','t/metre','t/hour','t/day','t/ea','t/no',
            't/unit','t/Unit'
        )
    """)


def downgrade() -> None:
    op.drop_column('units', 'label')
