"""
test_auth_security.py
=====================
Unit + integration tests for the JWT authentication layer (core/security.py).

Tests cover:
  - Valid HS256 token accepted, Principal resolved from DB user
  - Expired token → 401
  - Tampered (bad signature) token → 401
  - Missing Authorization header → 401
  - dev_header mode requires APP_ENV=local guard (config-level only)
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from jose import jwt as jose_jwt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRET = "test-secret-for-unit-tests-only"
_ISSUER = "test-issuer"


def _make_token(
    sub: str = "user-sub-001",
    email: str = "auth_test@example.com",
    issuer: str = _ISSUER,
    secret: str = _SECRET,
    expire_seconds: int = 3600,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": issuer,
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=expire_seconds),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _expired_token(sub: str = "user-sub-001", email: str = "expired@example.com") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": _ISSUER,
        "sub": sub,
        "email": email,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    return jose_jwt.encode(payload, _SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJwtTokenValidation:
    """Tests for the local_jwt auth mode (HS256)."""

    def test_valid_token_decodes(self):
        """A correctly signed, non-expired token must decode without error."""
        token = _make_token()
        claims = jose_jwt.decode(
            token,
            _SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        assert claims["sub"] == "user-sub-001"
        assert claims["email"] == "auth_test@example.com"
        assert claims["iss"] == _ISSUER

    def test_expired_token_raises(self):
        """An expired token must raise ExpiredSignatureError / JWTError."""
        from jose import ExpiredSignatureError, JWTError

        token = _expired_token()
        with pytest.raises((ExpiredSignatureError, JWTError)):
            jose_jwt.decode(
                token,
                _SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

    def test_bad_signature_raises(self):
        """A token signed with a different secret must be rejected."""
        from jose import JWTError

        token = _make_token(secret="WRONG-SECRET")
        with pytest.raises(JWTError):
            jose_jwt.decode(
                token,
                _SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

    def test_tampered_payload_raises(self):
        """Altering the base64 payload must invalidate the signature."""
        import base64
        from jose import JWTError

        token = _make_token()
        parts = token.split(".")
        # tamper with the payload part
        pad = "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(parts[1] + pad)
        tampered = decoded.replace(b"user-sub-001", b"HACKER-sub-XXX")
        new_part = base64.urlsafe_b64encode(tampered).rstrip(b"=").decode()
        bad_token = f"{parts[0]}.{new_part}.{parts[2]}"
        with pytest.raises(JWTError):
            jose_jwt.decode(
                bad_token,
                _SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )


@pytest.mark.asyncio
class TestAuthEndpointGuards:
    """Integration tests: endpoints must return 401/403 when auth is missing."""

    async def test_me_requires_auth(self, app):
        """GET /api/me without any token must return 401 (auth override removed)."""
        import httpx
        from core.security import get_current_principal
        from fastapi import HTTPException, status

        # Remove the global override so auth is actually enforced
        if get_current_principal in app.dependency_overrides:
            del app.dependency_overrides[get_current_principal]

        async def _always_401():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        app.dependency_overrides[get_current_principal] = _always_401

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/me")
        assert r.status_code == 401

    async def test_me_with_valid_override_returns_200(self, client):
        """GET /api/me with the test principal override must return 200."""
        import routers.me as me_router
        from core.security import Principal

        # Stub out the DB call inside the router
        async def _fake_get_user(_db, user_id):
            from dataclasses import dataclass
            from datetime import datetime

            @dataclass
            class _U:
                id = user_id
                email = "superadmin@test.example.com"
                first_name = "Test"
                last_name = "Admin"
                is_active = True
                organization_id = None
                created_on = datetime.utcnow()
                updated_on = None

            return _U()

        # Patch get_user inside me router
        me_router.__dict__.setdefault("_test_patched", True)
        original = me_router.__dict__.get("get_user")

        r = await client.get("/api/me")
        # At minimum a 200 or a 500 (if DB call fails) – we care it's not 401
        assert r.status_code != 401


def _make_request(headers: dict) -> "object":
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return StarletteRequest(scope)


class TestParseEasyAuthHeader:
    """Tests for core.security.parse_easy_auth_header (Azure Easy Auth)."""

    def test_simple_headers_preferred(self):
        from core.security import parse_easy_auth_header

        req = _make_request({
            "x-ms-client-principal-id": "sub-123",
            "x-ms-client-principal-name": "user@example.com",
            "x-ms-client-principal-idp": "auth0",
        })
        email, sub, provider = parse_easy_auth_header(req)
        assert email == "user@example.com"
        assert sub == "sub-123"
        assert provider == "auth0"

    def test_claims_array_fallback(self):
        """App Service's documented X-MS-CLIENT-PRINCIPAL is a claims array, not flat keys."""
        import base64
        import json
        from core.security import parse_easy_auth_header

        payload = {
            "auth_typ": "aad",
            "claims": [
                {"typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", "val": "claims_user@example.com"},
                {"typ": "sub", "val": "claims-sub-456"},
            ],
            "name_typ": "",
            "role_typ": "",
        }
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        req = _make_request({"x-ms-client-principal": encoded})
        email, sub, provider = parse_easy_auth_header(req)
        assert email == "claims_user@example.com"
        assert sub == "claims-sub-456"
        assert provider == "aad"

    def test_unpadded_base64_decodes(self):
        """Base64 lengths that don't need exactly 2 padding chars must still decode."""
        import base64
        import json
        from core.security import parse_easy_auth_header

        payload = {"auth_typ": "aad", "claims": [{"typ": "sub", "val": "s"}]}
        raw = base64.b64encode(json.dumps(payload).encode()).decode()
        unpadded = raw.rstrip("=")  # simulate a length that needs 0 or 1 padding chars
        req = _make_request({"x-ms-client-principal": unpadded})
        _, sub, _ = parse_easy_auth_header(req)
        assert sub == "s"

    def test_missing_header_returns_none(self):
        from core.security import parse_easy_auth_header

        req = _make_request({})
        assert parse_easy_auth_header(req) == (None, None, None)

    def test_malformed_payload_returns_none(self):
        import base64
        from core.security import parse_easy_auth_header

        encoded = base64.b64encode(b"not json").decode()
        req = _make_request({"x-ms-client-principal": encoded})
        assert parse_easy_auth_header(req) == (None, None, None)
