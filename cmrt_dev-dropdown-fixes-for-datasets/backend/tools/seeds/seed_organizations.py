"""
Seed script: organizations
==========================
Inserts industry organisations (design consultants & construction contractors)
and their associated allowed email domains.

Data source: tools/seeds/data/Organizations_list.csv
  Columns:  name, type (DESIGNERS | CONTRACTORS), domains (pipe-separated)

Idempotent:
  - Organisations are matched by name (case-insensitive).  If one already
    exists it is NOT overwritten — the script skips it and moves on.
  - Domains are matched by (organization_id, domain).  Duplicates are ignored.

Run from the backend/ directory:
    python -m tools.seeds.seed_organizations

Or let the orchestrator run it as part of the full seed:
    python -m tools.seeds.run_all
"""

import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
_CSV_PATH = Path(__file__).parent / "data" / "Organizations_list.csv"


def _load_orgs() -> list[dict]:
    """Parse the CSV and return a list of org dicts."""
    orgs = []
    # Strip comment lines before passing to DictReader; utf-8-sig handles BOM.
    with _CSV_PATH.open(newline="", encoding="utf-8-sig") as fh:
        data_lines = [line for line in fh if not line.lstrip().startswith("#")]
    reader = csv.DictReader(data_lines)
    for row in reader:
            name = row["name"].strip()
            org_type = row["type"].strip()
            raw_domains = row.get("domains", "").strip()
            domains = [d.strip() for d in raw_domains.split("|") if d.strip()]
            if not name:
                continue
            orgs.append({"name": name, "type": org_type, "domains": domains})
    return orgs


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    orgs = _load_orgs()
    if not orgs:
        print("  [seed_organizations] No organisations found in CSV — skipping.")
        return

    engine = create_async_engine(settings.database_url, echo=False)

    inserted_orgs = 0
    skipped_orgs = 0
    inserted_domains = 0
    skipped_domains = 0

    async with engine.begin() as conn:
        for org in orgs:
            # ── 1. Upsert organisation (skip if name already exists) ────────
            existing = await conn.execute(
                text("SELECT id FROM organization WHERE lower(name) = lower(:name)"),
                {"name": org["name"]},
            )
            row = existing.first()

            if row:
                org_id = row[0]
                skipped_orgs += 1
            else:
                res = await conn.execute(
                    text(
                        "INSERT INTO organization "
                        "  (id, name, type, country, is_active, is_proponent, created_on) "
                        "VALUES "
                        "  (gen_random_uuid(), :name, :type, 'AU', true, true, now()) "
                        "RETURNING id"
                    ),
                    {"name": org["name"], "type": org["type"]},
                )
                org_id = res.first()[0]
                inserted_orgs += 1

            # ── 2. Seed allowed email domains ────────────────────────────────
            for domain in org["domains"]:
                check = await conn.execute(
                    text(
                        "SELECT 1 FROM organization_domains "
                        "WHERE organization_id = :org_id AND domain = :domain"
                    ),
                    {"org_id": str(org_id), "domain": domain},
                )
                if check.first():
                    skipped_domains += 1
                    continue
                await conn.execute(
                    text(
                        "INSERT INTO organization_domains "
                        "  (id, organization_id, domain, is_active, created_on) "
                        "VALUES "
                        "  (gen_random_uuid(), :org_id, :domain, true, now())"
                    ),
                    {"org_id": str(org_id), "domain": domain},
                )
                inserted_domains += 1

    await engine.dispose()

    total = len(orgs)
    print(
        f"  [seed_organizations] {inserted_orgs} new / {skipped_orgs} existing "
        f"(of {total} orgs).  "
        f"Domains: {inserted_domains} inserted, {skipped_domains} skipped."
    )


if __name__ == "__main__":
    asyncio.run(seed())
