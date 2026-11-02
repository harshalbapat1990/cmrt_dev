"""
Seed script: permissions
Inserts default permissions.
Idempotent — uses INSERT ... ON CONFLICT (name) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_permissions
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

PERMISSIONS = [
    # ── Legacy permissions (kept for backward compatibility) ─────────────────
    {"name": "create_any",  "description": "Create any resource"},
    {"name": "read_any",    "description": "Read any resource"},
    {"name": "update_any",  "description": "Update any resource"},
    {"name": "delete_any",  "description": "Delete any resource"},
    {"name": "read_own",    "description": "Read own resource"},
    # ── Organisation-level permissions ───────────────────────────────────────
    {"name": "ORG_CREATE",                  "description": "Create a new organisation"},
    {"name": "ORG_ADMIN_APPOINT",           "description": "Directly appoint or deactivate an Org Admin"},
    {"name": "ORG_ADMIN_REQUEST_REVIEW",    "description": "Review (approve/reject) Org Admin requests"},
    {"name": "PROJECT_CREATE",              "description": "Create a project within an organisation"},
    {"name": "PROJECT_ASSIGN_PA",           "description": "Assign or deactivate a Project Admin on a project"},
    {"name": "ACCESS_VIEW",                 "description": "View user role assignments"},
    {"name": "REQUEST_REVIEW",              "description": "Review access requests (generic)"},
    # ── Project / Stage-level permissions ────────────────────────────────────
    {"name": "ACCESS_ASSIGN_PROJECT",       "description": "Grant/revoke roles at project scope"},
    {"name": "ACCESS_ASSIGN_STAGE",         "description": "Grant/revoke roles at stage scope"},
    {"name": "APPROVE_TECHNICAL",           "description": "Technically approve a project submission"},
    {"name": "APPROVE_FINAL",               "description": "Final approval of a project submission"},
    {"name": "RESULTS_VIEW",                "description": "View project results and reports"},
    {"name": "ACTIVITY_EDIT",               "description": "Edit activity data entries"},
    {"name": "COMPONENT_EDIT",              "description": "Edit component/material data"},
    {"name": "AUDIT_VIEW",                  "description": "View audit logs"},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in PERMISSIONS:
            result = await conn.execute(
                text(
                    "INSERT INTO permissions (id, name, description, created_on) "
                    "VALUES (gen_random_uuid(), :name, :description, now()) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_permissions] {inserted}/{len(PERMISSIONS)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
