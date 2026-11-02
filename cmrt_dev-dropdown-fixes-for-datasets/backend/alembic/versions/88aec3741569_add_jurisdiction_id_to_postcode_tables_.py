"""Add jurisdiction_id to postcode tables and RURAL area

Revision ID: 88aec3741569
Revises: abcd1234ef56
Create Date: 2026-04-13 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '88aec3741569'
down_revision: Union[str, Sequence[str], None] = 'abcd1234ef56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add jurisdiction_id to postcode tables."""
    # Add RURAL to area_class enum
    op.execute("ALTER TYPE area_class ADD VALUE 'RURAL' AFTER 'REMOTE'")
    
    # Add jurisdiction_id to postcode_reference (nullable)
    op.add_column('postcode_reference', 
        sa.Column('jurisdiction_id', sa.UUID(), nullable=True))
    
    # Create FK constraint for postcode_reference
    op.create_foreign_key(
        op.f('fk__postcode_reference__jurisdiction_id__jurisdictions'),
        'postcode_reference', 'jurisdictions',
        ['jurisdiction_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Drop old unique constraint and create composite one
    op.drop_constraint(op.f('uq_postcode_reference_postcode'), 
                       'postcode_reference', type_='unique')
    op.create_unique_constraint(
        'uq_postcode_jurisdiction',
        'postcode_reference',
        ['postcode', 'jurisdiction_id']
    )
    
    # Add jurisdiction_id to project_postcode (nullable)
    op.add_column('project_postcode', 
        sa.Column('jurisdiction_id', sa.UUID(), nullable=True))
    
    # Create FK constraint for project_postcode
    op.create_foreign_key(
        op.f('fk__project_postcode__jurisdiction_id__jurisdictions'),
        'project_postcode', 'jurisdictions',
        ['jurisdiction_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema - Remove jurisdiction_id from postcode tables."""
    # Remove FK constraint from project_postcode
    op.drop_constraint(
        op.f('fk__project_postcode__jurisdiction_id__jurisdictions'),
        'project_postcode',
        type_='foreignkey'
    )
    
    # Remove jurisdiction_id column from project_postcode
    op.drop_column('project_postcode', 'jurisdiction_id')
    
    # Remove composite unique constraint from postcode_reference
    op.drop_constraint('uq_postcode_jurisdiction', 
                       'postcode_reference', type_='unique')
    
    # Restore original unique constraint
    op.create_unique_constraint(
        op.f('uq_postcode_reference_postcode'),
        'postcode_reference',
        ['postcode']
    )
    
    # Remove FK constraint from postcode_reference
    op.drop_constraint(
        op.f('fk__postcode_reference__jurisdiction_id__jurisdictions'),
        'postcode_reference',
        type_='foreignkey'
    )
    
    # Remove jurisdiction_id column from postcode_reference
    op.drop_column('postcode_reference', 'jurisdiction_id')
    
    # Remove RURAL from area_class enum (PostgreSQL doesn't support this easily,
    # so we'll just leave it. It's safe to have extra enum values)


