"""Preserve full precision in Australian large road calculation results.

Revision ID: auslr01_precision
Revises: 9ef9cc7aa311, rp01_seed_recurring_periods
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "auslr01_precision"
down_revision: Union[str, Sequence[str], None] = (
    "9ef9cc7aa311",
    "rp01_seed_recurring_periods",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = (
    "vkt_calc",
    "speed_kph_calc",
    "emissions_intensity_gco2e_vkt",
    "emissions_tco2e",
)
_LEGACY_TYPES = {
    "vkt_calc": sa.Numeric(20, 6),
    "speed_kph_calc": sa.Numeric(10, 4),
    "emissions_intensity_gco2e_vkt": sa.Numeric(20, 6),
    "emissions_tco2e": sa.Numeric(20, 10),
}


def upgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            "user_emissions_aus_large_road_results",
            column,
            existing_type=_LEGACY_TYPES[column],
            type_=sa.Numeric(),
            postgresql_using=f"{column}::numeric",
        )


def downgrade() -> None:
    for column, column_type in _LEGACY_TYPES.items():
        op.alter_column(
            "user_emissions_aus_large_road_results",
            column,
            existing_type=sa.Numeric(),
            type_=column_type,
            postgresql_using=f"{column}::{column_type.compile(dialect=op.get_bind().dialect)}",
        )
