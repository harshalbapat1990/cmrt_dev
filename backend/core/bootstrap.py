"""Idempotent startup bootstrap — ensures the super-admin user always exists."""
import logging

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


async def ensure_super_admin(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        # Ensure SUPER_ADMIN role exists
        r = await conn.execute(
            text(
                "INSERT INTO roles (id, name, description, is_active, created_on) "
                "VALUES (gen_random_uuid(), 'SUPER_ADMIN', 'Global super administrator', true, now()) "
                "ON CONFLICT (name) DO NOTHING"
            )
        )
        logger.info("[bootstrap] SUPER_ADMIN role: %s", "inserted" if r.rowcount else "already exists")

        # In OIDC mode the super admin authenticates via Auth0 and is linked by email on first login.
        # In local_jwt mode, refresh the password hash so env-var changes take effect immediately.
        if settings.auth_mode == "local_jwt" and settings.super_admin_password:
            password_hash = _pwd.hash(settings.super_admin_password)
            r = await conn.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name, username, is_active, password_hash, created_on) "
                    "VALUES (gen_random_uuid(), :email, 'Admin', 'User', 'admin', true, :pw, now()) "
                    "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash"
                ),
                {"email": settings.super_admin_email, "pw": password_hash},
            )
        else:
            r = await conn.execute(
                text(
                    "INSERT INTO users (id, email, first_name, last_name, username, is_active, created_on) "
                    "VALUES (gen_random_uuid(), :email, 'Admin', 'User', 'admin', true, now()) "
                    "ON CONFLICT (email) DO NOTHING"
                ),
                {"email": settings.super_admin_email},
            )
        logger.info("[bootstrap] %s: %s", settings.super_admin_email, "inserted" if r.rowcount == 1 else "already exists")

        # Ensure SUPER_ADMIN/GLOBAL user_role mapping
        exists = await conn.execute(
            text(
                "SELECT 1 FROM user_roles ur "
                "JOIN users u ON u.id = ur.user_id "
                "JOIN roles ro ON ro.id = ur.role_id "
                "WHERE u.email = :email AND ro.name = 'SUPER_ADMIN' AND ur.scope_type = 'GLOBAL' AND ur.scope_id IS NULL"
            ),
            {"email": settings.super_admin_email},
        )
        if not exists.first():
            await conn.execute(
                text(
                    "INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id, is_active, created_on) "
                    "SELECT gen_random_uuid(), u.id, ro.id, 'GLOBAL', NULL, true, now() "
                    "FROM users u JOIN roles ro ON ro.name = 'SUPER_ADMIN' "
                    "WHERE u.email = :email"
                ),
                {"email": settings.super_admin_email},
            )
            logger.info("[bootstrap] %s -> SUPER_ADMIN role mapping: inserted", settings.super_admin_email)
        else:
            logger.info("[bootstrap] %s -> SUPER_ADMIN role mapping: already exists", settings.super_admin_email)
