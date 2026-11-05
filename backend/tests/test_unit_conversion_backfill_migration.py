from pathlib import Path
import re


def test_default_conversion_backfill_is_safe_for_existing_revisions():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "uc01_backfill_default_unit_conversions.py"
    )
    migration = migration_path.read_text(encoding="utf-8")
    sql_match = re.search(r'BACKFILL_SQL\s*=\s*"""(.*?)"""', migration, re.S)
    assert sql_match, "migration should expose its backfill query for review"
    sql = " ".join(sql_match.group(1).lower().split())

    assert "scope_type = 'default'" in sql
    assert "status = 'published'" in sql
    assert "order by created_at desc, id desc" in sql
    assert "target.scope_type <> 'default'" in sql
    assert "source.from_unit_id" in sql
    assert "source.to_unit_id" in sql
    assert "source.factor" in sql
    assert "not exists" in sql
    assert "existing.dataset_revision_id = target.id" in sql
    assert "existing.from_unit_id = source.from_unit_id" in sql
    assert "existing.to_unit_id = source.to_unit_id" in sql


def test_dataset_branching_copies_revision_scoped_unit_conversions():
    crud_path = Path(__file__).parents[1] / "crud" / "dataset_revisions.py"
    source = crud_path.read_text(encoding="utf-8")
    assert "if \"dataset_revision_id\" in mapper.local_table.c" in source
    assert "await _copy_table_bulk(model, model.__tablename__)" in source
    assert "unit_conversions" not in source.split("mapped_models = {", 1)[1].split("for model", 1)[0]
