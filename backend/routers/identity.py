from __future__ import annotations

import logging
from typing import Optional
from passlib.context import CryptContext

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.organization import get_organization
from crud.organization_domains import add_domain, domain_matches_org
from crud.access_requests import create_access_request
from crud.roles import get_role_by_name
from crud.user_roles import create_user_role
from crud.users import create_user, get_user_by_email
from crud.jurisdictions import get_jurisdiction_by_name
from core.config import settings
from core.security import parse_easy_auth_header
from models.organizations import Organization, Organization_Type
from schemas.identity import RegisterRequest, RegisterResponse
from schemas.access_requests import AccessRequestCreate
from schemas.users import UserCreate
from datetime import datetime, timezone
from crud import terms_documents as terms_documents_crud
from models.terms_documents import TermsDocumentType

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # kept for future re-enable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/identity", tags=["identity"])


class RegistrationContextResponse(BaseModel):
    needs_registration: bool
    email: Optional[str] = None


@router.get("/registration-context", response_model=RegistrationContextResponse)
async def registration_context(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Deployed mode only: tells the frontend whether the caller's forwarded identity
    already has an app account, and returns their verified email if not."""
    if settings.auth_mode != "forwarded_identity":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available in this environment.")
    email, _oidc_sub, _provider = parse_easy_auth_header(request)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Forwarded identity header missing or malformed.")
    existing = await get_user_by_email(db, email.lower())
    if existing:
        return RegistrationContextResponse(needs_registration=False, email=email.lower())
    return RegistrationContextResponse(needs_registration=True, email=email.lower())


def _resolve_registration_email(request: Request, payload: RegisterRequest) -> str:
    if settings.auth_mode == "forwarded_identity":
        email, _oidc_sub, _provider = parse_easy_auth_header(request)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Forwarded identity header missing or malformed.",
            )
        return email.lower()
    if not payload.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="email is required.",
        )
    return payload.email.lower()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_session),
):
    email = _resolve_registration_email(request, payload)

    # Enforced server-side — the frontend disabling the button is not sufficient on its own.
    if not payload.accepted_pics or not payload.accepted_terms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must accept the Personal Information Collection Statement and the CMRT Terms of Use to register.",
        )

    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    org_created = False
    org_id = payload.organisation_id
    
    if org_id is not None:
        org = await get_organization(db, org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organisation not found.",
            )
        if not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisation is inactive.",
            )
        if not await domain_matches_org(db, org_id, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Your email domain does not match this organisation's allowed domains. "
                    "Please use your corporate email address or request an invitation."
                ),
            )
        org_is_proponent = getattr(org, 'is_proponent', True)
        org_is_platform_operator = org.organization_type == Organization_Type.PLATFORM_OPERATOR

    else:
        if not payload.org_name or not payload.org_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="org_name and org_type are required when registering a new organisation.",
            )
        org_is_proponent = payload.is_proponent
        org_is_platform_operator = payload.org_type == "PLATFORM_OPERATOR"
        
        # Handle region lookup if region name is provided
        region_id = payload.region_id
        if payload.region and not region_id:
            jurisdiction = await get_jurisdiction_by_name(db, payload.region)
            if not jurisdiction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Region (jurisdiction) '{payload.region}' not found.",
                )
            region_id = jurisdiction.id
        
        # Validate region_id if provided
        if region_id:
            from crud.jurisdictions import get_jurisdiction
            jurisdiction = await get_jurisdiction(db, region_id)
            if not jurisdiction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Region (jurisdiction) with provided region_id not found.",
                )
        
        # Handle jurisdiction lookup if country is provided
        jurisdiction_id = None
        if payload.org_country:
            country_jurisdiction = await get_jurisdiction_by_name(db, payload.org_country, type="Country")
            
            if country_jurisdiction:
                jurisdiction_id = country_jurisdiction.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Country (jurisdiction) '{payload.org_country}' not found.",
                )
        
        org = Organization(
            name=payload.org_name,
            organization_type=Organization_Type(payload.org_type),
            country=payload.org_country,
            jurisdiction_id=jurisdiction_id,
            region_id=region_id,
            is_proponent=org_is_proponent,
            is_active=True,
        )
        db.add(org)
        await db.flush()
        org_id = org.id
        org_created = True

        email_domain = email.split("@")[-1]
        await add_domain(db, org_id, email_domain)

    # Server stamps the acceptance time/version — never trust a client-supplied timestamp.
    _acceptance_timestamp = datetime.now(timezone.utc)
    _active_pics = await terms_documents_crud.get_active(db, TermsDocumentType.PICS)
    _active_terms = await terms_documents_crud.get_active(db, TermsDocumentType.TERMS_OF_USE)
    _pics_version = _active_pics.version if _active_pics else None
    _terms_version = _active_terms.version if _active_terms else None

    user_payload = UserCreate(
        email=email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        organization_id=org_id,
        is_active=True,
        password_hash=None,
        pics_accepted=True,
        pics_accepted_at=_acceptance_timestamp,
        pics_version=_pics_version,
        terms_accepted=True,
        terms_accepted_at=_acceptance_timestamp,
        terms_version=_terms_version,
    )
    user = await create_user(db, user_payload)

    # Identity provider provisioning is owned by Azure Easy Auth before this endpoint runs.

    await write_audit_event(
        db,
        entity_type="user",
        entity_id=user.id,
        action="REGISTER",
        performed_by=user.id,
        performed_by_org=org_id,
        metadata={
            "email": user.email,
            "org_id": str(org_id),
            "org_created": org_created,
        },
    )

    gu_role = await get_role_by_name(db, "GENERAL_USER")
    if gu_role:
        await create_user_role(
            db,
            user_id=user.id,
            role_id=gu_role.id,
            scope_type="ORGANISATION",
            scope_id=org_id,
            is_active=True,
        )

    ar = None
    if org_is_proponent and (org_created or payload.org_admin_reason):
        from models.roles import Role
        role_res = await db.execute(select(Role).where(Role.name == "ORG_ADMIN"))
        oa_role = role_res.scalars().first()

        ar_payload = AccessRequestCreate(
            request_type="ORG_ADMIN",
            target_user_id=user.id,
            requested_role_id=oa_role.id if oa_role else None,
            scope_type="ORGANISATION",
            scope_id=org_id,
            organisation_id=org_id,
            reason=payload.org_admin_reason,
        )
        ar = await create_access_request(db, ar_payload, requester_user_id=user.id)

        await write_audit_event(
            db,
            entity_type="access_request",
            entity_id=ar.id,
            action="CREATE",
            performed_by=user.id,
            performed_by_org=org_id,
            metadata={"request_type": "ORG_ADMIN", "organisation_id": str(org_id)},
        )

    await db.commit()

    if org_created and org_is_proponent:
        msg = "Registration successful. Your Org Admin request has been submitted and is pending SUPER_ADMIN approval."
    elif org_created:
        msg = "Registration successful. Your new organisation has been created and you have been registered as a general member."
    else:
        msg = "Registration successful. You have been registered as a general member of the organisation."

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        organisation_id=org_id,
        jurisdiction_id=getattr(org, "jurisdiction_id", None) if org else None,
        region_id=getattr(org, "region_id", None) if org else None,
        org_created=org_created,
        org_admin_request_id=ar.id if ar else None,
        message=msg,
    )
