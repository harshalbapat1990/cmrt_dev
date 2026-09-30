from pathlib import Path
import re

import pytest

from services import aus_road_emissions_function as function_service


class _ExistsResult:
    def __init__(self, exists: bool):
        self._exists = exists

    def scalar(self):
        return self._exists


class _Connection:
    def __init__(self, exists: bool):
        self.exists = exists
        self.statements: list[str] = []
        self.parameters = None

    async def execute(self, statement, parameters):
        self.statements.append(str(statement))
        self.parameters = parameters
        return _ExistsResult(self.exists)

    async def exec_driver_sql(self, statement):
        self.statements.append(statement)


class _Begin:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *_args):
        return False


class _Engine:
    def __init__(self, exists: bool):
        self.connection = _Connection(exists)

    def begin(self):
        return _Begin(self.connection)


@pytest.mark.asyncio
@pytest.mark.parametrize("already_exists", [False, True])
async def test_startup_installs_or_refreshes_revision_aware_function(tmp_path: Path, monkeypatch, already_exists: bool):
    sql_file = tmp_path / "function.sql"
    sql_file.write_text("CREATE OR REPLACE FUNCTION public.example() RETURNS integer AS $$ SELECT 1 $$ LANGUAGE sql;", encoding="utf-8")
    monkeypatch.setattr(function_service, "_FUNCTION_SQL", sql_file)
    engine = _Engine(already_exists)

    await function_service.ensure_aus_road_emissions_function(engine)

    assert engine.connection.parameters == {"signature": function_service._FUNCTION_SIGNATURE}
    assert engine.connection.statements[-1] == sql_file.read_text(encoding="utf-8")


def test_function_definition_uses_revision_scoped_factors_with_legacy_fallbacks():
    definition = function_service._FUNCTION_SQL.read_text(encoding="utf-8-sig")
    normalized = re.sub(r"\s+", " ", definition).lower()

    assert "p_dataset_revision_id uuid" in normalized
    # These tables support legacy, unscoped rows. Revision-specific rows take
    # precedence, with NULL revision rows retained as a fallback.
    assert "rates.dataset_revision_id = p_dataset_revision_id or rates.dataset_revision_id is null" in normalized
    assert normalized.count(
        "coefficients.dataset_revision_id = p_dataset_revision_id or coefficients.dataset_revision_id is null"
    ) == 2
    # These factors must match the selected revision exactly.
    assert "vm.dataset_revision_id = p_dataset_revision_id" in normalized
    assert "euf.dataset_revision_id = p_dataset_revision_id" in normalized
    assert "edf.dataset_revision_id = p_dataset_revision_id" in normalized
    assert "to_jsonb(factor_row)->>'dataset_revision_id'" in normalized
