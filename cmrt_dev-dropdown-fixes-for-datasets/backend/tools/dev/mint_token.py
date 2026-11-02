"""
tools/dev/mint_token.py
=======================
LOCAL-ONLY helper to mint a signed HS256 JWT for testing authenticated
endpoints before the frontend wires up real auth.

Usage (from the backend/ directory):
    python -m tools.dev.mint_token --email admin@example.com

The token should then be sent as:
    Authorization: Bearer <token>

⚠️  NEVER use this in production. This script will refuse to run unless
    AUTH_MODE=local_jwt and APP_ENV is one of: local, dev.
"""

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.config import settings


def _mint(email: str, sub: Optional[str] = None, extra_claims: dict | None = None) -> str:
    from jose import jwt

    if settings.auth_mode != "local_jwt":
        raise SystemExit("This tool only works when AUTH_MODE=local_jwt")
    if settings.app_env.lower() not in ("local", "dev"):
        raise SystemExit("This tool only works when APP_ENV=local or APP_ENV=dev")

    now = datetime.now(tz=timezone.utc)
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": sub or f"dev|{uuid.uuid4()}",
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Optional: resolve user from DB to include real sub if stored ──────────────
async def _get_db_sub(email: str) -> str | None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from models.users import User

    if not settings.database_url:
        return None
    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalars().first()
    await engine.dispose()
    return user.oidc_sub if user and user.oidc_sub else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mint a dev JWT for local API testing")
    parser.add_argument("--email", required=True, help="User email (must exist in DB)")
    parser.add_argument("--sub", default=None, help="Override OIDC sub claim")
    args = parser.parse_args()

    # Try to look up an existing sub from DB (best-effort)
    db_sub = None
    if settings.database_url:
        try:
            db_sub = asyncio.run(_get_db_sub(args.email))
        except Exception:
            pass

    token = _mint(args.email, sub=args.sub or db_sub)
    print("\n=== Dev JWT (local only) ===")
    print(f"  Email  : {args.email}")
    print(f"  Expires: {settings.jwt_expire_minutes} minutes")
    print("\n  Token:")
    print(f"  {token}")
    print("\n  curl header:")
    print(f'  -H "Authorization: Bearer {token}"')
    print("=" * 40)


if __name__ == "__main__":
    main()
