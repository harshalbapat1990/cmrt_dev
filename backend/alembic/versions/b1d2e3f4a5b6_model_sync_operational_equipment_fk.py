"""Add ForeignKey constraint definition to operational_equipment model

Revision ID: b1d2e3f4a5b6
Revises: 644f003c0fa4
Create Date: 2026-04-22 00:00:00.000000

This migration is a NO-OP (no database changes required).

The operational_equipment table already has a ForeignKey constraint on 
dataset_revision_id (created in migration a2b3c4d5e6f7_add_operational_equipment.py).

This migration documents the update to the OperationalEquipment model to:
- Add the ForeignKey import
- Add ForeignKey constraint definition to dataset_revision_id column in the model

This ensures the SQLAlchemy model matches the actual database schema.

No SQL changes are needed as the database schema is already correct.
"""
from typing import Sequence, Union

revision: str = "b1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "644f003c0fa4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No database changes needed - model update only."""
    pass


def downgrade() -> None:
    """No database changes to revert."""
    pass
