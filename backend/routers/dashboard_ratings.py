"""dashboard_ratings.py

Ratings dashboard endpoint — Ene-1, Ene-2, Ene-3 credit scores
and the Ene-1 Reporting table (energy GJ + emissions tCO2e,
Construction / In-use / Lifecycle × Baseline / Actual).

Score formulas
--------------
Ene-1 (1–3):  1 + (pct_reduction / 0.30) × 2, clamped to [1, 3]
              pct_reduction = (baseline_lifecycle – actual_lifecycle) / baseline_lifecycle
Ene-2 (0–3):  3 × (lifecycle_renewable_gj / lifecycle_total_gj)
Ene-3 (0–3):  3 × abs(offsets_tco2e) / gross_a1_b7_tco2e
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from routers.dashboard_itmm_reporting import _ITMM_SQL
from routers.dashboard_carbon_storage import _DETAIL_SQL as _CARBON_STORAGE_DETAIL_SQL
from routers.dashboard_energy import _ENERGY_ROWS_SQL, _calc_reference_period


router = APIRouter(
    prefix="/api/dashboard/ratings",
    tags=["Dashboard — Ratings"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class Ene1ReportingRow(DashboardBase):
    """One row in the Ene-1 Reporting table (energy GJ or emissions tCO2e)."""
    actual_construction:    Optional[Decimal] = None
    actual_inuse:           Optional[Decimal] = None
    actual_lifecycle:       Optional[Decimal] = None
    baseline_construction:  Optional[Decimal] = None
    baseline_inuse:         Optional[Decimal] = None
    baseline_lifecycle:     Optional[Decimal] = None


class RatingsResponse(DashboardBase):
    """Full response for the Ratings dashboard tab."""
    ene1_score:          Optional[Decimal] = None
    ene2_score:          Optional[Decimal] = None
    ene3_score:          Optional[Decimal] = None
    ene1_energy_gj:      Ene1ReportingRow
    ene1_emissions_tco2e: Ene1ReportingRow


# ---------------------------------------------------------------------------
# SQL — mitigation energy rows
# Mirrors _ENERGY_ROWS_SQL but targets -mitigation / -mitigation-subst-adopted
# ui_table_keys.  Returns aggregated energy_gj per lifecycle_stage.
# ---------------------------------------------------------------------------

_MIT_ENERGY_SQL = text("""
WITH all_rows AS (

    -- bcDetailedLevel mitigation  (Construction, Fuels)
    SELECT
        'Construction'                                                           AS lifecycle_stage,
        ad.extra_fields->>'unit_code'                                            AS unit,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.quantity                                                              AS quantity
    FROM activity_data ad
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'bcDetailedLevel-mitigation',
              'bcDetailedLevel-mitigation-subst-adopted'
          )
      AND ad.extra_fields->>'emissions_category' = 'Fuels'

    UNION ALL

    -- electricity mitigation  (Construction, MWh)
    SELECT
        'Construction'                                                           AS lifecycle_stage,
        'MWh'                                                                    AS unit,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric                    AS quantity
    FROM activity_data ad
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'electricity-mitigation',
              'electricity-mitigation-subst-adopted'
          )

    UNION ALL

    -- replDetailed mitigation  (In-use / Operations, Fuels)
    SELECT
        'In-use / Operations'                                                    AS lifecycle_stage,
        ad.extra_fields->>'unit_code'                                            AS unit,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.quantity                                                              AS quantity
    FROM activity_data ad
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'replDetailed-mitigation',
              'replDetailed-mitigation-subst-adopted'
          )
      AND ad.extra_fields->>'emissions_category' = 'Fuels'

    UNION ALL

    -- opEnergy mitigation  (In-use / Operations, kWh via operational_equipment)
    SELECT
        'In-use / Operations'                                                    AS lifecycle_stage,
        'kWh'                                                                    AS unit,
        ad.extra_fields->>'item'                                                 AS emissions_source,
        CASE
            WHEN oe.annual_kwh_per_unit IS NOT NULL
            THEN oe.annual_kwh_per_unit
                 * COALESCE(ad.quantity, 0)
                 * CAST(:reference_period AS numeric)
            ELSE NULL
        END                                                                      AS quantity
    FROM activity_data ad
    LEFT JOIN LATERAL (
        SELECT (oe2.power_kw * oe2.hours_per_day * oe2.days_per_year)::numeric
            AS annual_kwh_per_unit
        FROM operational_equipment oe2
        WHERE oe2.id       = NULLIF(ad.extra_fields->>'eq_id', '')::uuid
          AND oe2.is_active = TRUE
        LIMIT 1
    ) oe ON TRUE
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'opEnergy-mitigation',
              'opEnergy-mitigation-subst-adopted'
          )

    UNION ALL

    -- opEnergyDetailed mitigation  (In-use / Operations, Fuels)
    SELECT
        'In-use / Operations'                                                    AS lifecycle_stage,
        ad.extra_fields->>'unit_code'                                            AS unit,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source', '')
        )                                                                        AS emissions_source,
        ad.quantity                                                              AS quantity
    FROM activity_data ad
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'opEnergyDetailed-mitigation',
              'opEnergyDetailed-mitigation-subst-adopted'
          )
      AND ad.extra_fields->>'emissions_category' = 'Fuels'

    UNION ALL

    -- opEnergyElectricity mitigation  (In-use / Operations, MWh)
    SELECT
        'In-use / Operations'                                                    AS lifecycle_stage,
        'MWh'                                                                    AS unit,
        ad.extra_fields->>'emission_source'                                      AS emissions_source,
        NULLIF(NULLIF(ad.extra_fields->>'quantity_mwh', ''), '-')::numeric                    AS quantity
    FROM activity_data ad
    WHERE ad.project_id                   = :project_id
      AND ad.project_stage_instance_id    = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN (
              'opEnergyElectricity-mitigation',
              'opEnergyElectricity-mitigation-subst-adopted'
          )

),

with_conversions AS (
    SELECT
        r.lifecycle_stage,
        CASE
            WHEN r.unit = 'GJ'
                THEN r.quantity
            WHEN r.unit IS DISTINCT FROM 'GJ' AND uc.factor IS NOT NULL
                THEN r.quantity * uc.factor
            WHEN r.unit IS DISTINCT FROM 'GJ' AND edc.energy_density IS NOT NULL
                THEN r.quantity * edc.energy_density
            ELSE NULL
        END                                                                      AS energy_gj
    FROM all_rows r
    LEFT JOIN LATERAL (
        SELECT uc2.factor
        FROM unit_conversions uc2
        JOIN units fu ON fu.id = uc2.from_unit_id
        JOIN units tu ON tu.id = uc2.to_unit_id
        WHERE fu.code = r.unit AND tu.code = 'GJ'
        LIMIT 1
    ) uc ON (r.unit IS DISTINCT FROM 'GJ')
    LEFT JOIN LATERAL (
        SELECT edc2.energy_density
        FROM energy_density_conversions edc2
        JOIN units eu ON eu.id = edc2.unit_id
        WHERE edc2.name                    = r.emissions_source
          AND eu.code                      = r.unit
          AND edc2.dataset_revision_id     IS NULL
        LIMIT 1
    ) edc ON (r.unit IS DISTINCT FROM 'GJ' AND uc.factor IS NULL)
    WHERE COALESCE(r.quantity, 0) <> 0
)

SELECT
    lifecycle_stage,
    COALESCE(SUM(energy_gj), 0) AS energy_gj
FROM with_conversions
WHERE energy_gj IS NOT NULL
GROUP BY lifecycle_stage
""")


# ---------------------------------------------------------------------------
# SQL — replDetailed non-Materials emissions
# Returns: actual_repl (tCO2e), baseline_repl (actual + mitigation + uplift_b2_b5)
# ---------------------------------------------------------------------------

_REPL_EMISSIONS_SQL = text("""
WITH repl_actual AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key              = 'replDetailed'
      AND COALESCE(extra_fields->>'emissions_category', '') != 'Materials'
),
repl_mit AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key IN (
              'replDetailed-mitigation',
              'replDetailed-mitigation-subst-adopted'
          )
      AND COALESCE(extra_fields->>'emissions_category', '') != 'Materials'
),
uplift_b2_b5 AS (
    SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
    FROM activity_data
    WHERE project_id                = :project_id
      AND project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL
           OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL
           OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key            = 'completeness'
      AND extra_fields->>'module' = 'b2_b5'
)
SELECT
    (SELECT val FROM repl_actual)                                                    AS actual_repl,
    (SELECT val FROM repl_actual)
    + (SELECT val FROM repl_mit)
    + (SELECT val FROM uplift_b2_b5)                                                AS baseline_repl
""")


# ---------------------------------------------------------------------------
# SQL — carbon offsets (Ene-3 numerator)
# Returns offsets_tco2e as a NEGATIVE value (matching breakdown router convention).
# ---------------------------------------------------------------------------

_OFFSETS_SQL = text("""
SELECT
    -COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0)
        AS offsets_tco2e
FROM activity_data
WHERE project_id                = :project_id
  AND project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL
       OR project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL
       OR submission_period_id = CAST(:submission_period_id AS uuid))
  AND ui_table_key IN (
          'bcDetailedLevel', 'constructionG3', 'recurringG3',
          'replDetailed', 'opEnergyDetailed'
      )
  AND extra_fields->>'emissions_category' = 'Offset'
""")


_DEFAULT_DATASET_REVISION_SQL = text("""
SELECT id FROM dataset_revisions
WHERE scope_type = 'DEFAULT' AND status = 'published'
ORDER BY created_at DESC LIMIT 1
""")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dec(val) -> Decimal:
    if val is None:
        return Decimal(0)
    return Decimal(str(val))


def _opt(val: Decimal) -> Optional[Decimal]:
    """Return None when the value is exactly zero (renders as '-' in the UI)."""
    return None if val == Decimal(0) else val


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/scores",
    response_model=RatingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Ratings: Ene-1, Ene-2, Ene-3 scores and Ene-1 Reporting table",
    description=(
        "Returns the three Ene credit scores and the Ene-1 Reporting table.\n\n"
        "- **Ene-1** (1–3): energy reduction score based on lifecycle emissions reduction 0–30%\n"
        "- **Ene-2** (0–3): renewable energy score based on lifecycle renewable energy %\n"
        "- **Ene-3** (0–3): carbon offsetting score based on offsets as % of gross A1–B7 emissions\n"
        "- **ene1_energy_gj**: Ene-1 Reporting table — energy (GJ) by stage × Actual / Baseline\n"
        "- **ene1_emissions_tco2e**: Ene-1 Reporting table — emissions (tCO2e) by stage × Actual / Baseline"
    ),
)
async def get_ratings(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> RatingsResponse:
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    # ── Project context ────────────────────────────────────────────────────
    ctx              = await ProjectContextHelper.get_project_context(db, project_id)
    reference_period = _calc_reference_period(ctx)
    jurisdiction     = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

    try:
        dr_result = await db.execute(_DEFAULT_DATASET_REVISION_SQL)
        default_dataset_revision_id = dr_result.scalar()
    except Exception:
        default_dataset_revision_id = None

    base_params = {
        "project_id":           str(project_id),
        "stage_instance_id":    str(stage_instance_id),
        "project_option_id":    str(project_option_id)    if project_option_id    else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }
    ittm_params = {
        **base_params,
        "elec_method":  elec_method,
        "jurisdiction": jurisdiction,
    }
    energy_params = {
        **base_params,
        "reference_period": reference_period,
        "default_dataset_revision_id": str(default_dataset_revision_id) if default_dataset_revision_id else None,
    }

    # ── Execute all queries ────────────────────────────────────────────────
    try:
        ittm_result   = await db.execute(_ITMM_SQL,                  ittm_params)
        cs_result     = await db.execute(_CARBON_STORAGE_DETAIL_SQL, ittm_params)
        energy_result = await db.execute(_ENERGY_ROWS_SQL,           energy_params)
        mit_result    = await db.execute(_MIT_ENERGY_SQL,            energy_params)
        repl_result   = await db.execute(_REPL_EMISSIONS_SQL,        base_params)
        offset_result = await db.execute(_OFFSETS_SQL,               base_params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    # ── Parse ITTM row ─────────────────────────────────────────────────────
    _raw = ittm_result.mappings().fetchone()
    ittm_row: dict = dict(_raw) if _raw is not None else {}

    # Biogenic injection (mirrors dashboard_ittm_reporting pattern)
    ittm_row["biogenic"] = sum(
        (_dec(r["carbon_storage_tco2e"]) for r in cs_result.mappings().all()),
        Decimal(0),
    )

    actual_a1a3              = _dec(ittm_row.get("actual_a1a3"))
    actual_a4                = _dec(ittm_row.get("actual_a4"))
    actual_a5_construction   = _dec(ittm_row.get("actual_a5_construction"))
    actual_a5_luc            = _dec(ittm_row.get("actual_a5_luc"))
    baseline_a5_construction = _dec(ittm_row.get("baseline_a5_construction"))
    baseline_a5_luc          = _dec(ittm_row.get("baseline_a5_luc"))
    actual_b1_2              = _dec(ittm_row.get("actual_b1_2"))
    baseline_b1_2            = _dec(ittm_row.get("baseline_b1_2"))
    actual_b2_b5             = _dec(ittm_row.get("actual_b2_b5"))
    actual_b6                = _dec(ittm_row.get("actual_b6"))
    baseline_b6              = _dec(ittm_row.get("baseline_b6"))
    actual_b7                = _dec(ittm_row.get("actual_b7"))
    baseline_b7              = _dec(ittm_row.get("baseline_b7"))
    actual_b8                = _dec(ittm_row.get("actual_b8"))

    # ── Parse actual energy rows ───────────────────────────────────────────
    energy_rows = energy_result.mappings().all()

    actual_construction_gj = sum(
        (_dec(r["energy_gj"])
         for r in energy_rows
         if r["lifecycle_stage"] == "Construction" and r["energy_gj"] is not None),
        Decimal(0),
    )
    actual_inuse_gj = sum(
        (_dec(r["energy_gj"])
         for r in energy_rows
         if r["lifecycle_stage"] == "In-use / Operations" and r["energy_gj"] is not None),
        Decimal(0),
    )
    renewable_gj = sum(
        (_dec(r["energy_gj"])
         for r in energy_rows
         if r["renewable_status"] == "Renewable" and r["energy_gj"] is not None),
        Decimal(0),
    )

    # ── Parse mitigation energy rows ───────────────────────────────────────
    mit_rows = mit_result.mappings().all()

    mit_construction_gj = sum(
        (_dec(r["energy_gj"])
         for r in mit_rows
         if r["lifecycle_stage"] == "Construction"),
        Decimal(0),
    )
    mit_inuse_gj = sum(
        (_dec(r["energy_gj"])
         for r in mit_rows
         if r["lifecycle_stage"] == "In-use / Operations"),
        Decimal(0),
    )

    # ── Parse replDetailed non-Materials emissions ─────────────────────────
    repl_row     = repl_result.mappings().fetchone()
    actual_repl  = _dec(repl_row["actual_repl"])  if repl_row else Decimal(0)
    baseline_repl = _dec(repl_row["baseline_repl"]) if repl_row else Decimal(0)

    # ── Parse offsets ──────────────────────────────────────────────────────
    # offsets_tco2e is stored as NEGATIVE; abs() gives the magnitude for Ene-3.
    offset_row  = offset_result.mappings().fetchone()
    offsets_val = _dec(offset_row["offsets_tco2e"]) if offset_row else Decimal(0)
    offsets_abs = abs(offsets_val)

    # ── Ene-1 energy GJ table ──────────────────────────────────────────────
    baseline_construction_gj = actual_construction_gj + mit_construction_gj
    baseline_inuse_gj        = actual_inuse_gj        + mit_inuse_gj
    actual_lifecycle_gj      = actual_construction_gj + actual_inuse_gj
    baseline_lifecycle_gj    = baseline_construction_gj + baseline_inuse_gj

    # ── Ene-1 emissions tCO2e table ────────────────────────────────────────
    actual_construction_tco2e   = actual_a5_construction   + actual_a5_luc
    actual_inuse_tco2e          = actual_b1_2  + actual_b6  + actual_b7  + actual_repl
    baseline_construction_tco2e = baseline_a5_construction + baseline_a5_luc
    baseline_inuse_tco2e        = baseline_b1_2 + baseline_b6 + baseline_b7 + baseline_repl
    actual_lifecycle_tco2e      = actual_construction_tco2e   + actual_inuse_tco2e
    baseline_lifecycle_tco2e    = baseline_construction_tco2e + baseline_inuse_tco2e

    # ── Ene-1 score ────────────────────────────────────────────────────────
    if baseline_lifecycle_tco2e > 0:
        pct_reduction = (
            (baseline_lifecycle_tco2e - actual_lifecycle_tco2e)
            / baseline_lifecycle_tco2e
        )
        ene1_score: Optional[Decimal] = max(
            Decimal("1"),
            min(
                Decimal("3"),
                Decimal("1") + (pct_reduction / Decimal("0.30")) * Decimal("2"),
            ),
        )
    else:
        ene1_score = Decimal("1")

    # ── Ene-2 score ────────────────────────────────────────────────────────
    if actual_lifecycle_gj > 0:
        ene2_score: Optional[Decimal] = min(
            Decimal("3"),
            Decimal("3") * renewable_gj / actual_lifecycle_gj,
        )
    else:
        ene2_score = Decimal("0")

    # ── Ene-3 score ────────────────────────────────────────────────────────
    # Gross A1–B7 excludes offsets and stored carbon
    gross_a1_b7 = (
        actual_a1a3
        + actual_a4
        + actual_a5_construction
        + actual_a5_luc
        + actual_b1_2
        + actual_b2_b5
        + actual_b6
        + actual_b7
        + actual_b8
    )
    if gross_a1_b7 > 0:
        ene3_score: Optional[Decimal] = min(
            Decimal("3"),
            Decimal("3") * offsets_abs / gross_a1_b7,
        )
    else:
        ene3_score = Decimal("0")

    # ── Build response ─────────────────────────────────────────────────────
    return RatingsResponse(
        ene1_score=ene1_score,
        ene2_score=ene2_score,
        ene3_score=ene3_score,
        ene1_energy_gj=Ene1ReportingRow(
            actual_construction   = _opt(actual_construction_gj),
            actual_inuse          = _opt(actual_inuse_gj),
            actual_lifecycle      = _opt(actual_lifecycle_gj),
            baseline_construction = _opt(baseline_construction_gj),
            baseline_inuse        = _opt(baseline_inuse_gj),
            baseline_lifecycle    = _opt(baseline_lifecycle_gj),
        ),
        ene1_emissions_tco2e=Ene1ReportingRow(
            actual_construction   = _opt(actual_construction_tco2e),
            actual_inuse          = _opt(actual_inuse_tco2e),
            actual_lifecycle      = _opt(actual_lifecycle_tco2e),
            baseline_construction = _opt(baseline_construction_tco2e),
            baseline_inuse        = _opt(baseline_inuse_tco2e),
            baseline_lifecycle    = _opt(baseline_lifecycle_tco2e),
        ),
    )
