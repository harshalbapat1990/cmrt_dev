"""
Seed script: users
Inserts default test users.
Idempotent — uses INSERT ... ON CONFLICT (email) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_users
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default passwords for seeded dev/test users.
# These are development credentials only — never use in production.
_DEFAULT_PASSWORDS: dict[str, str] = {
    "admin@example.com":  "Admin1234!",
    "orgadmin@example.com": "OrgAdmin1234!",
    "editor@example.com": "Editor1234!",
    "viewer@example.com": "Viewer1234!",
    "test@example.com":   "Test1234!",
}

USERS = [
    {
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "username": "admin",
        "is_active": True,
    },
    {
        "email": "orgadmin@example.com",
        "first_name": "Org",
        "last_name": "Admin",
        "username": "orgadmin",
        "is_active": True,
    },
    {
        "email": "editor@example.com",
        "first_name": "Editor",
        "last_name": "User",
        "username": "editor",
        "is_active": True,
    },
    {
        "email": "viewer@example.com",
        "first_name": "Viewer",
        "last_name": "User",
        "username": "viewer",
        "is_active": True,
    },
    {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "is_active": True,
    },
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in USERS:
            password_hash = _pwd_context.hash(_DEFAULT_PASSWORDS[row["email"]])
            result = await conn.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name, username, is_active, password_hash, created_on) "
                    "VALUES (gen_random_uuid(), :email, :first_name, :last_name, :username, :is_active, :password_hash, now()) "
                    "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash"
                ),
                {**row, "password_hash": password_hash},
            )
            inserted += result.rowcount
        print(f"[seed_users] {inserted}/{len(USERS)} rows upserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
