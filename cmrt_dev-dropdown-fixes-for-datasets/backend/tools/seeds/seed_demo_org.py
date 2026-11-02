"""
tools/seeds/seed_demo_org.py
============================
Seeds a demonstration organisation with allowed email domains so that the
domain-match registration rule can be exercised immediately in every environment.

Idempotent — checks existence before inserting.

Run from the backend/ directory:
    python -m tools.seeds.seed_demo_org
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings

DEMO_ORG = {
    "name": "Transport for NSW (Demo)",
    "type": "DESIGNERS",
    "country": "AU",
}

DEMO_DOMAINS = [
    "nsw.gov.au",
    "transport.nsw.gov.au",
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # 1. Create org (idempotent by name)
        check_org = await conn.execute(
            text("SELECT id FROM organization WHERE name = :name"),
            {"name": DEMO_ORG["name"]},
        )
        row = check_org.first()
        if row:
            org_id = row[0]
            print(f"[seed_demo_org] Org already exists: {org_id}")
        else:
            res = await conn.execute(
                text(
                    "INSERT INTO organization (id, name, type, country, is_active, created_on) "
                    "VALUES (gen_random_uuid(), :name, :type, :country, true, now()) "
                    "RETURNING id"
                ),
                DEMO_ORG,
            )
            org_id = res.first()[0]
            print(f"[seed_demo_org] Created demo org: {org_id} — {DEMO_ORG['name']}")

        # 2. Seed allowed domains (idempotent)
        inserted_domains = 0
        for domain in DEMO_DOMAINS:
            check = await conn.execute(
                text(
                    "SELECT 1 FROM organization_domains "
                    "WHERE organization_id = :org_id AND domain = :domain"
                ),
                {"org_id": str(org_id), "domain": domain},
            )
            if check.first():
                print(f"[seed_demo_org]   Domain already exists: {domain}")
                continue
            await conn.execute(
                text(
                    "INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on) "
                    "VALUES (gen_random_uuid(), :org_id, :domain, true, now())"
                ),
                {"org_id": str(org_id), "domain": domain},
            )
            inserted_domains += 1
            print(f"[seed_demo_org]   Added domain: {domain}")

        print(f"[seed_demo_org] Done — {inserted_domains} domain(s) added.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
