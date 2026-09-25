"""
Seed script: role_permissions
Inserts default role-permission mappings.
Idempotent — uses INSERT ... ON CONFLICT (role_id, permission_id) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_role_permissions
    
Prerequisites:
    - seed_roles.py must be run first
    - seed_permissions.py must be run first
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
from models.permissions import Permission


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    
    # Define role-permission mappings
    ROLE_PERMISSIONS = [
        # ── Legacy mappings ─────────────────────────────────────────────────
        ("Admin",  ["create_any", "read_any", "update_any", "delete_any"]),
        ("Editor", ["read_any", "update_any"]),
        ("Viewer", ["read_any"]),
        # ── SUPER_ADMIN: global scope ───────────────────────────────────────
        ("SUPER_ADMIN", [
            "ORG_CREATE",
            "ORG_ADMIN_APPOINT",
            "ORG_ADMIN_REQUEST_REVIEW",
            "ACCESS_VIEW",
            "REQUEST_REVIEW",
            "AUDIT_VIEW",
            # Also inherits all read access
            "read_any",
        ]),
        # ── ORG_ADMIN: organisation scope ───────────────────────────────────
        ("ORG_ADMIN", [
            "PROJECT_CREATE",
            "PROJECT_ASSIGN_PA",
            "ACCESS_VIEW",
            "REQUEST_REVIEW",
            "RESULTS_VIEW",
            "AUDIT_VIEW",
        ]),
        # ── PROJECT_ADMIN: project / stage scope ────────────────────────────
        ("PROJECT_ADMIN", [
            "ACCESS_ASSIGN_PROJECT",
            "ACCESS_ASSIGN_STAGE",
            "ACCESS_VIEW",
            "REQUEST_REVIEW",
            "APPROVE_TECHNICAL",
            "APPROVE_FINAL",
            "RESULTS_VIEW",
            "AUDIT_VIEW",
        ]),
        # ── PROJECT_EDITOR: project scope ───────────────────────────────────
        ("PROJECT_EDITOR", [
            "ACTIVITY_EDIT",
            "COMPONENT_EDIT",
            "RESULTS_VIEW",
        ]),
        # ── PROJECT_VIEWER: project scope ───────────────────────────────────
        ("PROJECT_VIEWER", [
            "RESULTS_VIEW",
        ]),
    ]

    async with engine.begin() as conn:
        # Fetch all roles and permissions
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Get all roles
            roles_result = await session.execute(select(Role).order_by(Role.name))
            roles_map = {role.name: role.id for role in roles_result.scalars().all()}
            
            # Get all permissions
            perms_result = await session.execute(select(Permission).order_by(Permission.name))
            perms_map = {perm.name: perm.id for perm in perms_result.scalars().all()}
        
        if not roles_map:
            print("[seed_role_permissions] ERROR: No roles found. Run seed_roles.py first.")
            await engine.dispose()
            return
        
        if not perms_map:
            print("[seed_role_permissions] ERROR: No permissions found. Run seed_permissions.py first.")
            await engine.dispose()
            return
        
        # Insert role-permission mappings
        inserted = 0
        for role_name, permission_names in ROLE_PERMISSIONS:
            role_id = roles_map.get(role_name)
            if not role_id:
                print(f"[seed_role_permissions] WARNING: Role '{role_name}' not found. Skipping.")
                continue
            
            for perm_name in permission_names:
                perm_id = perms_map.get(perm_name)
                if not perm_id:
                    print(f"[seed_role_permissions] WARNING: Permission '{perm_name}' not found. Skipping.")
                    continue
                
                result = await conn.execute(
                    text(
                        "INSERT INTO role_permissions (id, role_id, permission_id, created_on) "
                        "VALUES (gen_random_uuid(), :role_id, :permission_id, now()) "
                        "ON CONFLICT (role_id, permission_id) DO NOTHING"
                    ),
                    {"role_id": str(role_id), "permission_id": str(perm_id)},
                )
                inserted += result.rowcount
        
        print(f"[seed_role_permissions] {inserted} role-permission mappings inserted.")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
