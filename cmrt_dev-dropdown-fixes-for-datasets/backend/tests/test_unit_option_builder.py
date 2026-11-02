from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from crud.unit_conversions import build_unit_options_with_conversions


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


@pytest.mark.asyncio
async def test_unit_options_include_canonical_unit_without_conversions():
    canonical_id = uuid4()
    canonical = SimpleNamespace(id=canonical_id, code="m", label="Metre")
    # The builder queries for canonical units, then checks whether global
    # conversion rows exist. Model the empty conversion query explicitly.
    db = _Session([_ScalarsResult([canonical]), _ScalarsResult([])])

    options = await build_unit_options_with_conversions(db, [canonical_id])

    assert options == [{
        "id": canonical_id,
        "name": "m",
        "label": "Metre",
        "is_canonical": True,
        "to_canonical_factor": 1,
        "canonical_unit_id": canonical_id,
        "canonical_unit_code": "m",
    }]
    assert len(db.statements) == 2


@pytest.mark.asyncio
async def test_revision_conversion_takes_precedence_over_global_pair():
    canonical_id, source_id, global_source_id, revision_id = uuid4(), uuid4(), uuid4(), uuid4()
    canonical = SimpleNamespace(id=canonical_id, code="m", label="Metre")
    source = SimpleNamespace(id=source_id, code="cm", label="Centimetre")
    global_source = SimpleNamespace(id=global_source_id, code="mm", label="Millimetre")
    global_conversion = SimpleNamespace(
        from_unit_id=source_id, to_unit_id=canonical_id, factor=Decimal("0.01"), dataset_revision_id=None
    )
    revision_conversion = SimpleNamespace(
        from_unit_id=source_id, to_unit_id=canonical_id, factor=Decimal("0.02"), dataset_revision_id=revision_id
    )
    global_only_conversion = SimpleNamespace(
        from_unit_id=global_source_id, to_unit_id=canonical_id, factor=Decimal("0.001"), dataset_revision_id=None
    )
    db = _Session([
        _ScalarsResult([canonical]),
        _ScalarsResult([revision_conversion, global_conversion, global_only_conversion]),
        _ScalarsResult([source, global_source]),
    ])

    options = await build_unit_options_with_conversions(db, [canonical_id], revision_id)

    assert [option["name"] for option in options] == ["m", "cm", "mm"]
    assert options[1]["to_canonical_factor"] == Decimal("0.02")
    assert options[2]["to_canonical_factor"] == Decimal("0.001")
    conversion_query = db.statements[1]
    compiled = conversion_query.compile()
    assert "IS NULL" in str(compiled)
    assert revision_id in compiled.params.values()
