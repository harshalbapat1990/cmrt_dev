"""Attach legacy vehicle masses and direct substitutions to dataset revisions.

Revision ID: ds02_revision_legacy_tables
Revises: 207e9e8c8806
"""
from alembic import op
import sqlalchemy as sa


revision = "ds02_revision_legacy_tables"
down_revision = "207e9e8c8806"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Older installs may not have a published DEFAULT revision yet. Establish
    # one before associating the existing platform-wide rows with it.
    conn.execute(sa.text("""
        INSERT INTO dataset_revisions (id, name, status, scope_type, scope_id, created_at, notes)
        SELECT gen_random_uuid(), 'Legacy global datasets', 'published', 'DEFAULT', NULL, now(),
               'Baseline revision created while attaching legacy dataset tables'
        WHERE NOT EXISTS (
            SELECT 1 FROM dataset_revisions
            WHERE scope_type = 'DEFAULT' AND scope_id IS NULL AND status = 'published'
        )
    """))

    foreign_key_names = {
        "vehicle_masses": "fk_vehicle_masses_revision_id",
        "direct_substitution_factors": "fk_direct_substitution_revision_id",
    }
    for table in ("vehicle_masses", "direct_substitution_factors"):
        op.add_column(table, sa.Column("dataset_revision_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            foreign_key_names[table],
            table,
            "dataset_revisions",
            ["dataset_revision_id"],
            ["id"],
            ondelete="CASCADE",
        )
        conn.execute(sa.text(f"""
            UPDATE {table}
            SET dataset_revision_id = (
                SELECT id FROM dataset_revisions
                WHERE scope_type = 'DEFAULT' AND scope_id IS NULL AND status = 'published'
                ORDER BY created_at DESC
                LIMIT 1
            )
            WHERE dataset_revision_id IS NULL
        """))
        op.alter_column(table, "dataset_revision_id", nullable=False)
        op.create_index(f"ix_{table}_dataset_revision_id", table, ["dataset_revision_id"])

    op.drop_constraint(
        "uq_vehicle_masses_vehicle_class_id",
        "vehicle_masses",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_vehicle_masses_revision_class",
        "vehicle_masses",
        ["dataset_revision_id", "vehicle_class_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_vehicle_masses_revision_class", "vehicle_masses", type_="unique")
    op.execute(sa.text("""
        DELETE FROM vehicle_masses a USING vehicle_masses b
        WHERE a.vehicle_class_id = b.vehicle_class_id
          AND a.dataset_revision_id = b.dataset_revision_id
          AND a.id > b.id
    """))
    op.create_unique_constraint(
        "uq_vehicle_masses_vehicle_class_id",
        "vehicle_masses",
        ["vehicle_class_id"],
    )
    foreign_key_names = {
        "vehicle_masses": "fk_vehicle_masses_revision_id",
        "direct_substitution_factors": "fk_direct_substitution_revision_id",
    }
    for table in ("vehicle_masses", "direct_substitution_factors"):
        op.drop_index(f"ix_{table}_dataset_revision_id", table_name=table)
        op.drop_constraint(
            foreign_key_names[table],
            table,
            type_="foreignkey",
        )
        op.drop_column(table, "dataset_revision_id")
