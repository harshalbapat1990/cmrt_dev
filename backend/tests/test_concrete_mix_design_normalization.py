from types import SimpleNamespace
from uuid import UUID

import pytest

from crud.concrete_mix_design import list_mix_designs, normalize_component_code
from models.concrete_mix_design import ConcreteMixDesign


def test_component_codes_normalize_case_and_surrounding_whitespace():
    assert normalize_component_code(" FLY_ASH ") == "fly_ash"
    row = ConcreteMixDesign(component_code=" FLY_ASH ", component_label="Fly ash")
    assert row.component_code == "fly_ash"


class _ScalarsResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _query):
        return _ScalarsResult(self.rows)


@pytest.mark.asyncio
async def test_mix_design_reads_deduplicate_variants_and_prefer_canonical_code():
    revision_id = UUID("96dc8ce2-7520-445e-a030-9beea184f5a6")
    rows = [
        SimpleNamespace(
            id=UUID("8ca17263-28aa-4f32-86cc-d52af49aeb50"),
            dataset_revision_id=revision_id,
            component_code="FLY_ASH",
        ),
        SimpleNamespace(
            id=UUID("649ad36f-bbf3-4e28-9c05-9e8c3c992f0f"),
            dataset_revision_id=revision_id,
            component_code="fly_ash",
        ),
    ]

    result = await list_mix_designs(_Session(rows), revision_id)

    assert len(result) == 1
    assert result[0].component_code == "fly_ash"
