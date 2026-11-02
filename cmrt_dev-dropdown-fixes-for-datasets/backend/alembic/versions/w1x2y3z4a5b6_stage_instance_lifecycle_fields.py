"""stage_instance_lifecycle_fields

Revision ID: w1x2y3z4a5b6
Revises: v1w2x3y4z5a6, i1j2k3l4m5n6
Create Date: 2026-03-27 00:00:00.000000

Merges two branches and adds stage instance lifecycle fields.

Add sequence, num_reports_required, frequency, technical_approved_at columns.
Expand approval_status values: open → draft | submitted | in_review | tech_approved | final_approved.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'w1x2y3z4a5b6'
down_revision: Union[str, Sequence[str], None] = ('v1w2x3y4z5a6', 'i1j2k3l4m5n6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('project_stage_instances', sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('project_stage_instances', sa.Column('num_reports_required', sa.Integer(), nullable=True))
    op.add_column('project_stage_instances', sa.Column('frequency', sa.String(length=20), nullable=True))
    op.add_column('project_stage_instances', sa.Column('technical_approved_at', sa.TIMESTAMP(), nullable=True))
    
    # Migrate existing 'open' status to 'draft'
    op.execute("UPDATE project_stage_instances SET approval_status = 'draft' WHERE approval_status = 'open'")
    
    # Update default value
    op.alter_column('project_stage_instances', 'approval_status', server_default='draft')


def downgrade() -> None:
    # Reverse status migration
    op.execute("UPDATE project_stage_instances SET approval_status = 'open' WHERE approval_status = 'draft'")
    op.alter_column('project_stage_instances', 'approval_status', server_default='open')
    
    # Drop columns
    op.drop_column('project_stage_instances', 'technical_approved_at')
    op.drop_column('project_stage_instances', 'frequency')
    op.drop_column('project_stage_instances', 'num_reports_required')
    op.drop_column('project_stage_instances', 'sequence')
