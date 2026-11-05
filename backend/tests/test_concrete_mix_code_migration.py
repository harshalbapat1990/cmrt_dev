from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "cm02_normalize_concrete_mix_component_codes.py"
)
SPEC = spec_from_file_location("cm02_normalize_concrete_mix_component_codes", MIGRATION_PATH)
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def _row(**values):
    return {field: None for field in MIGRATION._STRENGTH_FIELDS} | values


def test_migration_merges_empty_placeholder_with_populated_legacy_row():
    populated = _row(strength_20_kg_m3=0, strength_25_kg_m3=93)

    merged, conflicts = MIGRATION._merge_strength_values([_row(), populated])

    assert conflicts == []
    assert merged["strength_20_kg_m3"] == 0
    assert merged["strength_25_kg_m3"] == 93
    assert merged["strength_32_kg_m3"] is None


def test_migration_reports_only_fields_with_different_populated_values():
    first = _row(strength_20_kg_m3=100, strength_25_kg_m3=20)
    second = _row(strength_20_kg_m3=100, strength_25_kg_m3=30)

    merged, conflicts = MIGRATION._merge_strength_values([first, second])

    assert conflicts == ["strength_25_kg_m3"]
    assert merged["strength_20_kg_m3"] == 100
