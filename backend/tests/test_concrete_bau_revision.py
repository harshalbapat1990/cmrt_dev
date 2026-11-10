from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return [SimpleNamespace(_mapping=row) for row in self._rows]


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None
        self.params = None

    async def execute(self, statement, params=None):
        self.statement = str(statement)
        self.params = params
        return _Result(self.rows)


def _bau_total_row(*, quantity=550, assumption=0.3):
    return {
        "component_code": "total_cementitious_content",
        "component_label": "Total cementitious content",
        "quantity_kg_m3": quantity,
        "is_total_cementitious": True,
        "default_max_fly_ash_pct": assumption,
        "display_order": 10,
    }


def test_bau_view_migration_unpivots_50mpa_and_scopes_active_rows_and_assumptions():
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "cm03_create_revision_scoped_bau_concrete_view.py"
    source = migration.read_text(encoding="utf-8")

    assert "(50,  design.strength_50_kg_m3)" in source
    assert "WHERE design.is_active = TRUE" in source
    assert "assumptions.is_active = TRUE" in source
    assert "assumptions.dataset_revision_id IS NOT DISTINCT FROM design.dataset_revision_id" in source
    assert "assumptions.bau_scm_content_pct" in source
    # Preserve the pre-existing Azure view contract so CREATE OR REPLACE does
    # not attempt to remove or reorder its columns.
    projected_columns = source.split("SELECT", 2)[-1].split("FROM concrete_mix_designs", 1)[0]
    expected_order = [
        "design.dataset_revision_id",
        "design.component_code",
        "design.component_label",
        "design.display_order",
        "strength.strength_mpa",
        "strength.quantity_kg_m3",
        "is_total_cementitious",
        "assumptions.bau_scm_content_pct",
        "assumptions.default_max_fly_ash_pct",
    ]
    positions = [projected_columns.index(column) for column in expected_order]
    assert positions == sorted(positions)


def test_follow_up_migration_only_appends_missing_bau_scm_column():
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "cm04_append_bau_scm_view_column.py"
    source = migration.read_text(encoding="utf-8")

    assert "revision = \"cm04_append_bau_scm_view_column\"" in source
    assert "down_revision = \"cm03_bau_concrete_view\"" in source
    assert "NOT EXISTS" in source
    assert "attname = 'bau_scm_content_pct'" in source
    assert "CREATE OR REPLACE VIEW public.v_bau_default_concrete_mix" in source
    assert "DROP VIEW" not in source
    assert "CASCADE" not in source


@pytest.mark.asyncio
async def test_bau_lookup_reads_50mpa_from_the_requested_revision():
    from services.concrete_mix_register_calculations import calculator

    revision_id = uuid4()
    db = _Session([_bau_total_row()])

    result = await calculator._fetch_bau_grade_data(
        db, 50, dataset_revision_id=str(revision_id)
    )

    assert result["total_cementitious"] == 550.0
    assert result["assumptions_found"] is True
    assert db.params == {"rev_id": str(revision_id), "grade": 50}
    assert "dataset_revision_id = CAST(:rev_id AS uuid)" in db.statement


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("row", "expected_missing"),
    [
        (_bau_total_row(quantity=None), "Total cementitious content for 50 MPa"),
        (_bau_total_row(assumption=None), "active BAU concrete assumptions row"),
        (None, "active Total cementitious content row"),
    ],
)
async def test_simplified_calculation_reports_specific_missing_bau_input(
    monkeypatch, row, expected_missing
):
    from services import concrete_mix_register_calculations as service

    revision_id = uuid4()
    async def get_revision(_db, _project_id):
        return revision_id

    monkeypatch.setattr(
        service.ProjectContextHelper,
        "fetch_project_dataset_revision",
        staticmethod(get_revision),
    )
    # The unit under test stops before any emissions lookup when BAU data is incomplete.
    request = service.ConcreteSimplifiedRegisterRequest(
        project_id=uuid4(), mix_type="Precast", strength_mpa=50, scm_pct=30, volume_m3=1
    )
    with pytest.raises(ValueError, match=expected_missing):
        await service.calculator.calculate_simplified(
            _Session([row] if row else []), request
        )

