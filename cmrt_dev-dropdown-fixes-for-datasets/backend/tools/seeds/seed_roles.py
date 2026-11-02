"""
Seed script: roles
Inserts default roles.
Idempotent — uses INSERT ... ON CONFLICT (name) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_roles
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

ROLES = [
    # ── Legacy roles (kept for backward compatibility) ──────────────────────
    {"name": "Admin",  "description": "Legacy administrator (use SUPER_ADMIN or ORG_ADMIN)"},
    {"name": "Editor", "description": "Legacy editor (use PROJECT_EDITOR)"},
    {"name": "Viewer", "description": "Legacy viewer (use PROJECT_VIEWER)"},
    # ── Canonical roles (authoritative RBAC model) ──────────────────────────
    {"name": "SUPER_ADMIN",    "description": "Global super administrator – creates orgs, approves Org Admin requests"},
    {"name": "ORG_ADMIN",      "description": "Organisation administrator – creates projects, manages Project Admins"},
    {"name": "PROJECT_ADMIN",  "description": "Project administrator – manages user roles within a project/stage"},
    {"name": "PROJECT_EDITOR", "description": "Project editor – enters/edits activity and component data"},
    {"name": "PROJECT_VIEWER", "description": "Project viewer – read-only access to assigned projects"},
    {"name": "GENERAL_USER",   "description": "Default role for newly registered users; basic org membership only – no project access until explicitly granted a project role by a PROJECT_ADMIN"},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in ROLES:
            result = await conn.execute(
                text(
                    "INSERT INTO roles (id, name, description, is_active, created_on) "
                    "VALUES (gen_random_uuid(), :name, :description, true, now()) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_roles] {inserted}/{len(ROLES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
