"""normalize active concrete mix component codes and enforce logical uniqueness

Revision ID: cm02_normalize_cm_codes
Revises: rp01_seed_recurring_periods, uc01_backfill_unit_conversions
"""
from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "cm02_normalize_cm_codes"
down_revision: Union[str, Sequence[str], None] = (
    "rp01_seed_recurring_periods",
    "uc01_backfill_unit_conversions",
)
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


def _normalize(code: str) -> str:
    return code.strip().lower()


def _merge_strength_values(group):
    """Coalesce missing values, but flag genuinely disagreeing populated cells."""
    merged = {}
    conflicting_fields = []
    for field in _STRENGTH_FIELDS:
        populated = [row[field] for row in group if row[field] is not None]
        distinct_values = set(populated)
        if len(distinct_values) > 1:
            conflicting_fields.append(field)
        elif populated:
            merged[field] = populated[0]
        else:
            merged[field] = None
    return merged, conflicting_fields


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, dataset_revision_id, component_code, component_label,
                   strength_20_kg_m3, strength_25_kg_m3, strength_32_kg_m3,
                   strength_40_kg_m3, strength_50_kg_m3, strength_65_kg_m3,
                   strength_80_kg_m3, strength_100_kg_m3
            FROM concrete_mix_designs
            WHERE is_active = TRUE
            ORDER BY dataset_revision_id NULLS FIRST, id
            """
        )
    ).mappings().all()

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["dataset_revision_id"], _normalize(row["component_code"]))].append(row)

    conflicts = []
    duplicate_groups = []
    for (revision_id, normalized_code), group in grouped.items():
        if len(group) < 2:
            continue
        _, conflicting_fields = _merge_strength_values(group)
        if conflicting_fields:
            ids = ", ".join(str(row["id"]) for row in group)
            scope = str(revision_id) if revision_id is not None else "GLOBAL"
            conflicts.append(
                f"scope={scope}, code={normalized_code}, fields={conflicting_fields}, ids=[{ids}]"
            )
        else:
            duplicate_groups.append((revision_id, normalized_code, group))

    if conflicts:
        preview = "; ".join(conflicts[:20])
        extra = f" (and {len(conflicts) - 20} more)" if len(conflicts) > 20 else ""
        raise RuntimeError(
            "Conflicting active concrete_mix_designs rows share a normalized "
            "component code. Resolve these groups manually, then rerun the "
            f"migration: {preview}{extra}"
        )

    update_code = sa.text(
        "UPDATE concrete_mix_designs SET component_code = :code, updated_on = now() WHERE id = :id"
    )
    merge_values = sa.text(
        "UPDATE concrete_mix_designs SET component_code = :code, "
        + ", ".join(f"{field} = :{field}" for field in _STRENGTH_FIELDS)
        + ", updated_on = now() WHERE id = :id"
    )
    deactivate = sa.text(
        "UPDATE concrete_mix_designs SET is_active = FALSE, updated_on = now() WHERE id = :id"
    )
    for _, normalized_code, group in duplicate_groups:
        canonical = sorted(
            group,
            key=lambda row: (
                0 if row["component_code"] == normalized_code else 1,
                str(row["id"]),
            ),
        )[0]
        values, _ = _merge_strength_values(group)
        connection.execute(
            merge_values,
            {"code": normalized_code, "id": canonical["id"], **values},
        )
        for row in group:
            if row["id"] != canonical["id"]:
                connection.execute(deactivate, {"id": row["id"]})

    # Normalize singleton variants too, so all active rows are stored canonically.
    for (_, normalized_code), group in grouped.items():
        if len(group) == 1 and group[0]["component_code"] != normalized_code:
            connection.execute(update_code, {"code": normalized_code, "id": group[0]["id"]})

    # Calculated values are derived data; refresh them from the active
    # assumptions and total cementitious row after the cleanup.
    for field in _STRENGTH_FIELDS:
        connection.execute(
            sa.text(
                f"""
                UPDATE concrete_mix_designs AS target
                SET {field} = CASE target.component_code
                    WHEN 'general_purpose_cement'
                        THEN (1 - assumptions.bau_scm_content_pct) * total.{field}
                    WHEN 'fly_ash'
                        THEN LEAST(assumptions.bau_scm_content_pct,
                                   assumptions.default_max_fly_ash_pct) * total.{field}
                    WHEN 'ggbf_slag'
                        THEN GREATEST(assumptions.bau_scm_content_pct -
                                      assumptions.default_max_fly_ash_pct, 0) * total.{field}
                END,
                updated_on = now()
                FROM concrete_mix_designs AS total
                JOIN concrete_mix_assumptions AS assumptions
                  ON assumptions.dataset_revision_id IS NOT DISTINCT FROM total.dataset_revision_id
                 AND assumptions.is_active = TRUE
                WHERE target.dataset_revision_id IS NOT DISTINCT FROM total.dataset_revision_id
                  AND target.is_active = TRUE
                  AND target.component_code IN ('general_purpose_cement', 'fly_ash', 'ggbf_slag')
                  AND total.is_active = TRUE
                  AND total.component_code = 'total_cementitious_content'
                """
            )
        )

    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_global_component")
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_revision_component")
    op.execute(
        """CREATE UNIQUE INDEX uq_concrete_mix_designs_global_component
           ON concrete_mix_designs (lower(btrim(component_code)))
           WHERE dataset_revision_id IS NULL AND is_active = TRUE"""
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_concrete_mix_designs_revision_component
           ON concrete_mix_designs (dataset_revision_id, lower(btrim(component_code)))
           WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"""
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_revision_component")
    op.execute("DROP INDEX IF EXISTS uq_concrete_mix_designs_global_component")
    op.execute(
        """CREATE UNIQUE INDEX uq_concrete_mix_designs_global_component
           ON concrete_mix_designs (component_code)
           WHERE dataset_revision_id IS NULL AND is_active = TRUE"""
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_concrete_mix_designs_revision_component
           ON concrete_mix_designs (dataset_revision_id, component_code)
           WHERE dataset_revision_id IS NOT NULL AND is_active = TRUE"""
    )
