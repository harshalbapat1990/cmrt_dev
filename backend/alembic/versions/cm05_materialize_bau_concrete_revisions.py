"""Materialize populated BAU mix data in empty dataset-revision scaffolds.

Revision ID: cm05_materialize_bau_concrete_revisions
Revises: cm04_append_bau_scm_view_column

Some older revisions contain only empty concrete mix rows created by opening
the editor. The simplified register intentionally reads only the assigned
revision, so these empty rows hide usable data from the revision's ancestry.
Backfill only revisions with no active strength values, preserving all
revision-specific rows and assumptions that already contain user data.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from alembic import op


revision = "cm05_materialize_bau_concrete_revisions"
down_revision = "cm04_append_bau_scm_view_column"
branch_labels = None
depends_on = None

_STRENGTH_FIELDS = (
    "strength_20_kg_m3",
    "strength_25_kg_m3",
    "strength_32_kg_m3",
    "strength_40_kg_m3",
    "strength_50_kg_m3",
    "strength_65_kg_m3",
    "strength_80_kg_m3",
    "strength_100_kg_m3",
)


def _has_populated_mix(connection, revision_id: Optional[UUID]) -> bool:
    any_value = " OR ".join(f"{field} IS NOT NULL" for field in _STRENGTH_FIELDS)
    return bool(connection.execute(
        sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM concrete_mix_designs
                WHERE dataset_revision_id IS NOT DISTINCT FROM :revision_id
                  AND is_active = TRUE
                  AND ({any_value})
            )
        """),
        {"revision_id": revision_id},
    ).scalar_one())


def _source_for_revision(connection, revision_id: UUID, parent_by_id: dict) -> Optional[UUID]:
    """Use the closest populated ancestor, then published DEFAULT, then legacy global."""
    parent_id = parent_by_id.get(revision_id)
    visited: set[UUID] = set()
    while parent_id is not None and parent_id not in visited:
        visited.add(parent_id)
        if _has_populated_mix(connection, parent_id):
            return parent_id
        parent_id = parent_by_id.get(parent_id)

    default_id = connection.execute(sa.text("""
        SELECT id FROM dataset_revisions
        WHERE scope_type = 'DEFAULT' AND status = 'published'
          AND id <> :revision_id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """), {"revision_id": revision_id}).scalar_one_or_none()
    if default_id is not None and _has_populated_mix(connection, default_id):
        return default_id
    if _has_populated_mix(connection, None):
        return None
    return None


def _materialize_mix(connection, target_id: UUID, source_id: Optional[UUID]) -> None:
    # Existing target rows are known to be empty as a group. Copy values into
    # matching scaffolds and add only source components absent in the target.
    assignments = ",\n            ".join(
        f"{field} = source.{field}" for field in _STRENGTH_FIELDS
    )
    connection.execute(sa.text(f"""
        UPDATE concrete_mix_designs AS target
        SET component_code = source.component_code,
            component_label = source.component_label,
            display_order = source.display_order,
            {assignments},
            updated_on = now()
        FROM concrete_mix_designs AS source
        WHERE target.dataset_revision_id = :target_id
          AND target.is_active = TRUE
          AND source.dataset_revision_id IS NOT DISTINCT FROM :source_id
          AND source.is_active = TRUE
          AND lower(btrim(target.component_code)) = lower(btrim(source.component_code))
    """), {"target_id": target_id, "source_id": source_id})

    strength_columns = ", ".join(_STRENGTH_FIELDS)
    source_strengths = ", ".join(f"source.{field}" for field in _STRENGTH_FIELDS)
    connection.execute(sa.text(f"""
        INSERT INTO concrete_mix_designs
            (id, dataset_revision_id, component_code, component_label, display_order,
             {strength_columns}, is_active, created_on, updated_on)
        SELECT gen_random_uuid(), :target_id, source.component_code,
               source.component_label, source.display_order,
               {source_strengths}, TRUE, now(), now()
        FROM concrete_mix_designs AS source
        WHERE source.dataset_revision_id IS NOT DISTINCT FROM :source_id
          AND source.is_active = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM concrete_mix_designs AS target
              WHERE target.dataset_revision_id = :target_id
                AND target.is_active = TRUE
                AND lower(btrim(target.component_code)) = lower(btrim(source.component_code))
          )
    """), {"target_id": target_id, "source_id": source_id})

    target_has_assumptions = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM concrete_mix_assumptions
            WHERE dataset_revision_id = :target_id AND is_active = TRUE
        )
    """), {"target_id": target_id}).scalar_one()
    if not target_has_assumptions:
        connection.execute(sa.text("""
            INSERT INTO concrete_mix_assumptions
                (id, dataset_revision_id, bau_scm_content_pct,
                 default_max_fly_ash_pct, is_active, created_on, updated_on)
            SELECT gen_random_uuid(), :target_id,
                   source.bau_scm_content_pct, source.default_max_fly_ash_pct,
                   TRUE, now(), now()
            FROM concrete_mix_assumptions AS source
            WHERE source.dataset_revision_id IS NOT DISTINCT FROM :source_id
              AND source.is_active = TRUE
            ORDER BY source.created_on DESC, source.id
            LIMIT 1
        """), {"target_id": target_id, "source_id": source_id})

    # Recompute calculated binder rows under the target revision's assumptions.
    for field in _STRENGTH_FIELDS:
        connection.execute(sa.text(f"""
            UPDATE concrete_mix_designs AS derived
            SET {field} = CASE lower(btrim(derived.component_code))
                WHEN 'general_purpose_cement'
                    THEN (1 - assumption.bau_scm_content_pct) * total.{field}
                WHEN 'fly_ash'
                    THEN LEAST(assumption.bau_scm_content_pct,
                               assumption.default_max_fly_ash_pct) * total.{field}
                WHEN 'ggbf_slag'
                    THEN GREATEST(assumption.bau_scm_content_pct -
                                  assumption.default_max_fly_ash_pct, 0) * total.{field}
            END,
            updated_on = now()
            FROM concrete_mix_designs AS total
            JOIN concrete_mix_assumptions AS assumption
              ON assumption.dataset_revision_id = :target_id
             AND assumption.is_active = TRUE
            WHERE derived.dataset_revision_id = :target_id
              AND derived.is_active = TRUE
              AND lower(btrim(derived.component_code)) IN
                  ('general_purpose_cement', 'fly_ash', 'ggbf_slag')
              AND total.dataset_revision_id = :target_id
              AND total.is_active = TRUE
              AND lower(btrim(total.component_code)) = 'total_cementitious_content'
        """), {"target_id": target_id})


def upgrade() -> None:
    connection = op.get_bind()
    revisions = connection.execute(sa.text("""
        SELECT id, parent_revision_id
        FROM dataset_revisions
        ORDER BY created_at, id
    """)).mappings().all()
    parent_by_id = {row["id"]: row["parent_revision_id"] for row in revisions}

    for row in revisions:
        target_id = row["id"]
        # Never overwrite an already-populated revision.
        if _has_populated_mix(connection, target_id):
            continue
        source_id = _source_for_revision(connection, target_id, parent_by_id)
        if source_id is None and not _has_populated_mix(connection, None):
            continue
        _materialize_mix(connection, target_id, source_id)


def downgrade() -> None:
    # Backfilled data can be edited after deployment; deleting it on downgrade
    # would risk losing user data. The repair is intentionally irreversible.
    pass
