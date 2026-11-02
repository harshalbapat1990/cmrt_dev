"""Add new tables and schema changes - FIXED

Revision ID: 3f7c4b74bdb4
Revises: 06e08714f169
Create Date: 2026-01-28 21:13:11.547827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3f7c4b74bdb4'
down_revision: Union[str, Sequence[str], None] = '06e08714f169'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ========================================================================================
    # STEP 1: Create ENUM types using raw SQL with proper PostgreSQL idempotency
    # ========================================================================================
    # Using PostgreSQL DO blocks that catch duplicate_object exceptions
    op.execute("""
    DO $$ BEGIN
      CREATE TYPE project_class AS ENUM ('SMALL', 'LARGE', 'RECURRING');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
      CREATE TYPE area_class AS ENUM ('METROPOLITAN', 'REGIONAL', 'REMOTE');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
      CREATE TYPE org_role AS ENUM ('PROPONENT', 'DESIGNER', 'DELIVERY');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
      CREATE TYPE project_stage AS ENUM ('BUSINESS_CASE', 'DESIGN', 'CONSTRUCTION');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
    DO $$ BEGIN
      CREATE TYPE report_frequency AS ENUM ('MONTHLY', 'QUARTERLY', 'BI_MONTHLY', 'ANNUAL');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    # ========================================================================================
    # STEP 2: Create new tables
    # ========================================================================================
    op.create_table(
        'organization',
        sa.Column('organization_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_on', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('organization_id', name=op.f('pk__organization')),
        sa.UniqueConstraint('name', name=op.f('uq__organization__name')),
    )

    op.create_table(
        'postcode_reference',
        sa.Column('postcode_reference_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('postcode', sa.String(length=10), nullable=False),
        sa.Column('area_class', postgresql.ENUM('METROPOLITAN', 'REGIONAL', 'REMOTE', name='area_class', create_type=False), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('postcode_reference_id', name=op.f('pk__postcode_reference')),
        sa.UniqueConstraint('postcode', name='uq_postcode_reference_postcode'),
    )

    op.create_table(
        'project_type',
        sa.Column('project_type_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_on', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('project_type_id', name=op.f('pk__project_type')),
        sa.UniqueConstraint('name', name=op.f('uq__project_type__name')),
    )

    op.create_table(
        'project_typecast',
        sa.Column('project_typecast_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_type_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_maintenance', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_on', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('project_typecast_id', name=op.f('pk__project_typecast')),
    )

    op.create_table(
        'project_organizations',
        sa.Column('project_organization_link_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('role', postgresql.ENUM('PROPONENT', 'DESIGNER', 'DELIVERY', name='org_role', create_type=False), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.organization_id'], name=op.f('fk__project_organizations__organization_id__organization')),
        sa.ForeignKeyConstraint(['project_id'], ['project.project_id'], name=op.f('fk__project_organizations__project_id__project')),
        sa.PrimaryKeyConstraint('project_organization_link_id', name=op.f('pk__project_organizations')),
    )

    op.create_table(
        'project_postcode',
        sa.Column('project_postcode_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('postcode', sa.String(length=10), nullable=False),
        sa.Column('area_class', postgresql.ENUM('METROPOLITAN', 'REGIONAL', 'REMOTE', name='area_class', create_type=False), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['project.project_id'], name=op.f('fk__project_postcode__project_id__project')),
        sa.PrimaryKeyConstraint('project_postcode_id', name=op.f('pk__project_postcode')),
    )

    op.create_table(
        'project_stage_config',
        sa.Column('project_stage_config_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('stage', postgresql.ENUM('BUSINESS_CASE', 'DESIGN', 'CONSTRUCTION', name='project_stage', create_type=False), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('num_reports_required', sa.Integer(), nullable=True),
        sa.Column('frequency', postgresql.ENUM('MONTHLY', 'QUARTERLY', 'BI_MONTHLY', 'ANNUAL', name='report_frequency', create_type=False), nullable=True),
        sa.Column('min_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_on', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_on', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['project.project_id'], name=op.f('fk__project_stage_config__project_id__project')),
        sa.PrimaryKeyConstraint('project_stage_config_id', name=op.f('pk__project_stage_config')),
    )

    # ========================================================================================
    # STEP 3: Modify existing tables
    # ========================================================================================
    op.drop_index(op.f('ix_emission_entry_source'), table_name='emission_entry')
    op.drop_index(op.f('ix_emission_entry_subcategory'), table_name='emission_entry')
    op.create_foreign_key(
        op.f('fk__emission_entry_summary__project_reporting_submission_id__project_reporting_submission'),
        'emission_entry_summary',
        'project_reporting_submission',
        ['project_reporting_submission_id'],
        ['project_reporting_submission_id'],
    )
    op.create_foreign_key(
        op.f('fk__emission_entry_summary__submitted_by_user_id__users'),
        'emission_entry_summary',
        'users',
        ['submitted_by_user_id'],
        ['user_id'],
    )
    op.create_foreign_key(
        op.f('fk__emission_entry_summary__project_id__project'),
        'emission_entry_summary',
        'project',
        ['project_id'],
        ['project_id'],
    )

    op.drop_index(op.f('ix_emission_factor_source_unit'), table_name='emission_factor', postgresql_where='is_active')
    op.drop_index(op.f('ux_emission_factor_value_stage'), table_name='emission_factor_value')
    op.drop_constraint(op.f('emission_factor_value_emission_factor_id_fkey'), 'emission_factor_value', type_='foreignkey')
    op.create_foreign_key(
        op.f('fk__emission_factor_value__emission_factor_id__emission_factor'),
        'emission_factor_value',
        'emission_factor',
        ['emission_factor_id'],
        ['emission_factor_id'],
    )
    op.drop_index(op.f('ix_emission_source_by_subcategory'), table_name='emission_source')
    op.drop_index(op.f('ux_emission_source_subcat_name'), table_name='emission_source')
    op.drop_index(op.f('ix_emissions_sub_category_emissions_category_id'), table_name='emissions_sub_category')

    op.add_column(
        'project',
        sa.Column('project_class', postgresql.ENUM('SMALL', 'LARGE', 'RECURRING', name='project_class', create_type=False), nullable=False, server_default=sa.text("'SMALL'")),
    )
    op.add_column('project', sa.Column('simple_carbon_assessment', sa.Boolean(), nullable=True))
    op.add_column('project', sa.Column('contract_number', sa.String(length=100), nullable=False, server_default=sa.text("''")))
    op.add_column('project', sa.Column('program_name', sa.String(length=255), nullable=True))
    op.add_column('project', sa.Column('location_text', sa.String(length=255), nullable=True))
    op.add_column('project', sa.Column('construction_start_date', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('construction_end_date', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('commencement_of_operations', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('operational_life_years', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('project_capex_million', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('project', sa.Column('project_opex', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('project', sa.Column('first_submission_month', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('maintenance_region', sa.String(length=255), nullable=True))
    op.add_column('project', sa.Column('proponent_org_id', sa.UUID(), nullable=True))
    op.add_column('project', sa.Column('created_by_user_id', sa.UUID(), nullable=True))
    op.add_column('project', sa.Column('last_updated_by_user_id', sa.UUID(), nullable=True))

    op.create_unique_constraint('uq_project_project_name', 'project', ['project_name'])
    op.create_foreign_key(op.f('fk__project__created_by_user_id__users'), 'project', 'users', ['created_by_user_id'], ['user_id'])
    op.create_foreign_key(op.f('fk__project__last_updated_by_user_id__users'), 'project', 'users', ['last_updated_by_user_id'], ['user_id'])
    op.create_foreign_key(op.f('fk__project__proponent_org_id__organization'), 'project', 'organization', ['proponent_org_id'], ['organization_id'])

    op.alter_column(
        'project_reporting_submission',
        'frequency',
        existing_type=postgresql.ENUM('MONTHLY', 'QUARTERLY', 'FINANCIAL_YEAR', 'CALENDAR_YEAR', 'SIX_MONTHLY', 'AS_BUILT', name='report_frequency_type'),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
    op.drop_index(op.f('ix_project_reporting_submission_project'), table_name='project_reporting_submission')
    op.alter_column('roles', 'role_name',
               existing_type=sa.TEXT(),
               type_=sa.String(length=255),
               existing_nullable=False)
    op.drop_index(op.f('ux_roles_name_ci'), table_name='roles')
    op.create_unique_constraint(op.f('uq__roles__role_name'), 'roles', ['role_name'])
    op.add_column('users', sa.Column('organization_id', sa.UUID(), nullable=True))
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_index(op.f('ux_users_email_ci'), table_name='users')
    op.create_unique_constraint(op.f('uq__users__email'), 'users', ['email'])
    op.create_foreign_key(op.f('fk__users__organization_id__organization'), 'users', 'organization', ['organization_id'], ['organization_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraints and columns
    op.drop_constraint(op.f('fk__users__organization_id__organization'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('uq__users__email'), 'users', type_='unique')
    op.create_index(op.f('ux_users_email_ci'), 'users', [sa.literal_column('lower(email::text)')], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)
    op.drop_column('users', 'organization_id')
    op.drop_constraint(op.f('uq__roles__role_name'), 'roles', type_='unique')
    op.create_index(op.f('ux_roles_name_ci'), 'roles', [sa.literal_column('lower(role_name)')], unique=True)
    op.alter_column('roles', 'role_name',
               existing_type=sa.String(length=255),
               type_=sa.TEXT(),
               existing_nullable=False)
    op.create_index(op.f('ix_project_reporting_submission_project'), 'project_reporting_submission', ['project_id'], unique=False)
    op.alter_column('project_reporting_submission', 'frequency',
               existing_type=sa.String(length=50),
               type_=postgresql.ENUM('MONTHLY', 'QUARTERLY', 'FINANCIAL_YEAR', 'CALENDAR_YEAR', 'SIX_MONTHLY', 'AS_BUILT', name='report_frequency_type'),
               existing_nullable=False)
    op.drop_constraint(op.f('fk__project__proponent_org_id__organization'), 'project', type_='foreignkey')
    op.drop_constraint(op.f('fk__project__last_updated_by_user_id__users'), 'project', type_='foreignkey')
    op.drop_constraint(op.f('fk__project__created_by_user_id__users'), 'project', type_='foreignkey')
    op.drop_constraint('uq_project_project_name', 'project', type_='unique')
    op.drop_column('project', 'last_updated_by_user_id')
    op.drop_column('project', 'created_by_user_id')
    op.drop_column('project', 'proponent_org_id')
    op.drop_column('project', 'maintenance_region')
    op.drop_column('project', 'first_submission_month')
    op.drop_column('project', 'project_opex')
    op.drop_column('project', 'project_capex_million')
    op.drop_column('project', 'operational_life_years')
    op.drop_column('project', 'commencement_of_operations')
    op.drop_column('project', 'construction_end_date')
    op.drop_column('project', 'construction_start_date')
    op.drop_column('project', 'location_text')
    op.drop_column('project', 'program_name')
    op.drop_column('project', 'contract_number')
    op.drop_column('project', 'simple_carbon_assessment')
    op.drop_column('project', 'project_class')
    op.create_index(op.f('ix_emission_factor_source_unit'), 'emission_factor', ['emission_source_id', 'measurement_unit_id'], unique=False, postgresql_where='is_active')
    op.drop_constraint(op.f('fk__emission_entry_summary__project_id__project'), 'emission_entry_summary', type_='foreignkey')
    op.drop_constraint(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', type_='foreignkey')
    op.drop_constraint(op.f('fk__emission_entry_summary__project_reporting_submission_id__project_reporting_submission'), 'emission_entry_summary', type_='foreignkey')
    op.create_index(op.f('ix_emission_entry_subcategory'), 'emission_entry', ['emissions_sub_category_id'], unique=False)
    op.create_index(op.f('ix_emission_entry_source'), 'emission_entry', ['emission_source_id'], unique=False)
    op.drop_table('project_stage_config')
    op.drop_table('project_postcode')
    op.drop_table('project_organizations')
    op.drop_table('project_typecast')
    op.drop_table('project_type')
    op.drop_table('postcode_reference')
    op.drop_table('organization')

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS project_class CASCADE;")
    op.execute("DROP TYPE IF EXISTS area_class CASCADE;")
    op.execute("DROP TYPE IF EXISTS org_role CASCADE;")
    op.execute("DROP TYPE IF EXISTS project_stage CASCADE;")
    op.execute("DROP TYPE IF EXISTS report_frequency CASCADE;")
