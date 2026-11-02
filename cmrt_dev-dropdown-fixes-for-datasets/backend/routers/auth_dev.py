"""
routers/auth_dev.py
===================
Development-only token minting endpoint.

SAFETY: This router is registered in main.py ONLY when APP_ENV=local.
        It must NEVER be reachable in staging or production.

Usage:
    POST /api/auth/dev/token
    { "email": "alice@example.com" }

    Returns a short-lived HS256 JWT that can be used as a Bearer token for
    all protected endpoints while AUTH_MODE=local_jwt.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.session import get_session
from crud.users import get_user_by_email

router = APIRouter(
    prefix="/api/auth/dev",
    tags=["auth-dev"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DevTokenRequest(BaseModel):
    email: EmailStr
    expires_in_minutes: int = 60


class DevTokenResponse(BaseModel):
    token_type: str = "bearer"
    expires_in: int          # seconds
    sub: str
    email: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/token",
    response_model=DevTokenResponse,
    summary="[DEV ONLY] Mint a local JWT for testing",
)
async def mint_dev_token(
    body: DevTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> DevTokenResponse:
    """
    Looks up the user by email and returns a signed JWT.
    The user must already exist in the database (created via seeding or
    the /api/identity/register endpoint).

    This endpoint is ONLY available when APP_ENV=local.
    """
    if settings.app_env != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in local development mode.",
        )

    user = await get_user_by_email(db, body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email '{body.email}'. "
                   "Seed the database or register via /api/identity/register first.",
        )

    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=body.expires_in_minutes)

    claims = {
        "sub": str(user.id),
        "email": user.email,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }

    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Mirror the production login behaviour: set httpOnly cookie.
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # local only — HTTP is fine here; this router is never mounted elsewhere
        samesite="lax",
        max_age=body.expires_in_minutes * 60,
        path="/",
    )

    return DevTokenResponse(
        expires_in=body.expires_in_minutes * 60,
        sub=str(user.id),
        email=user.email,
    )
