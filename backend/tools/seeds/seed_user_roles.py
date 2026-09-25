"""
Seed script: user_roles
Inserts default user-role mappings.
Idempotent — uses INSERT ... ON CONFLICT (user_id, role_id, scope_type, scope_id) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_user_roles
    
Prerequisites:
    - Users must exist in the users table
    - seed_roles.py must be run first
    
Note:
    This script maps admin/test users to roles. Modify USER_ROLES if you have different users.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
from models.roles import Role
from models.users import User


# Map user emails to roles (and optionally scope)
USER_ROLES = [
    # Format: (user_email, role_name, scope_type, scope_id, is_active)
    # scope_type must be GLOBAL / ORGANISATION / PROJECT / STAGE
    ("admin@example.com",  "SUPER_ADMIN",    "GLOBAL", None, True),
    ("orgadmin@example.com", "ORG_ADMIN", "GLOBAL", None, True),
    ("editor@example.com", "PROJECT_EDITOR", "GLOBAL", None, True),
    ("viewer@example.com", "PROJECT_VIEWER", "GLOBAL", None, True),
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        async with async_session() as session:
            # Get all roles by name
            roles_result = await session.execute(select(Role).order_by(Role.name))
            roles_map = {role.name: role.id for role in roles_result.scalars().all()}
            
            # Get all users by email
            users_result = await session.execute(select(User).order_by(User.email))
            users_map = {user.email: user.id for user in users_result.scalars().all()}
        
        if not roles_map:
            print("[seed_user_roles] ERROR: No roles found. Run seed_roles.py first.")
            await engine.dispose()
            return
        
        if not users_map:
            print("[seed_user_roles] WARNING: No users found in database.")
            print("[seed_user_roles] Please create users first via the API or database.")
            print(f"[seed_user_roles] Expected users: {[email for email, _, _, _, _ in USER_ROLES]}")
            await engine.dispose()
            return
        
        # Insert user-role mappings
        inserted = 0
        skipped = 0
        
        for user_email, role_name, scope_type, scope_id, is_active in USER_ROLES:
            user_id = users_map.get(user_email)
            if not user_id:
                print(f"[seed_user_roles] SKIPPED: User '{user_email}' not found in database.")
                skipped += 1
                continue
            
            role_id = roles_map.get(role_name)
            if not role_id:
                print(f"[seed_user_roles] SKIPPED: Role '{role_name}' not found.")
                skipped += 1
                continue
            
            # Use a SELECT+INSERT pattern because our unique constraints are partial indexes
            # (Postgres ON CONFLICT cannot reference partial index names directly)
            if scope_id is None:
                existing = await conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM user_roles
                        WHERE user_id = :user_id
                        AND role_id = :role_id
                        AND scope_type = :scope_type
                        AND scope_id IS NULL
                        """
                    ),
                    {
                        "user_id": str(user_id),
                        "role_id": str(role_id),
                        "scope_type": scope_type,
                    },
                )
            else:
                existing = await conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM user_roles
                        WHERE user_id = :user_id
                        AND role_id = :role_id
                        AND scope_type = :scope_type
                        AND scope_id = CAST(:scope_id AS uuid)
                        """
                    ),
                    {
                        "user_id": str(user_id),
                        "role_id": str(role_id),
                        "scope_type": scope_type,
                        "scope_id": str(scope_id),
                    },
            )
            if existing.first():
                skipped += 1
                continue

            result = await conn.execute(
                text(
                    "INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id, is_active, created_on) "
                    "VALUES (gen_random_uuid(), :user_id, :role_id, :scope_type, :scope_id, :is_active, now())"
                ),
                {
                    "user_id": str(user_id),
                    "role_id": str(role_id),
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "is_active": is_active,
                },
            )
            inserted += result.rowcount
        
        print(f"[seed_user_roles] {inserted} user-role mappings inserted, {skipped} skipped.")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
