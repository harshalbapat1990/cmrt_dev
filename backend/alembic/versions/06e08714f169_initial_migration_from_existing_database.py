"""Initial migration from existing database

Revision ID: 06e08714f169
Revises: 
Create Date: 2026-01-27 19:37:42.889961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06e08714f169'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This migration was generated as a baseline against a pre-Alembic legacy
    # database. All destructive operations use IF EXISTS so the migration is
    # safe to run against a fresh empty schema (drops become no-ops) as well as
    # against an existing legacy schema (normal cleanup).
    from sqlalchemy import inspect as sa_inspect
    conn = op.get_bind()
    existing_tables = set(sa_inspect(conn).get_table_names(schema="public"))

    # Drop legacy indexes — safe no-ops when tables/indexes don't exist
    op.execute("DROP INDEX IF EXISTS ix_emission_entry_source")
    op.execute("DROP INDEX IF EXISTS ix_emission_entry_subcategory")
    op.execute("DROP INDEX IF EXISTS ix_emission_factor_source_unit")
    op.execute("DROP INDEX IF EXISTS ux_emission_factor_value_stage")
    op.execute("DROP INDEX IF EXISTS ix_emission_source_by_subcategory")
    op.execute("DROP INDEX IF EXISTS ux_emission_source_subcat_name")
    op.execute("DROP INDEX IF EXISTS ix_emissions_sub_category_emissions_category_id")
    op.execute("DROP INDEX IF EXISTS ix_project_reporting_submission_project")
    op.execute("DROP INDEX IF EXISTS ux_roles_name_ci")
    op.execute("DROP INDEX IF EXISTS ix_users_role_id")
    op.execute("DROP INDEX IF EXISTS ux_users_email_ci")

    # Drop legacy FK — safe no-op when table/constraint doesn't exist
    if "emission_factor_value" in existing_tables:
        op.execute("ALTER TABLE emission_factor_value DROP CONSTRAINT IF EXISTS emission_factor_value_emission_factor_id_fkey")

    # Create FK constraints / alter columns only when the target tables already
    # exist (i.e. this is a legacy schema, not a fresh install)
    if "emission_entry_summary" in existing_tables:
        op.execute(
            """
            DO $$
            DECLARE
                constraint_name text;
            BEGIN
                FOR constraint_name IN
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_attribute att ON att.attrelid = rel.oid
                    WHERE rel.relname = 'emission_entry_summary'
                      AND att.attnum = ANY(con.conkey)
                      AND att.attname IN (
                          'submitted_by_user_id',
                          'project_reporting_submission_id',
                          'project_id'
                      )
                      AND con.contype = 'f'
                LOOP
                    EXECUTE format('ALTER TABLE emission_entry_summary DROP CONSTRAINT IF EXISTS %I', constraint_name);
                END LOOP;
            END $$;
            """
        )
        op.create_foreign_key(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', 'users', ['submitted_by_user_id'], ['id'])
        op.create_foreign_key(op.f('fk__emission_entry_summary__project_reporting_submission_id__project_reporting_submission'), 'emission_entry_summary', 'project_reporting_submission', ['project_reporting_submission_id'], ['id'])
        op.create_foreign_key(op.f('fk__emission_entry_summary__project_id__project'), 'emission_entry_summary', 'project', ['project_id'], ['id'])

    if "emission_factor_value" in existing_tables:
        op.execute(
            """
            DO $$
            DECLARE r text;
            BEGIN
                FOR r IN
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_attribute att ON att.attrelid = rel.oid
                    WHERE rel.relname = 'emission_factor_value'
                      AND att.attnum = ANY(con.conkey)
                      AND att.attname = 'emission_factor_id'
                      AND con.contype = 'f'
                LOOP
                    EXECUTE format('ALTER TABLE emission_factor_value DROP CONSTRAINT IF EXISTS %I', r);
                END LOOP;
            END $$;
            """
        )
        op.create_foreign_key(op.f('fk__emission_factor_value__emission_factor_id__emission_factor'), 'emission_factor_value', 'emission_factor', ['emission_factor_id'], ['id'])

    if "roles" in existing_tables:
        existing_role_cols = {c["name"] for c in sa_inspect(conn).get_columns("roles", schema="public")}
        if "role_name" in existing_role_cols:
            op.alter_column('roles', 'role_name',
                       existing_type=sa.TEXT(),
                       type_=sa.String(length=255),
                       existing_nullable=False)
            op.execute("ALTER TABLE roles DROP CONSTRAINT IF EXISTS uq__roles__role_name")
            op.create_unique_constraint(op.f('uq__roles__role_name'), 'roles', ['role_name'])

    if "users" in existing_tables:
        op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq__users__email")
        op.create_unique_constraint(op.f('uq__users__email'), 'users', ['email'])


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('uq__users__email'), 'users', type_='unique')
    op.create_index(op.f('ux_users_email_ci'), 'users', [sa.literal_column('lower(email::text)')], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)
    op.drop_constraint(op.f('uq__roles__role_name'), 'roles', type_='unique')
    op.create_index(op.f('ux_roles_name_ci'), 'roles', [sa.literal_column('lower(role_name)')], unique=True)
    op.alter_column('roles', 'role_name',
               existing_type=sa.String(length=255),
               type_=sa.TEXT(),
               existing_nullable=False)
    op.create_index(op.f('ix_project_reporting_submission_project'), 'project_reporting_submission', ['project_id'], unique=False)
    op.create_index(op.f('ix_emissions_sub_category_emissions_category_id'), 'emissions_sub_category', ['emissions_sub_category_id'], unique=False)
    op.create_index(op.f('ux_emission_source_subcat_name'), 'emission_source', ['emissions_sub_category_id', sa.literal_column('lower(name::text)')], unique=True)
    op.create_index(op.f('ix_emission_source_by_subcategory'), 'emission_source', ['emissions_sub_category_id'], unique=False)
    op.drop_constraint(op.f('fk__emission_factor_value__emission_factor_id__emission_factor'), 'emission_factor_value', type_='foreignkey')
    op.create_foreign_key(op.f('emission_factor_value_emission_factor_id_fkey'), 'emission_factor_value', 'emission_factor', ['emission_factor_id'], ['emission_factor_id'], ondelete='CASCADE')
    op.create_index(op.f('ux_emission_factor_value_stage'), 'emission_factor_value', ['emission_factor_id', 'stage_code'], unique=True)
    op.create_index(op.f('ix_emission_factor_source_unit'), 'emission_factor', ['emission_source_id', 'measurement_unit_id'], unique=False, postgresql_where='is_active')
    op.drop_constraint(op.f('fk__emission_entry_summary__project_id__project'), 'emission_entry_summary', type_='foreignkey')
    op.drop_constraint(op.f('fk__emission_entry_summary__project_reporting_submission_id__project_reporting_submission'), 'emission_entry_summary', type_='foreignkey')
    op.drop_constraint(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', type_='foreignkey')
    op.create_index(op.f('ix_emission_entry_subcategory'), 'emission_entry', ['emissions_sub_category_id'], unique=False)
    op.create_index(op.f('ix_emission_entry_source'), 'emission_entry', ['emission_source_id'], unique=False)
    # ### end Alembic commands ###
