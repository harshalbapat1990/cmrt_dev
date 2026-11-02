from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from crud.project import _build_project_partner_link
from schemas.partner_organizations import normalize_partner_name
from schemas.project import OrgLinkIn


def test_partner_name_normalization_collapses_case_and_whitespace():
    assert normalize_partner_name("  acme   road  ") == "ACME ROAD"
    assert normalize_partner_name("Acme Road") == "ACME ROAD"


def test_project_partner_link_requires_exactly_one_directory_or_custom_value():
    with pytest.raises(ValidationError):
        OrgLinkIn(role="DESIGNER")
    with pytest.raises(ValidationError):
        OrgLinkIn(
            partner_organization_id=uuid4(),
            custom_partner_name="Typed name",
            role="DESIGNER",
        )


@pytest.mark.asyncio
async def test_custom_project_partner_stays_project_local_and_does_not_create_registered_org():
    project_id = uuid4()
    link = OrgLinkIn(custom_partner_name="  A New Design Studio  ", role="DESIGNER")

    project_link = await _build_project_partner_link(db=None, project_id=project_id, link=link)

    assert project_link.project_id == project_id
    assert project_link.partner_organization_id is None
    assert project_link.custom_partner_name == "A New Design Studio"
    assert project_link.role == "DESIGNER"


@pytest.mark.asyncio
async def test_partner_suggestion_is_a_separate_record_from_registered_organizations(
    client, organization_store, monkeypatch
):
    import routers.partner_organizations as partner_router
    from models.partner_organizations import PartnerOrganizationSuggestion

    suggestion = PartnerOrganizationSuggestion(
        id=uuid4(),
        name="New Civil Studio",
        normalized_name="NEW CIVIL STUDIO",
        partner_type="DESIGNERS",
        status="pending",
        submitted_by_user_id=uuid4(),
        created_at=datetime.utcnow(),
    )

    async def submit(_db, _payload, _user_id):
        return suggestion, True

    monkeypatch.setattr(partner_router, "submit_partner_suggestion", submit)
    response = await client.post(
        "/api/partner-organizations/suggestions",
        json={"name": " New Civil   Studio ", "partner_type": "DESIGNERS"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    assert organization_store == {}


@pytest.mark.asyncio
async def test_only_super_admins_can_review_partner_suggestions(client, monkeypatch):
    import core.rbac as rbac

    async def no_roles(_db, _user_id, project_id=None):
        return []

    monkeypatch.setattr(rbac, "get_effective_role_names", no_roles)
    response = await client.post(
        f"/api/partner-organizations/suggestions/{uuid4()}/review",
        json={"decision": "approved"},
    )

    assert response.status_code == 403
