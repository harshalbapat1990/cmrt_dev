"""One-off: assign canonical SUPER_ADMIN role to seeded users."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

ASSIGNMENTS = [
    ("admin@example.com",  "SUPER_ADMIN",    "GLOBAL"),
    ("editor@example.com", "PROJECT_EDITOR", "GLOBAL"),
    ("viewer@example.com", "PROJECT_VIEWER", "GLOBAL"),
]

async def go():
    e = create_async_engine(settings.database_url, echo=False)
    async with e.begin() as c:
        for email, role_name, scope in ASSIGNMENTS:
            r = await c.execute(text("""
                INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id, is_active, created_on)
                SELECT gen_random_uuid(), u.id, ro.id, CAST(:scope AS text), NULL, true, now()
                FROM users u
                JOIN roles ro ON ro.name = CAST(:role_name AS text)
                WHERE u.email = CAST(:email AS text)
                AND NOT EXISTS (
                    SELECT 1 FROM user_roles ur2
                    WHERE ur2.user_id = u.id AND ur2.role_id = ro.id AND ur2.scope_type = CAST(:scope AS text)
                )
            """), {"email": email, "role_name": role_name, "scope": scope})
            print(f"{'INSERTED' if r.rowcount else 'already exists':10s}  {email}  ->  {role_name}")

        print()
        print("=== admin@example.com roles ===")
        r2 = await c.execute(text("""
            SELECT ro.name, ur.scope_type, ur.is_active
            FROM user_roles ur
            JOIN roles ro ON ro.id = ur.role_id
            JOIN users u ON u.id = ur.user_id
            WHERE u.email = 'admin@example.com'
        """))
        for row in r2.fetchall():
            print(f"  {row[0]:20s}  scope={row[1]}  active={row[2]}")

    await e.dispose()

if __name__ == "__main__":
    asyncio.run(go())
