"""
One-time migration: assign all NULL-revision rows in material_recycled_content,
default_transport_distances and default_waste_rates to a target revision.

Strategy per table:
  1. DELETE null-revision rows that already have a counterpart in the target
     revision (they were copied by a prior branch operation — the revision copy
     is the authoritative one).
  2. UPDATE any remaining null-revision rows to the target revision.

Usage:
    cd backend
    python tools/migrate_revision_ids.py --revision-id d1e03bea-0918-4788-9922-8c5268abadee
    # add --dry-run to preview counts without committing
"""

import argparse
import sys
from pathlib import Path

# ── make sure backend packages are on sys.path ─────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from core.config import Settings

TABLES = [
    {
        "name": "material_recycled_content",
        # columns that form the unique key (per uq_mrc_revision_jurisdiction_material)
        "key_cols": ["jurisdiction_id", "material_id"],
    },
    {
        "name": "default_transport_distances",
        # two separate unique indexes; cover both key combos
        "key_cols": ["jurisdiction_id", "material_id", "emissions_category_id"],
    },
    {
        "name": "default_waste_rates",
        "key_cols": [
            "jurisdiction_id",
            "material_id",
            "waste_treatment_id",
            "applicable_lifecycle_module_code",
            "basis",
        ],
    },
]


def null_safe_match(cols: list[str], alias_a: str, alias_b: str) -> str:
    """Build IS NOT DISTINCT FROM conditions between two table aliases."""
    return " AND ".join(
        f"{alias_a}.{c} IS NOT DISTINCT FROM {alias_b}.{c}" for c in cols
    )


def process_table(cur, table: dict, revision_id: str, dry_run: bool) -> None:
    tname = table["name"]
    key_cols = table["key_cols"]
    match_clause = null_safe_match(key_cols, "n", "r")

    # ── 1. count / delete duplicates ──────────────────────────────────────
    count_sql = f"""
        SELECT COUNT(*) FROM {tname} n
        WHERE n.dataset_revision_id IS NULL
          AND EXISTS (
            SELECT 1 FROM {tname} r
            WHERE r.dataset_revision_id = %s
              AND {match_clause}
          )
    """
    cur.execute(count_sql, (revision_id,))
    dup_count = cur.fetchone()[0]

    if dry_run:
        print(f"  [{tname}] would DELETE {dup_count} duplicate NULL rows (already in revision)")
    else:
        delete_sql = f"""
            DELETE FROM {tname} n
            USING {tname} r
            WHERE n.dataset_revision_id IS NULL
              AND r.dataset_revision_id = %s
              AND {null_safe_match(key_cols, 'n', 'r')}
        """
        cur.execute(delete_sql, (revision_id,))
        print(f"  [{tname}] deleted {cur.rowcount} duplicate NULL rows")

    # ── 2. count / update remaining NULL rows ─────────────────────────────
    count_sql2 = f"SELECT COUNT(*) FROM {tname} WHERE dataset_revision_id IS NULL"
    cur.execute(count_sql2)
    remaining = cur.fetchone()[0]

    if dry_run:
        print(f"  [{tname}] would UPDATE {remaining} remaining NULL rows → revision")
    else:
        cur.execute(
            f"UPDATE {tname} SET dataset_revision_id = %s WHERE dataset_revision_id IS NULL",
            (revision_id,),
        )
        print(f"  [{tname}] updated {cur.rowcount} rows → revision {revision_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate null revision IDs to a target revision.")
    parser.add_argument("--revision-id", required=True, help="Target dataset_revision UUID")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    args = parser.parse_args()

    settings = Settings()
    db_url = settings.database_url
    if not db_url:
        print("ERROR: DATABASE_URL is not set in .env.local", file=sys.stderr)
        sys.exit(1)

    # psycopg2 wants postgresql:// not postgresql+asyncpg://
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Connecting to database…")
    conn = psycopg2.connect(pg_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            for table in TABLES:
                print(f"\nProcessing {table['name']}…")
                process_table(cur, table, args.revision_id, args.dry_run)

        if args.dry_run:
            conn.rollback()
            print("\n[DRY RUN] No changes committed.")
        else:
            conn.commit()
            print("\nAll changes committed successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
