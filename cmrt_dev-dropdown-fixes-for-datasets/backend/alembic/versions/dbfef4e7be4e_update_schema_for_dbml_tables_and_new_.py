"""Update schema for DBML tables and new models

Revision ID: dbfef4e7be4e
Revises: a224bbfcb0aa
Create Date: 2026-02-26 10:37:27.311195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dbfef4e7be4e'
down_revision: Union[str, Sequence[str], None] = 'a224bbfcb0aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    def _drop_pk(table_name: str) -> None:
        op.execute(
            f"""
            DO $$
            DECLARE
                pk_name text;
            BEGIN
                SELECT c.conname
                INTO pk_name
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE c.contype = 'p'
                  AND t.relname = '{table_name}'
                LIMIT 1;

                IF pk_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table_name}', pk_name);
                END IF;
            END $$;
            """
        )

    # ------------------------------------------------------------------------------------
    # Drop FKs first (so we can switch PKs / drop old PK columns)
    # ------------------------------------------------------------------------------------
    op.execute("ALTER TABLE emission_entry DROP CONSTRAINT IF EXISTS emission_entry_submitted_by_user_id_fkey")
    op.execute("ALTER TABLE emission_entry_summary DROP CONSTRAINT IF EXISTS fk__emission_entry_summary__submitted_by_user_id__users")
    op.execute("ALTER TABLE project DROP CONSTRAINT IF EXISTS fk__project__created_by_user_id__users")
    op.execute("ALTER TABLE project DROP CONSTRAINT IF EXISTS fk__project__last_updated_by_user_id__users")
    op.execute("ALTER TABLE project DROP CONSTRAINT IF EXISTS fk__project__proponent_org_id__organization")
    op.execute("ALTER TABLE project_organizations DROP CONSTRAINT IF EXISTS fk__project_organizations__organization_id__organization")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk__users__organization_id__organization")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_id_fkey")

    # ------------------------------------------------------------------------------------
    # Roles: role_id/role_name -> id/name
    # ------------------------------------------------------------------------------------
    op.add_column('roles', sa.Column('id', sa.UUID(), nullable=True))
    op.execute('UPDATE roles SET id = role_id WHERE id IS NULL')
    op.alter_column('roles', 'id', nullable=False)

    op.add_column('roles', sa.Column('name', sa.String(), nullable=True))
    op.execute('UPDATE roles SET name = role_name WHERE name IS NULL')
    op.alter_column('roles', 'name', nullable=False)

    op.execute('UPDATE roles SET is_active = true WHERE is_active IS NULL')
    op.alter_column('roles', 'is_active', existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text('true'))

    op.execute('ALTER TABLE roles DROP CONSTRAINT IF EXISTS uq__roles__role_name')
    _drop_pk('roles')
    op.create_primary_key(op.f('pk__roles'), 'roles', ['id'])
    op.create_unique_constraint(op.f('uq__roles__name'), 'roles', ['name'])

    op.drop_column('roles', 'role_name')
    op.drop_column('roles', 'role_id')

    # ------------------------------------------------------------------------------------
    # Organization: organization_id/organization_type -> id/type (+country)
    # ------------------------------------------------------------------------------------
    op.add_column('organization', sa.Column('id', sa.UUID(), nullable=True))
    op.execute('UPDATE organization SET id = organization_id WHERE id IS NULL')
    op.alter_column('organization', 'id', nullable=False)

    op.add_column(
        'organization',
        sa.Column('type', sa.Enum('DESIGNERS', 'CONTRACTORS', name='organization_type'), nullable=True),
    )
    op.execute('UPDATE organization SET type = organization_type WHERE type IS NULL')
    op.alter_column('organization', 'type', nullable=False)

    op.add_column('organization', sa.Column('country', sa.String(), nullable=True))

    op.execute('UPDATE organization SET is_active = true WHERE is_active IS NULL')
    op.execute('UPDATE organization SET created_on = now() WHERE created_on IS NULL')
    op.alter_column('organization', 'is_active', existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column(
        'organization',
        'created_on',
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text('now()'),
    )

    _drop_pk('organization')
    op.create_primary_key(op.f('pk__organization'), 'organization', ['id'])

    op.drop_column('organization', 'organization_id')
    op.drop_column('organization', 'organization_type')

    # ------------------------------------------------------------------------------------
    # Users: user_id -> id (+profile fields). Note: role_id is being removed.
    # ------------------------------------------------------------------------------------
    op.add_column('users', sa.Column('id', sa.UUID(), nullable=True))
    op.execute('UPDATE users SET id = user_id WHERE id IS NULL')
    op.alter_column('users', 'id', nullable=False)

    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.add_column('users', sa.Column('oidc_sub', sa.String(), nullable=True))
    op.add_column('users', sa.Column('oidc_issuer', sa.String(), nullable=True))

    op.execute('UPDATE users SET is_active = true WHERE is_active IS NULL')
    op.execute('UPDATE users SET created_on = now() WHERE created_on IS NULL')
    op.alter_column('users', 'is_active', existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text('true'))
    op.alter_column(
        'users',
        'created_on',
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text('now()'),
    )

    _drop_pk('users')
    op.create_primary_key(op.f('pk__users'), 'users', ['id'])
    op.create_unique_constraint(op.f('uq__users__username'), 'users', ['username'])

    # Drop legacy auth/role columns
    op.drop_column('users', 'user_name')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'role_id')
    op.drop_column('users', 'user_id')

    # ------------------------------------------------------------------------------------
    # New/updated timestamps
    # ------------------------------------------------------------------------------------
    op.add_column('postcode_reference', sa.Column('updated_on', sa.TIMESTAMP(), nullable=True))
    op.add_column('project_organizations', sa.Column('updated_on', sa.TIMESTAMP(), nullable=True))
    op.add_column('project_postcode', sa.Column('updated_on', sa.TIMESTAMP(), nullable=True))

    # ------------------------------------------------------------------------------------
    # Recreate FKs against the new PK columns
    # ------------------------------------------------------------------------------------
    op.create_foreign_key(op.f('fk__users__organization_id__organization'), 'users', 'organization', ['organization_id'], ['id'])
    op.create_foreign_key(op.f('fk__project__proponent_org_id__organization'), 'project', 'organization', ['proponent_org_id'], ['id'])
    op.create_foreign_key(op.f('fk__project__created_by_user_id__users'), 'project', 'users', ['created_by_user_id'], ['id'])
    op.create_foreign_key(op.f('fk__project__last_updated_by_user_id__users'), 'project', 'users', ['last_updated_by_user_id'], ['id'])
    op.create_foreign_key(op.f('fk__project_organizations__organization_id__organization'), 'project_organizations', 'organization', ['organization_id'], ['id'])
    op.create_foreign_key(op.f('fk__emission_entry__submitted_by_user_id__users'), 'emission_entry', 'users', ['submitted_by_user_id'], ['id'])
    op.create_foreign_key(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', 'users', ['submitted_by_user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('user_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('role_id', sa.UUID(), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('password_hash', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('user_name', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.drop_constraint(op.f('fk__users__organization_id__organization'), 'users', type_='foreignkey')
    op.create_foreign_key(op.f('fk__users__organization_id__organization'), 'users', 'organization', ['organization_id'], ['organization_id'])
    op.create_foreign_key(op.f('users_role_id_fkey'), 'users', 'roles', ['role_id'], ['role_id'])
    op.drop_constraint('users_username_key', 'users', type_='unique')
    op.drop_constraint('users_email_key', 'users', type_='unique')
    op.drop_constraint(op.f('uq__users__username'), 'users', type_='unique')
    op.alter_column('users', 'created_on',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.drop_column('users', 'oidc_issuer')
    op.drop_column('users', 'oidc_sub')
    op.drop_column('users', 'username')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'id')
    op.add_column('roles', sa.Column('role_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False))
    op.add_column('roles', sa.Column('role_name', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.drop_constraint(op.f('uq__roles__name'), 'roles', type_='unique')
    op.drop_constraint('roles_name_key', 'roles', type_='unique')
    op.create_unique_constraint(op.f('uq__roles__role_name'), 'roles', ['role_name'])
    op.alter_column('roles', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.drop_column('roles', 'name')
    op.drop_column('roles', 'id')
    op.drop_column('project_postcode', 'updated_on')
    op.drop_constraint(op.f('fk__project_organizations__organization_id__organization'), 'project_organizations', type_='foreignkey')
    op.create_foreign_key(op.f('fk__project_organizations__organization_id__organization'), 'project_organizations', 'organization', ['organization_id'], ['organization_id'])
    op.drop_column('project_organizations', 'updated_on')
    op.drop_constraint(op.f('fk__project__last_updated_by_user_id__users'), 'project', type_='foreignkey')
    op.drop_constraint(op.f('fk__project__created_by_user_id__users'), 'project', type_='foreignkey')
    op.drop_constraint(op.f('fk__project__proponent_org_id__organization'), 'project', type_='foreignkey')
    op.create_foreign_key(op.f('fk__project__last_updated_by_user_id__users'), 'project', 'users', ['last_updated_by_user_id'], ['user_id'])
    op.create_foreign_key(op.f('fk__project__proponent_org_id__organization'), 'project', 'organization', ['proponent_org_id'], ['organization_id'])
    op.create_foreign_key(op.f('fk__project__created_by_user_id__users'), 'project', 'users', ['created_by_user_id'], ['user_id'])
    op.drop_column('postcode_reference', 'updated_on')
    op.add_column('organization', sa.Column('organization_type', postgresql.ENUM('DESIGNERS', 'CONTRACTORS', name='organization_type'), server_default=sa.text("'DESIGNERS'::organization_type"), autoincrement=False, nullable=False))
    op.add_column('organization', sa.Column('organization_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False))
    op.create_unique_constraint(op.f('uq__organization__name'), 'organization', ['name'])
    op.alter_column('organization', 'created_on',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('organization', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_column('organization', 'country')
    op.drop_column('organization', 'type')
    op.drop_column('organization', 'id')
    op.drop_constraint(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', type_='foreignkey')
    op.create_foreign_key(op.f('fk__emission_entry_summary__submitted_by_user_id__users'), 'emission_entry_summary', 'users', ['submitted_by_user_id'], ['user_id'])
    op.drop_constraint(op.f('fk__emission_entry__submitted_by_user_id__users'), 'emission_entry', type_='foreignkey')
    op.create_foreign_key(op.f('emission_entry_submitted_by_user_id_fkey'), 'emission_entry', 'users', ['submitted_by_user_id'], ['user_id'])
    # ### end Alembic commands ###
