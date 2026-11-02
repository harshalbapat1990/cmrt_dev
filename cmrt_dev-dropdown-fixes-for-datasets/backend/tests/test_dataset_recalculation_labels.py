from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from services.dataset_recalculation_labels import data_entry_table_display_name


@pytest.mark.asyncio
async def test_data_entry_label_queries_stage_scalar_without_relationship_lazy_load():
    stage_instance_id = uuid4()
    result = SimpleNamespace(scalar_one_or_none=lambda: "BUSINESS_CASE")
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    row = SimpleNamespace(
        ui_table_key="componentRepl",
        project_stage_instance_id=stage_instance_id,
    )

    label = await data_entry_table_display_name(db, row)

    assert label == "Business case-Replacement and Refurbishment-Component level replacement"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_data_entry_label_works_without_stage_instance():
    db = SimpleNamespace(execute=AsyncMock())
    row = SimpleNamespace(ui_table_key="componentRepl", project_stage_instance_id=None)

    label = await data_entry_table_display_name(db, row)

    assert label == "Stage-Replacement and Refurbishment-Component level replacement"
    db.execute.assert_not_awaited()
