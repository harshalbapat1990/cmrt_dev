from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.session import get_session


@dataclass
class Principal:
    user_id: uuid.UUID
    email: str
    oidc_issuer: Optional[str] = None
    oidc_sub: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None


_bearer_scheme = HTTPBearer(auto_error=False)


async def _resolve_user_from_db(
    db: AsyncSession,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
    oidc_issuer: Optional[str] = None,
    oidc_sub: Optional[str] = None,
) -> Principal:
    from sqlalchemy import select
    from models.users import User

    user: Optional[User] = None

    if user_id:
        try:
            uid = uuid.UUID(user_id)
            result = await db.execute(select(User).where(User.id == uid))
            user = result.scalars().first()
        except (ValueError, AttributeError):
            pass

    if user is None and oidc_issuer and oidc_sub:
        result = await db.execute(
            select(User).where(
                User.oidc_issuer == oidc_issuer,
                User.oidc_sub == oidc_sub,
            )
        )
        user = result.scalars().first()

    if user is None and email:
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalars().first()
        if user and oidc_issuer and oidc_sub and not user.oidc_sub:
            user.oidc_issuer = oidc_issuer
            user.oidc_sub = oidc_sub
            await db.flush()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Principal(
        user_id=user.id,
        email=user.email,
        oidc_issuer=user.oidc_issuer,
        oidc_sub=user.oidc_sub,
        organization_id=user.organization_id,
    )


async def _auth_local_jwt(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
) -> Principal:
    # Accept token from Authorization header (API clients) or httpOnly cookie (browser).
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header or session cookie missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: Optional[str] = payload.get("email")
    oidc_sub: Optional[str] = payload.get("sub")
    oidc_issuer: Optional[str] = payload.get("iss")

    return await _resolve_user_from_db(
        db,
        email=email,
        user_id=oidc_sub,
        oidc_issuer=oidc_issuer,
        oidc_sub=oidc_sub,
    )


def parse_easy_auth_header(request: Request) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (email, oidc_sub, provider) from Azure Easy Auth identity headers.

    In this architecture, the backend is private and these headers are not set by a
    backend-side Easy Auth — they are set by Azure Easy Auth at the public frontend
    Container App boundary and forwarded to the backend by the frontend's server-side
    proxy (client/server.js). The header format is unchanged from Azure's App Service
    schema, so this parser is reused as-is.

    Prefers the simple X-MS-CLIENT-PRINCIPAL-ID/-NAME/-IDP headers. Falls back to
    decoding X-MS-CLIENT-PRINCIPAL, whose payload is a claims array
    (`{"auth_typ", "claims": [{"typ", "val"}], ...}`) per App Service's documented
    schema — NOT the flat userId/userDetails shape used by Static Web Apps.
    """
    principal_id = request.headers.get("x-ms-client-principal-id")
    principal_name = request.headers.get("x-ms-client-principal-name")
    provider = request.headers.get("x-ms-client-principal-idp")
    if principal_id or principal_name:
        return principal_name, principal_id, provider

    header_value = request.headers.get("x-ms-client-principal")
    if not header_value:
        return None, None, None
    try:
        padding = "=" * (-len(header_value) % 4)
        decoded = base64.b64decode(header_value + padding).decode("utf-8")
        principal_data = json.loads(decoded)
    except Exception:
        return None, None, None

    claims = {
        c.get("typ"): c.get("val")
        for c in principal_data.get("claims", [])
        if isinstance(c, dict)
    }
    email: Optional[str] = (
        claims.get("emails")
        or claims.get("email")
        or claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        or claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
    )
    oidc_sub: Optional[str] = (
        claims.get("sub")
        or claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
    )
    provider = provider or principal_data.get("auth_typ")
    return email, oidc_sub, provider


def has_forwarded_identity_header(request: Request) -> bool:
    return any(
        request.headers.get(header)
        for header in (
            "x-ms-client-principal",
            "x-ms-client-principal-id",
            "x-ms-client-principal-name",
        )
    )


async def _auth_forwarded_identity(
    request: Request,
    db: AsyncSession,
) -> Principal:
    email, oidc_sub, provider = parse_easy_auth_header(request)
    if not email and not oidc_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forwarded identity header missing or malformed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _resolve_user_from_db(
        db,
        email=email,
        oidc_issuer=provider,
        oidc_sub=oidc_sub,
    )



async def get_current_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> Principal:
    if settings.auth_mode == "local_jwt" and settings.app_env == "local":
        principal = await _auth_local_jwt(request, credentials, db)
    else:
        if not has_forwarded_identity_header(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Forwarded identity header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal = await _auth_forwarded_identity(request, db)
    from core.audit_context import AuditActorContext, set_audit_actor
    from models.users import User as UserModel
    from models.organizations import Organization
    from sqlalchemy.future import select as _select

    _user_row = (await db.execute(
        _select(UserModel.first_name, UserModel.last_name, UserModel.email)
        .where(UserModel.id == principal.user_id)
    )).first()
    if _user_row:
        _display = f"{_user_row.first_name or ''} {_user_row.last_name or ''}".strip() or _user_row.email or principal.email
    else:
        _display = principal.email

    _org_name = None
    if principal.organization_id:
        _org_name = (await db.execute(
            _select(Organization.name).where(Organization.id == principal.organization_id)
        )).scalar_one_or_none()

    set_audit_actor(AuditActorContext(
        user_id=principal.user_id,
        display_name=_display,
        org_id=principal.organization_id,
        org_name=_org_name,
    ))

    return principal


async def get_optional_principal(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> Optional[Principal]:
    try:
        return await get_current_principal(request, credentials, db)
    except HTTPException:
        return None
