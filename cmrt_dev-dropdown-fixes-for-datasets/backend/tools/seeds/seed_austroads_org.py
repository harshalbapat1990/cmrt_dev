"""
Seed script: Austroads platform operator org
============================================
Creates the Austroads organisation with type PLATFORM_OPERATOR and registers
the allowed email domain so that Austroads staff who self-register are
automatically routed through the SUPER_ADMIN approval flow.

Idempotent — safe to run multiple times.

Run from the backend/ directory:
    python -m tools.seeds.seed_austroads_org

Prerequisites:
    - Alembic migration i1j2k3l4m5n6 (PLATFORM_OPERATOR enum value) must be applied.
    - Roles must exist (run seed_roles.py first).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

# ── Configuration ─────────────────────────────────────────────────────────────
AUSTROADS_ORG_NAME = "Austroads"
AUSTROADS_ORG_TYPE = "PLATFORM_OPERATOR"
AUSTROADS_DOMAIN   = "austroads.com.au"
# ─────────────────────────────────────────────────────────────────────────────


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        # 1. Check if Austroads org already exists (by name + type)
        existing = await conn.execute(
            text(
                "SELECT id FROM organization WHERE name = :name AND type = :org_type LIMIT 1"
            ),
            {"name": AUSTROADS_ORG_NAME, "org_type": AUSTROADS_ORG_TYPE},
        )
        row = existing.fetchone()

        if row:
            org_id = row[0]
            print(f"[seed_austroads_org] Austroads org already exists: {org_id}")
        else:
            result = await conn.execute(
                text(
                    """
                    INSERT INTO organization (id, name, type, is_proponent, is_active, created_on)
                    VALUES (gen_random_uuid(), :name, :org_type, false, true, now())
                    RETURNING id
                    """
                ),
                {"name": AUSTROADS_ORG_NAME, "org_type": AUSTROADS_ORG_TYPE},
            )
            org_id = result.scalar_one()
            print(f"[seed_austroads_org] Created Austroads org: {org_id}")

        # 2. Ensure the allowed domain is registered
        domain_result = await conn.execute(
            text(
                """
                INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
                VALUES (gen_random_uuid(), :org_id, :domain, true, now())
                ON CONFLICT (organization_id, domain) DO NOTHING
                """
            ),
            {"org_id": org_id, "domain": AUSTROADS_DOMAIN},
        )
        if domain_result.rowcount:
            print(f"[seed_austroads_org] Added allowed domain: {AUSTROADS_DOMAIN}")
        else:
            print(f"[seed_austroads_org] Domain already registered: {AUSTROADS_DOMAIN}")

        print(
            f"\n[seed_austroads_org] Done.\n"
            f"  Org ID : {org_id}\n"
            f"  Domain : {AUSTROADS_DOMAIN}\n"
            f"\n"
            f"  Any user who self-registers with an @{AUSTROADS_DOMAIN} email\n"
            f"  will trigger a SUPER_ADMIN access request (pending SA approval).\n"
            f"\n"
            f"  To onboard the first Austroads SUPER_ADMIN without self-registration,\n"
            f"  run seed_users.py + seed_user_roles.py with that user's email.\n"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
