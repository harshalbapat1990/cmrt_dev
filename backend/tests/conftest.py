from __future__ import annotations

import sys
from pathlib import Path

# Ensure imports like `from app.main import app` work no matter where pytest is invoked from.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import httpx

from app.main import app as fastapi_app
from core.session import get_session


@dataclass
class DummyUser:
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    oidc_sub: Optional[str] = None
    oidc_issuer: Optional[str] = None
    organization_id: Optional[UUID] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    password_hash: Optional[str] = None
    pics_accepted: bool = False
    pics_accepted_at: Optional[datetime] = None
    pics_version: Optional[int] = None
    terms_accepted: bool = False
    terms_accepted_at: Optional[datetime] = None
    terms_version: Optional[int] = None


class _FakeScalars:
    """Mimics the scalars() result object returned by async DB sessions."""

    def __init__(self, items=None):
        self._items = list(items or [])

    def first(self):
        return self._items[0] if self._items else None

    def one_or_none(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items

    def __iter__(self):
        return iter(self._items)


class _FakeResult:
    """Mimics the result object returned by `await db.execute(...)`."""

    def __init__(self, items=None):
        self._items = list(items or [])

    def scalars(self):
        return _FakeScalars(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._items[0] if self._items else None

    def one_or_none(self):
        return self._items[0] if self._items else None

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


class FakeSession:
    """In-memory stub for SQLAlchemy AsyncSession.

    Tests that exercise raw ``db.execute`` / ``db.add`` / ``db.flush`` calls
    can supply ``_execute_results`` to control what ``execute()`` returns.
    """

    def __init__(self, execute_returns=None):
        # list of items to return for successive execute() calls (FIFO)
        self._execute_queue: list = list(execute_returns or [])
        self._added: list = []

    async def commit(self) -> None:
        return None

    async def execute(self, query):
        if self._execute_queue:
            items = self._execute_queue.pop(0)
            return _FakeResult(items if isinstance(items, list) else [items])
        return _FakeResult([])

    def add(self, obj) -> None:
        self._added.append(obj)

    async def flush(self) -> None:
        # Assign fake UUIDs to any add()ed ORM objects whose id is still None.
        import uuid as _uuid
        for obj in self._added:
            try:
                if getattr(obj, "id", None) is None:
                    obj.id = _uuid.uuid4()
            except Exception:
                pass
        self._added.clear()

    async def rollback(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        """No-op: objects are already in-memory; no DB round-trip needed."""
        return None


@dataclass
class DummyOrganization:
    id: UUID
    name: str
    organization_type: str
    is_active: bool = True
    is_proponent: bool = True
    jurisdiction_id: Optional[UUID] = None
    region_id: Optional[UUID] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


@pytest.fixture
def app():
    # Override DB session dependency so tests don't need a real database.
    async def override_get_session() -> AsyncIterator[FakeSession]:
        yield FakeSession()

    from core.security import get_current_principal, Principal

    _test_principal_id = uuid4()

    async def override_get_principal() -> Principal:
        return Principal(
            user_id=_test_principal_id,
            email="superadmin@test.example.com",
            oidc_issuer="test-issuer",
            oidc_sub="test-sub-001",
            organization_id=None,
        )

    fastapi_app.dependency_overrides[get_session] = override_get_session
    fastapi_app.dependency_overrides[get_current_principal] = override_get_principal
    return fastapi_app


@pytest.fixture(autouse=True)
def patch_rbac_core(monkeypatch: pytest.MonkeyPatch):
    """Globally stub RBAC checks so all existing tests keep passing.

    Tests that specifically exercise RBAC logic should override these within
    their own fixtures (narrower monkeypatch scope wins because it's applied
    last).
    """
    import core.rbac as rbac_module

    async def _all_roles(_db, user_id, project_id=None):
        from core.rbac import SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER
        return [SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER]

    async def _org_roles(_db, user_id, organisation_id):
        from core.rbac import SUPER_ADMIN, ORG_ADMIN
        return [SUPER_ADMIN, ORG_ADMIN]

    async def _validate_scope_noop(_db, scope_type, scope_id, caller):
        pass

    async def _assert_grant_noop(_db, caller, target_role_name, scope_type, scope_id):
        pass

    monkeypatch.setattr(rbac_module, "get_effective_role_names", _all_roles)
    monkeypatch.setattr(rbac_module, "get_org_scoped_role_names", _org_roles)
    monkeypatch.setattr(rbac_module, "validate_scope", _validate_scope_noop)
    monkeypatch.setattr(rbac_module, "assert_can_grant_role", _assert_grant_noop)


@pytest.fixture(autouse=True)
def patch_audit_log(monkeypatch: pytest.MonkeyPatch):
    """Stub out audit log writes so tests don't need the audit_logs table."""
    import crud.audit_logs as audit_module

    async def _noop(_db, **kwargs):
        pass

    monkeypatch.setattr(audit_module, "write_audit_event", _noop)

    # Also patch in every router that imported write_audit_event directly.
    for router_module_name in (
        "routers.user_roles",
        "routers.organization",
        "routers.project",
        "routers.access_requests",
        "routers.identity",
        "routers.me",
        "routers.organization_domains",
    ):
        try:
            import importlib
            m = importlib.import_module(router_module_name)
            if hasattr(m, "write_audit_event"):
                monkeypatch.setattr(m, "write_audit_event", _noop)
        except ImportError:
            pass


@pytest.fixture(autouse=True)
def patch_rbac_in_routers(monkeypatch: pytest.MonkeyPatch):
    """Patch RBAC helper imports inside each router module's namespace."""
    import importlib
    from core.rbac import SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER

    async def _validate_scope_noop(_db, scope_type, scope_id, caller):
        pass

    async def _assert_grant_noop(_db, caller, target_role_name, scope_type, scope_id):
        pass

    async def _all_roles(_db, user_id, project_id=None):
        return [SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER]

    async def _org_roles(_db, user_id, organisation_id):
        return [SUPER_ADMIN, ORG_ADMIN]

    async def _no_admin_projects(_db, user_id):
        # Default: no specific project admin IDs — SA path bypasses this anyway.
        return []

    for mod_name in ("routers.user_roles", "routers.project", "routers.organization",
                     "routers.access_requests", "routers.organization_domains"):
        try:
            m = importlib.import_module(mod_name)
            for name, val in (
                ("validate_scope", _validate_scope_noop),
                ("assert_can_grant_role", _assert_grant_noop),
                ("get_effective_role_names", _all_roles),
                ("get_org_scoped_role_names", _org_roles),
                ("get_project_ids_where_admin", _no_admin_projects),
            ):
                if hasattr(m, name):
                    monkeypatch.setattr(m, name, val)
        except ImportError:
            pass

    # Stub get_role in user_roles router so the role-name lookup never hits FakeSession.
    try:
        import routers.user_roles as _ur
        from dataclasses import dataclass as _dc

        @_dc
        class _StubRole:
            name: str = "PROJECT_VIEWER"

        async def _get_role_stub(_db, role_id):
            return _StubRole()

        if hasattr(_ur, "get_role"):
            monkeypatch.setattr(_ur, "get_role", _get_role_stub)
    except ImportError:
        pass


@pytest.fixture
def user_store() -> Dict[UUID, DummyUser]:
    return {}


@pytest.fixture
def organization_store() -> Dict[UUID, DummyOrganization]:
    return {}


@pytest.fixture(autouse=True)
def patch_users_crud(monkeypatch: pytest.MonkeyPatch, user_store: Dict[UUID, DummyUser]):
    # The router imports CRUD functions directly, so patch in routers.users.
    import routers.users as users_router

    async def create_user(_db, payload):
        user_id = uuid4()
        now = datetime.utcnow()
        data = payload.model_dump()
        obj = DummyUser(id=user_id, created_on=now, updated_on=None, **data)
        user_store[user_id] = obj
        return obj

    async def get_user(_db, user_id: UUID):
        return user_store.get(user_id)

    async def get_user_by_email(_db, email: str):
        for obj in user_store.values():
            if obj.email == email:
                return obj
        return None

    async def list_users(_db, skip: int = 0, limit: int = 50, is_active=None):
        items = list(user_store.values())
        if is_active is not None:
            items = [u for u in items if u.is_active is is_active]
        return items[skip : skip + limit]

    async def update_user(_db, obj: DummyUser, payload):
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)
        obj.updated_on = datetime.utcnow()
        return obj

    async def delete_user(_db, user_id: UUID) -> bool:
        return user_store.pop(user_id, None) is not None

    monkeypatch.setattr(users_router, "create_user", create_user)
    monkeypatch.setattr(users_router, "get_user", get_user)
    monkeypatch.setattr(users_router, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(users_router, "list_users", list_users)
    monkeypatch.setattr(users_router, "update_user", update_user)
    monkeypatch.setattr(users_router, "delete_user", delete_user)


@pytest.fixture(autouse=True)
def patch_organizations_crud(
    monkeypatch: pytest.MonkeyPatch, organization_store: Dict[UUID, DummyOrganization]
):
    import routers.organization as organization_router

    async def create_organization(_db, payload):
        organization_id = uuid4()
        now = datetime.utcnow()
        data = payload.model_dump()
        org_type = getattr(data.get("organization_type"), "value", data.get("organization_type"))
        obj = DummyOrganization(
            id=organization_id,
            name=data["name"],
            organization_type=org_type,
            is_active=data.get("is_active", True),
            created_on=now,
            updated_on=None,
        )
        # unique name (case-insensitive)
        for existing in organization_store.values():
            if existing.name.lower() == obj.name.lower():
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Organization name already exists",
                )
        organization_store[organization_id] = obj
        return obj

    async def get_organization(_db, organization_id: UUID):
        return organization_store.get(organization_id)

    async def list_organizations(_db, skip: int = 0, limit: int = 50, is_active=None, organization_type=None, q=None):
        items = list(organization_store.values())
        if is_active is not None:
            items = [o for o in items if o.is_active is is_active]
        if organization_type:
            items = [o for o in items if o.organization_type == organization_type]
        if q:
            q_lower = q.lower()
            items = [o for o in items if q_lower in o.name.lower()]
        items.sort(key=lambda o: o.name)
        return items[skip : skip + limit]

    async def update_organization(_db, obj: DummyOrganization, payload):
        update_data = payload.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"]:
            new_name = update_data["name"]
            for existing in organization_store.values():
                if existing.id != obj.id and existing.name.lower() == new_name.lower():
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Organization name already exists",
                    )
            obj.name = new_name

        if "organization_type" in update_data and update_data["organization_type"]:
            obj.organization_type = getattr(update_data["organization_type"], "value", update_data["organization_type"])

        if "is_active" in update_data and update_data["is_active"] is not None:
            obj.is_active = update_data["is_active"]

        obj.updated_on = datetime.utcnow()
        return obj

    async def delete_organization(_db, organization_id: UUID) -> bool:
        return organization_store.pop(organization_id, None) is not None

    monkeypatch.setattr(organization_router, "create_organization", create_organization)
    monkeypatch.setattr(organization_router, "get_organization", get_organization)
    monkeypatch.setattr(organization_router, "list_organizations", list_organizations)
    monkeypatch.setattr(organization_router, "update_organization", update_organization)
    monkeypatch.setattr(organization_router, "delete_organization", delete_organization)


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Jurisdictions & Staging Model — dummy types and stores
# ---------------------------------------------------------------------------


@dataclass
class DummyJurisdiction:
    id: UUID
    name: str
    code: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[UUID] = None
    created_at: Optional[datetime] = None


@dataclass
class DummyAnzReportingStage:
    id: UUID
    name: str
    sequence: int = 0
    created_at: Optional[datetime] = None


@dataclass
class DummyJurisdictionReportingStage:
    id: UUID
    jurisdiction_id: UUID
    anz_reporting_stage_id: UUID
    name: str
    sequence: int = 0
    created_at: Optional[datetime] = None


@dataclass
class DummyGhgScope:
    id: int
    name: str


@dataclass
class DummyUnit:
    id: UUID
    code: str


@dataclass
class DummyUnitConversion:
    id: UUID
    from_unit_id: UUID
    to_unit_id: UUID
    factor: Decimal
    from_unit: Optional[DummyUnit] = None
    to_unit: Optional[DummyUnit] = None


@dataclass
class DummyEmissionsCategory:
    id: UUID
    name: str
    code: Optional[str] = None
    scope: Optional[int] = None
    parent_category_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool = True
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None


# -- stores ------------------------------------------------------------------


@pytest.fixture
def jurisdiction_store() -> Dict[UUID, DummyJurisdiction]:
    return {}


@pytest.fixture
def anz_stage_store() -> Dict[UUID, DummyAnzReportingStage]:
    return {}


@pytest.fixture
def jrs_store() -> Dict[UUID, DummyJurisdictionReportingStage]:
    """Jurisdiction Reporting Stage store."""
    return {}


@pytest.fixture
def ghg_scope_store() -> Dict[int, DummyGhgScope]:
    return {
        1: DummyGhgScope(id=1, name="Scope 1"),
        2: DummyGhgScope(id=2, name="Scope 2"),
        3: DummyGhgScope(id=3, name="Scope 3"),
    }


@pytest.fixture
def unit_store() -> Dict[UUID, DummyUnit]:
    return {}


@pytest.fixture
def unit_conversion_store() -> Dict[UUID, DummyUnitConversion]:
    return {}


@pytest.fixture
def emissions_category_store() -> Dict[UUID, DummyEmissionsCategory]:
    return {}


# -- patches -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_jurisdictions_crud(
    monkeypatch: pytest.MonkeyPatch,
    jurisdiction_store: Dict[UUID, DummyJurisdiction],
    jrs_store: Dict[UUID, DummyJurisdictionReportingStage],
):
    import routers.jurisdictions as j_router

    async def create_jurisdiction(_db, payload):
        obj = DummyJurisdiction(
            id=uuid4(), name=payload.name, code=payload.code, type=payload.type,
            parent_id=payload.parent_id, created_at=datetime.utcnow()
        )
        jurisdiction_store[obj.id] = obj
        return obj

    async def get_jurisdiction(_db, jid: UUID):
        return jurisdiction_store.get(jid)

    async def get_jurisdiction_by_name(_db, name: str, type: Optional[str] = None):
        for o in jurisdiction_store.values():
            if o.name.lower() == name.lower() and (type is None or o.type == type):
                return o
        return None

    async def list_jurisdictions(
        _db, skip: int = 0, limit: int = 100, type: Optional[str] = None, parent_id: Optional[UUID] = None
    ):
        items = list(jurisdiction_store.values())
        if type is not None:
            items = [o for o in items if o.type == type]
        if parent_id is not None:
            items = [o for o in items if o.parent_id == parent_id]
        return items[skip : skip + limit]

    async def update_jurisdiction(_db, obj: DummyJurisdiction, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_jurisdiction(_db, jid: UUID) -> bool:
        return jurisdiction_store.pop(jid, None) is not None

    async def list_jurisdiction_reporting_stages_by_jurisdiction(
        _db, jid: UUID, skip: int = 0, limit: int = 100
    ):
        items = [s for s in jrs_store.values() if s.jurisdiction_id == jid]
        return items[skip : skip + limit]

    monkeypatch.setattr(j_router, "create_jurisdiction", create_jurisdiction)
    monkeypatch.setattr(j_router, "get_jurisdiction", get_jurisdiction)
    monkeypatch.setattr(j_router, "get_jurisdiction_by_name", get_jurisdiction_by_name)
    monkeypatch.setattr(j_router, "list_jurisdictions", list_jurisdictions)
    monkeypatch.setattr(j_router, "update_jurisdiction", update_jurisdiction)
    monkeypatch.setattr(j_router, "delete_jurisdiction", delete_jurisdiction)
    monkeypatch.setattr(
        j_router,
        "list_jurisdiction_reporting_stages_by_jurisdiction",
        list_jurisdiction_reporting_stages_by_jurisdiction,
    )


@pytest.fixture(autouse=True)
def patch_anz_reporting_stages_crud(
    monkeypatch: pytest.MonkeyPatch,
    anz_stage_store: Dict[UUID, DummyAnzReportingStage],
):
    import routers.anz_reporting_stages as anz_router

    async def create_anz_reporting_stage(_db, payload):
        obj = DummyAnzReportingStage(
            id=uuid4(),
            name=payload.name,
            sequence=payload.sequence if hasattr(payload, "sequence") else 0,
            created_at=datetime.utcnow(),
        )
        anz_stage_store[obj.id] = obj
        return obj

    async def get_anz_reporting_stage(_db, sid: UUID):
        return anz_stage_store.get(sid)

    async def get_anz_reporting_stage_by_name(_db, name: str):
        for o in anz_stage_store.values():
            if o.name.lower() == name.lower():
                return o
        return None

    async def list_anz_reporting_stages(_db, skip: int = 0, limit: int = 100):
        items = list(anz_stage_store.values())
        return items[skip : skip + limit]

    async def update_anz_reporting_stage(_db, obj: DummyAnzReportingStage, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_anz_reporting_stage(_db, sid: UUID) -> bool:
        return anz_stage_store.pop(sid, None) is not None

    monkeypatch.setattr(anz_router, "create_anz_reporting_stage", create_anz_reporting_stage)
    monkeypatch.setattr(anz_router, "get_anz_reporting_stage", get_anz_reporting_stage)
    monkeypatch.setattr(anz_router, "get_anz_reporting_stage_by_name", get_anz_reporting_stage_by_name)
    monkeypatch.setattr(anz_router, "list_anz_reporting_stages", list_anz_reporting_stages)
    monkeypatch.setattr(anz_router, "update_anz_reporting_stage", update_anz_reporting_stage)
    monkeypatch.setattr(anz_router, "delete_anz_reporting_stage", delete_anz_reporting_stage)


@pytest.fixture(autouse=True)
def patch_jurisdiction_reporting_stages_crud(
    monkeypatch: pytest.MonkeyPatch,
    jurisdiction_store: Dict[UUID, DummyJurisdiction],
    jrs_store: Dict[UUID, DummyJurisdictionReportingStage],
):
    import routers.jurisdiction_reporting_stages as jrs_router

    async def get_jurisdiction(_db, jid: UUID):
        return jurisdiction_store.get(jid)

    async def create_jurisdiction_reporting_stage(_db, payload):
        obj = DummyJurisdictionReportingStage(
            id=uuid4(),
            jurisdiction_id=payload.jurisdiction_id,
            anz_reporting_stage_id=payload.anz_reporting_stage_id,
            name=payload.name,
            sequence=getattr(payload, "sequence", 0) or 0,
            created_at=datetime.utcnow(),
        )
        jrs_store[obj.id] = obj
        return obj

    async def get_jurisdiction_reporting_stage(_db, sid: UUID):
        return jrs_store.get(sid)

    async def list_jurisdiction_reporting_stages(_db, skip: int = 0, limit: int = 100):
        items = list(jrs_store.values())
        return items[skip : skip + limit]

    async def update_jurisdiction_reporting_stage(_db, obj: DummyJurisdictionReportingStage, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_jurisdiction_reporting_stage(_db, sid: UUID) -> bool:
        return jrs_store.pop(sid, None) is not None

    monkeypatch.setattr(jrs_router, "get_jurisdiction", get_jurisdiction)
    monkeypatch.setattr(jrs_router, "create_jurisdiction_reporting_stage", create_jurisdiction_reporting_stage)
    monkeypatch.setattr(jrs_router, "get_jurisdiction_reporting_stage", get_jurisdiction_reporting_stage)
    monkeypatch.setattr(jrs_router, "list_jurisdiction_reporting_stages", list_jurisdiction_reporting_stages)
    monkeypatch.setattr(jrs_router, "update_jurisdiction_reporting_stage", update_jurisdiction_reporting_stage)
    monkeypatch.setattr(jrs_router, "delete_jurisdiction_reporting_stage", delete_jurisdiction_reporting_stage)


@pytest.fixture(autouse=True)
def patch_ghg_scopes_crud(
    monkeypatch: pytest.MonkeyPatch,
    ghg_scope_store: Dict[int, DummyGhgScope],
):
    import routers.ghg_scopes as ghg_router

    async def list_ghg_scopes(_db):
        return list(ghg_scope_store.values())

    async def get_ghg_scope(_db, scope_id: int):
        return ghg_scope_store.get(scope_id)

    monkeypatch.setattr(ghg_router, "list_ghg_scopes", list_ghg_scopes)
    monkeypatch.setattr(ghg_router, "get_ghg_scope", get_ghg_scope)


@pytest.fixture(autouse=True)
def patch_units_crud(
    monkeypatch: pytest.MonkeyPatch,
    unit_store: Dict[UUID, DummyUnit],
):
    import routers.units as units_router

    async def create_unit(_db, payload):
        obj = DummyUnit(id=uuid4(), code=payload.code)
        unit_store[obj.id] = obj
        return obj

    async def get_unit(_db, uid: UUID):
        return unit_store.get(uid)

    async def get_unit_by_code(_db, code: str):
        for o in unit_store.values():
            if o.code == code:
                return o
        return None

    async def list_units(_db, skip: int = 0, limit: int = 100):
        items = list(unit_store.values())
        return items[skip : skip + limit]

    async def update_unit(_db, obj: DummyUnit, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_unit(_db, uid: UUID) -> bool:
        return unit_store.pop(uid, None) is not None

    monkeypatch.setattr(units_router, "create_unit", create_unit)
    monkeypatch.setattr(units_router, "get_unit", get_unit)
    monkeypatch.setattr(units_router, "get_unit_by_code", get_unit_by_code)
    monkeypatch.setattr(units_router, "list_units", list_units)
    monkeypatch.setattr(units_router, "update_unit", update_unit)
    monkeypatch.setattr(units_router, "delete_unit", delete_unit)


@pytest.fixture(autouse=True)
def patch_unit_conversions_crud(
    monkeypatch: pytest.MonkeyPatch,
    unit_conversion_store: Dict[UUID, DummyUnitConversion],
):
    import routers.unit_conversions as uc_router

    async def create_unit_conversion(_db, payload):
        obj = DummyUnitConversion(
            id=uuid4(),
            from_unit_id=payload.from_unit_id,
            to_unit_id=payload.to_unit_id,
            factor=Decimal(str(payload.factor)),
            from_unit=DummyUnit(id=payload.from_unit_id, code=str(payload.from_unit_id)),
            to_unit=DummyUnit(id=payload.to_unit_id, code=str(payload.to_unit_id)),
        )
        unit_conversion_store[obj.id] = obj
        return obj

    async def get_unit_conversion(_db, cid: UUID):
        return unit_conversion_store.get(cid)

    async def get_unit_conversion_by_pair(_db, from_unit_id: UUID, to_unit_id: UUID, dataset_revision_id: Optional[UUID] = None):
        for o in unit_conversion_store.values():
            if o.from_unit_id == from_unit_id and o.to_unit_id == to_unit_id:
                return o
        return None

    async def list_unit_conversions(
        _db, from_unit_id: Optional[UUID] = None, dataset_revision_id: Optional[UUID] = None,
        skip: int = 0, limit: int = 100, global_only: bool = False
    ):
        items = list(unit_conversion_store.values())
        if from_unit_id is not None:
            items = [o for o in items if o.from_unit_id == from_unit_id]
        return items[skip : skip + limit]

    async def update_unit_conversion(_db, obj: DummyUnitConversion, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_unit_conversion(_db, cid: UUID) -> bool:
        return unit_conversion_store.pop(cid, None) is not None

    monkeypatch.setattr(uc_router, "create_unit_conversion", create_unit_conversion)
    monkeypatch.setattr(uc_router, "get_unit_conversion", get_unit_conversion)
    monkeypatch.setattr(uc_router, "get_unit_conversion_by_pair", get_unit_conversion_by_pair)
    monkeypatch.setattr(uc_router, "list_unit_conversions", list_unit_conversions)
    monkeypatch.setattr(uc_router, "update_unit_conversion", update_unit_conversion)
    monkeypatch.setattr(uc_router, "delete_unit_conversion", delete_unit_conversion)


@pytest.fixture(autouse=True)
def patch_emissions_categories_crud(
    monkeypatch: pytest.MonkeyPatch,
    emissions_category_store: Dict[UUID, DummyEmissionsCategory],
):
    import routers.emissions_categories as ec_router

    async def create_emissions_category(_db, payload):
        obj = DummyEmissionsCategory(
            id=uuid4(),
            name=payload.name,
            code=getattr(payload, "code", None),
            scope=getattr(payload, "scope", None),
            parent_category_id=getattr(payload, "parent_category_id", None),
            description=getattr(payload, "description", None),
            is_active=getattr(payload, "is_active", True),
            sort_order=getattr(payload, "sort_order", None),
            created_at=datetime.utcnow(),
        )
        emissions_category_store[obj.id] = obj
        return obj

    async def get_emissions_category(_db, cid: UUID):
        return emissions_category_store.get(cid)

    async def list_emissions_categories(
        _db,
        is_active: Optional[bool] = None,
        scope: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        items = list(emissions_category_store.values())
        if is_active is not None:
            items = [o for o in items if o.is_active is is_active]
        if scope is not None:
            items = [o for o in items if o.scope == scope]
        return items[skip : skip + limit]

    async def list_emissions_categories_by_parent(
        _db, parent_category_id: Optional[UUID], skip: int = 0, limit: int = 100
    ):
        items = [o for o in emissions_category_store.values() if o.parent_category_id == parent_category_id]
        return items[skip : skip + limit]

    async def update_emissions_category(_db, obj: DummyEmissionsCategory, payload):
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def delete_emissions_category(_db, cid: UUID) -> bool:
        return emissions_category_store.pop(cid, None) is not None

    monkeypatch.setattr(ec_router, "create_emissions_category", create_emissions_category)
    monkeypatch.setattr(ec_router, "get_emissions_category", get_emissions_category)
    monkeypatch.setattr(ec_router, "list_emissions_categories", list_emissions_categories)
    monkeypatch.setattr(ec_router, "list_emissions_categories_by_parent", list_emissions_categories_by_parent)
    monkeypatch.setattr(ec_router, "update_emissions_category", update_emissions_category)
    monkeypatch.setattr(ec_router, "delete_emissions_category", delete_emissions_category)


# ---------------------------------------------------------------------------
# Roles, Permissions, User Roles, Role Permissions — dummy types and stores
# ---------------------------------------------------------------------------


@dataclass
class DummyRole:
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


@dataclass
class DummyPermission:
    id: UUID
    name: str
    description: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


@dataclass
class DummyUserRole:
    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: Optional[str] = None
    scope_id: Optional[UUID] = None
    is_active: bool = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


@dataclass
class DummyRolePermission:
    id: UUID
    role_id: UUID
    permission_id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


# -- stores ------------------------------------------------------------------


@pytest.fixture
def role_store() -> Dict[UUID, DummyRole]:
    return {}


@pytest.fixture
def permission_store() -> Dict[UUID, DummyPermission]:
    return {}


@pytest.fixture
def user_role_store() -> Dict[UUID, DummyUserRole]:
    return {}


@pytest.fixture
def role_permission_store() -> Dict[UUID, DummyRolePermission]:
    return {}


# -- patches -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_roles_crud(
    monkeypatch: pytest.MonkeyPatch,
    role_store: Dict[UUID, DummyRole],
):
    import routers.roles as roles_router

    async def create_role(_db, payload):
        obj = DummyRole(
            id=uuid4(),
            name=payload.name,
            description=payload.description if hasattr(payload, "description") else None,
            is_active=payload.is_active if hasattr(payload, "is_active") else True,
            created_on=datetime.utcnow(),
            updated_on=None,
        )
        role_store[obj.id] = obj
        return obj

    async def get_role(_db, role_id: UUID):
        return role_store.get(role_id)

    async def get_role_by_name(_db, name: str):
        for o in role_store.values():
            if o.name.lower() == name.lower():
                return o
        return None

    async def list_roles(_db, skip: int = 0, limit: int = 50, is_active=None):
        items = list(role_store.values())
        if is_active is not None:
            items = [r for r in items if r.is_active is is_active]
        return items[skip : skip + limit]

    async def update_role(_db, obj: DummyRole, payload):
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)
        obj.updated_on = datetime.utcnow()
        return obj

    async def delete_role(_db, role_id: UUID) -> bool:
        return role_store.pop(role_id, None) is not None

    monkeypatch.setattr(roles_router, "create_role", create_role)
    monkeypatch.setattr(roles_router, "get_role", get_role)
    monkeypatch.setattr(roles_router, "get_role_by_name", get_role_by_name)
    monkeypatch.setattr(roles_router, "list_roles", list_roles)
    monkeypatch.setattr(roles_router, "update_role", update_role)
    monkeypatch.setattr(roles_router, "delete_role", delete_role)


@pytest.fixture(autouse=True)
def patch_permissions_crud(
    monkeypatch: pytest.MonkeyPatch,
    permission_store: Dict[UUID, DummyPermission],
):
    import routers.permissions as permissions_router

    async def get_permission(_db, permission_id: UUID):
        return permission_store.get(permission_id)

    async def list_permissions(_db, skip: int = 0, limit: int = 50):
        items = list(permission_store.values())
        return items[skip : skip + limit]

    monkeypatch.setattr(permissions_router, "get_permission", get_permission)
    monkeypatch.setattr(permissions_router, "list_permissions", list_permissions)


@pytest.fixture(autouse=True)
def patch_user_roles_crud(
    monkeypatch: pytest.MonkeyPatch,
    user_role_store: Dict[UUID, DummyUserRole],
):
    import routers.user_roles as user_roles_router

    async def create_user_role(_db, user_id: UUID, role_id: UUID, scope_type=None, scope_id=None, is_active=True):
        obj = DummyUserRole(
            id=uuid4(),
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            is_active=is_active,
            created_on=datetime.utcnow(),
            updated_on=None,
        )
        user_role_store[obj.id] = obj
        return obj

    async def get_user_role(_db, user_role_id: UUID):
        return user_role_store.get(user_role_id)

    async def list_user_roles(
        _db,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[UUID] = None,
        role_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None,
    ):
        items = list(user_role_store.values())
        if user_id is not None:
            items = [ur for ur in items if ur.user_id == user_id]
        if role_id is not None:
            items = [ur for ur in items if ur.role_id == role_id]
        if is_active is not None:
            items = [ur for ur in items if ur.is_active is is_active]
        if scope_type is not None:
            items = [ur for ur in items if getattr(ur, "scope_type", None) == scope_type]
        if scope_id is not None:
            items = [ur for ur in items if getattr(ur, "scope_id", None) == scope_id]
        return items[skip : skip + limit]

    async def update_user_role(_db, user_role_id: UUID, *, is_active=None):
        obj = user_role_store.get(user_role_id)
        if obj is None:
            return None
        if is_active is not None:
            obj.is_active = is_active
        obj.updated_on = datetime.utcnow()
        return obj

    async def delete_user_role(_db, user_role_id: UUID) -> bool:
        return user_role_store.pop(user_role_id, None) is not None

    monkeypatch.setattr(user_roles_router, "create_user_role", create_user_role)
    monkeypatch.setattr(user_roles_router, "get_user_role", get_user_role)
    monkeypatch.setattr(user_roles_router, "list_user_roles", list_user_roles)
    monkeypatch.setattr(user_roles_router, "update_user_role", update_user_role)
    monkeypatch.setattr(user_roles_router, "delete_user_role", delete_user_role)


@pytest.fixture(autouse=True)
def patch_role_permissions_crud(
    monkeypatch: pytest.MonkeyPatch,
    role_permission_store: Dict[UUID, DummyRolePermission],
):
    import routers.role_permissions as role_permissions_router

    async def create_role_permission(_db, role_id: UUID, permission_id: UUID):
        obj = DummyRolePermission(
            id=uuid4(),
            role_id=role_id,
            permission_id=permission_id,
            created_on=datetime.utcnow(),
            updated_on=None,
        )
        role_permission_store[obj.id] = obj
        return obj

    async def get_role_permission(_db, role_permission_id: UUID):
        return role_permission_store.get(role_permission_id)

    async def list_role_permissions(
        _db,
        skip: int = 0,
        limit: int = 50,
        role_id: Optional[UUID] = None,
        permission_id: Optional[UUID] = None,
    ):
        items = list(role_permission_store.values())
        if role_id is not None:
            items = [rp for rp in items if rp.role_id == role_id]
        if permission_id is not None:
            items = [rp for rp in items if rp.permission_id == permission_id]
        return items[skip : skip + limit]

    async def delete_role_permission(_db, role_permission_id: UUID) -> bool:
        return role_permission_store.pop(role_permission_id, None) is not None

    monkeypatch.setattr(role_permissions_router, "create_role_permission", create_role_permission)
    monkeypatch.setattr(role_permissions_router, "get_role_permission", get_role_permission)
    monkeypatch.setattr(role_permissions_router, "list_role_permissions", list_role_permissions)
    monkeypatch.setattr(role_permissions_router, "delete_role_permission", delete_role_permission)


# ---------------------------------------------------------------------------
# Defaults & Materials — dummy types and stores
# ---------------------------------------------------------------------------

from datetime import date as date_type


@dataclass
class DummyMaterial:
    id: UUID
    name: str
    emissions_category_id: Optional[UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class DummyMaterialRecycledContent:
    id: UUID
    material_id: Optional[UUID] = None
    recycled_from_material_id: Optional[UUID] = None
    percent: Optional[Decimal] = None
    jurisdiction_id: Optional[UUID] = None
    effective_from: Optional[date_type] = None
    effective_to: Optional[date_type] = None
    notes: Optional[str] = None
    dataset_revision_id: Optional[UUID] = None


@dataclass
class DummyDensity:
    id: UUID
    dataset: str
    record_key: str
    unit_id: UUID
    dataset_revision_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    unit: Optional[DummyUnit] = None
    group: Optional[str] = None
    sub_group: Optional[str] = None
    item: Optional[str] = None
    item_description: Optional[str] = None
    emissions_category_id: Optional[UUID] = None
    emissions_sub_category_id: Optional[UUID] = None
    emissions_source: Optional[str] = None
    density: Optional[Decimal] = None
    source: Optional[str] = None


@dataclass
class DummyWasteTreatment:
    id: UUID
    name: str
    is_active: bool = True


@dataclass
class DummyDefaultTransportDistance:
    id: UUID
    jurisdiction_id: UUID
    material_id: Optional[UUID] = None
    emissions_category_id: Optional[UUID] = None
    truck_distance: Optional[Decimal] = None
    rail_distance: Optional[Decimal] = None
    sea_distance: Optional[Decimal] = None
    distance_unit_id: Optional[UUID] = None
    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    sea_transport_mode: Optional[str] = None
    source: Optional[str] = None
    grade_applicability: Optional[str] = None
    effective_from: Optional[date_type] = None
    effective_to: Optional[date_type] = None
    dataset_revision_id: Optional[UUID] = None


@dataclass
class DummyDefaultWasteRate:
    id: UUID
    jurisdiction_id: UUID
    material_id: UUID
    waste_treatment_id: UUID
    basis: str
    rate: Decimal
    applicable_lifecycle_module_code: Optional[str] = None
    rate_unit_id: Optional[UUID] = None
    notes: Optional[str] = None
    effective_from: Optional[date_type] = None
    effective_to: Optional[date_type] = None
    dataset_revision_id: Optional[UUID] = None


@dataclass
class DummyBaseCaseAssumption:
    id: UUID
    name: str
    emissions_category_id: Optional[UUID] = None
    default_value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    is_anz_default: bool = True
    notes: Optional[str] = None
    dataset_revision_id: Optional[UUID] = None


@dataclass
class DummyProponentAssumptionOverride:
    id: UUID
    proponent_org_id: UUID
    assumption_id: UUID
    effective_from: date_type
    value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    effective_to: Optional[date_type] = None


# -- stores ------------------------------------------------------------------


@pytest.fixture
def material_store() -> Dict[UUID, DummyMaterial]:
    return {}


@pytest.fixture
def material_recycled_content_store() -> Dict[UUID, DummyMaterialRecycledContent]:
    return {}


@pytest.fixture
def density_store() -> Dict[UUID, DummyDensity]:
    return {}


@pytest.fixture
def waste_treatment_store() -> Dict[UUID, DummyWasteTreatment]:
    return {}


@pytest.fixture
def default_transport_distance_store() -> Dict[UUID, DummyDefaultTransportDistance]:
    return {}


@pytest.fixture
def default_waste_rate_store() -> Dict[UUID, DummyDefaultWasteRate]:
    return {}


@pytest.fixture
def base_case_assumption_store() -> Dict[UUID, DummyBaseCaseAssumption]:
    return {}


@pytest.fixture
def proponent_assumption_override_store() -> Dict[UUID, DummyProponentAssumptionOverride]:
    return {}


# -- patches -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_materials_crud(
    monkeypatch: pytest.MonkeyPatch,
    material_store: Dict[UUID, DummyMaterial],
):
    import routers.materials as mat_router

    async def create_material(_db, payload):
        obj = DummyMaterial(id=uuid4(), name=payload.name,
                            emissions_category_id=getattr(payload, "emissions_category_id", None),
                            is_active=getattr(payload, "is_active", True),
                            created_at=datetime.utcnow())
        material_store[obj.id] = obj
        return obj

    async def get_material(_db, mid: UUID):
        return material_store.get(mid)

    async def get_material_by_name(_db, name: str):
        for o in material_store.values():
            if o.name == name:
                return o
        return None

    async def list_materials(_db, skip: int = 0, limit: int = 100, is_active=None):
        items = list(material_store.values())
        if is_active is not None:
            items = [o for o in items if o.is_active is is_active]
        return items[skip: skip + limit]

    async def update_material(_db, obj: DummyMaterial, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_material(_db, mid: UUID) -> bool:
        return material_store.pop(mid, None) is not None

    monkeypatch.setattr(mat_router, "create_material", create_material)
    monkeypatch.setattr(mat_router, "get_material", get_material)
    monkeypatch.setattr(mat_router, "get_material_by_name", get_material_by_name)
    monkeypatch.setattr(mat_router, "list_materials", list_materials)
    monkeypatch.setattr(mat_router, "update_material", update_material)
    monkeypatch.setattr(mat_router, "delete_material", delete_material)


@pytest.fixture(autouse=True)
def patch_material_recycled_content_crud(
    monkeypatch: pytest.MonkeyPatch,
    material_recycled_content_store: Dict[UUID, DummyMaterialRecycledContent],
):
    import routers.material_recycled_content as mrc_router

    async def create_material_recycled_content(_db, payload):
        d = payload.model_dump()
        obj = DummyMaterialRecycledContent(id=uuid4(), **d)
        material_recycled_content_store[obj.id] = obj
        return obj

    async def get_material_recycled_content(_db, rid: UUID):
        return material_recycled_content_store.get(rid)

    async def get_material_recycled_content_by_jurisdiction_and_material(_db, jurisdiction_id, material_id):
        if jurisdiction_id is None or material_id is None:
            return None
        for o in material_recycled_content_store.values():
            if o.jurisdiction_id == jurisdiction_id and o.material_id == material_id:
                return o
        return None

    async def list_material_recycled_contents(_db, material_id=None, jurisdiction_id=None, skip=0, limit=100):
        items = list(material_recycled_content_store.values())
        if material_id:
            items = [o for o in items if o.material_id == material_id]
        if jurisdiction_id:
            items = [o for o in items if o.jurisdiction_id == jurisdiction_id]
        return items[skip: skip + limit]

    async def update_material_recycled_content(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_material_recycled_content(_db, rid: UUID) -> bool:
        return material_recycled_content_store.pop(rid, None) is not None

    monkeypatch.setattr(mrc_router, "create_material_recycled_content", create_material_recycled_content)
    monkeypatch.setattr(mrc_router, "get_material_recycled_content", get_material_recycled_content)
    monkeypatch.setattr(mrc_router, "get_material_recycled_content_by_jurisdiction_and_material", get_material_recycled_content_by_jurisdiction_and_material)
    monkeypatch.setattr(mrc_router, "list_material_recycled_contents", list_material_recycled_contents)
    monkeypatch.setattr(mrc_router, "update_material_recycled_content", update_material_recycled_content)
    monkeypatch.setattr(mrc_router, "delete_material_recycled_content", delete_material_recycled_content)


@pytest.fixture(autouse=True)
def patch_densities_crud(
    monkeypatch: pytest.MonkeyPatch,
    density_store: Dict[UUID, DummyDensity],
    unit_store: Dict[UUID, DummyUnit],
):
    import routers.densities as dens_router

    async def create_density(db, payload):
        d = payload.model_dump()
        density_val = d.get("density")

        unit = unit_store.get(d["unit_id"])

        obj = DummyDensity(
            id=uuid4(),
            dataset=d["dataset"],
            record_key=d["record_key"],
            unit_id=d["unit_id"],
            dataset_revision_id=d.get("dataset_revision_id"),
            jurisdiction_id=d.get("jurisdiction_id"),
            unit=unit,
            group=d.get("group"),
            sub_group=d.get("sub_group"),
            item=d.get("item"),
            item_description=d.get("item_description"),
            emissions_category_id=d.get("emissions_category_id"),
            emissions_sub_category_id=d.get("emissions_sub_category_id"),
            emissions_source=d.get("emissions_source"),
            density=Decimal(str(density_val)) if density_val is not None else None,
            source=d.get("source"),
        )

        density_store[obj.id] = obj
        return obj

    async def get_density(db, density_id: UUID):
        return density_store.get(density_id)

    async def get_density_by_key(
        db,
        jurisdiction_id,
        dataset: str,
        record_key: str,
        unit_id: UUID,
        dataset_revision_id: UUID,
    ):
        for o in density_store.values():
            if (
                o.jurisdiction_id == jurisdiction_id
                and o.dataset_revision_id == dataset_revision_id
                and o.dataset == dataset
                and o.record_key == record_key
                and o.unit_id == unit_id
            ):
                return o

        return None

    async def list_densities(
        db,
        dataset=None,
        jurisdiction_id=None,
        unit_id=None,
        search=None,
        dataset_revision_id=None,
        skip=0,
        limit=100,
    ):
        items = list(density_store.values())

        if dataset:
            items = [o for o in items if o.dataset == dataset]

        if jurisdiction_id:
            items = [o for o in items if o.jurisdiction_id == jurisdiction_id]

        if unit_id:
            items = [o for o in items if o.unit_id == unit_id]

        if search:
            items = [
                o for o in items
                if search.lower() in o.record_key.lower()
            ]

        return items[skip: skip + limit]

    async def update_density(db, obj: DummyDensity, payload):
        data = payload.model_dump(exclude_unset=True)

        for k, v in data.items():
            setattr(obj, k, v)

        if "unit_id" in data:
            obj.unit = unit_store.get(data["unit_id"])

        return obj

    async def delete_density(db, density_id: UUID) -> bool:
        return density_store.pop(density_id, None) is not None

    async def assert_revision_edit_permission(
        db,
        principal,
        dataset_revision_id,
        dataset_type=None,
    ):
        return True
    
    monkeypatch.setattr(dens_router, "create_density", create_density)
    monkeypatch.setattr(dens_router, "get_density", get_density)
    monkeypatch.setattr(dens_router, "get_density_by_key", get_density_by_key)
    monkeypatch.setattr(dens_router, "list_densities", list_densities)
    monkeypatch.setattr(dens_router, "update_density", update_density)
    monkeypatch.setattr(dens_router, "delete_density", delete_density)
    monkeypatch.setattr(
        dens_router,
        "assert_revision_edit_permission",
        assert_revision_edit_permission,
    )

@pytest.fixture(autouse=True)
def patch_waste_treatments_crud(
    monkeypatch: pytest.MonkeyPatch,
    waste_treatment_store: Dict[UUID, DummyWasteTreatment],
):
    import routers.waste_treatments as wt_router

    async def create_waste_treatment(_db, payload):
        obj = DummyWasteTreatment(id=uuid4(), name=payload.name, is_active=getattr(payload, "is_active", True))
        waste_treatment_store[obj.id] = obj
        return obj

    async def get_waste_treatment(_db, wid: UUID):
        return waste_treatment_store.get(wid)

    async def get_waste_treatment_by_name(_db, name: str):
        for o in waste_treatment_store.values():
            if o.name == name:
                return o
        return None

    async def list_waste_treatments(_db, skip=0, limit=100, is_active=None):
        items = list(waste_treatment_store.values())
        if is_active is not None:
            items = [o for o in items if o.is_active is is_active]
        return items[skip: skip + limit]

    async def update_waste_treatment(_db, obj: DummyWasteTreatment, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_waste_treatment(_db, wid: UUID) -> bool:
        return waste_treatment_store.pop(wid, None) is not None

    monkeypatch.setattr(wt_router, "create_waste_treatment", create_waste_treatment)
    monkeypatch.setattr(wt_router, "get_waste_treatment", get_waste_treatment)
    monkeypatch.setattr(wt_router, "get_waste_treatment_by_name", get_waste_treatment_by_name)
    monkeypatch.setattr(wt_router, "list_waste_treatments", list_waste_treatments)
    monkeypatch.setattr(wt_router, "update_waste_treatment", update_waste_treatment)
    monkeypatch.setattr(wt_router, "delete_waste_treatment", delete_waste_treatment)


@pytest.fixture(autouse=True)
def patch_default_transport_distances_crud(
    monkeypatch: pytest.MonkeyPatch,
    default_transport_distance_store: Dict[UUID, DummyDefaultTransportDistance],
):
    import routers.default_transport_distances as dtd_router

    async def create_default_transport_distance(_db, payload):
        d = payload.model_dump()
        obj = DummyDefaultTransportDistance(id=uuid4(), **d)
        default_transport_distance_store[obj.id] = obj
        return obj

    async def get_default_transport_distance(_db, rid: UUID):
        return default_transport_distance_store.get(rid)

    async def get_default_transport_distance_by_key(_db, jurisdiction_id, material_id, emissions_category_id):
        for o in default_transport_distance_store.values():
            if (o.jurisdiction_id == jurisdiction_id
                    and o.material_id == material_id
                    and o.emissions_category_id == emissions_category_id):
                return o
        return None

    async def list_default_transport_distances(_db, jurisdiction_id=None, material_id=None, emissions_category_id=None, skip=0, limit=100):
        items = list(default_transport_distance_store.values())
        if jurisdiction_id:
            items = [o for o in items if o.jurisdiction_id == jurisdiction_id]
        if material_id:
            items = [o for o in items if o.material_id == material_id]
        if emissions_category_id:
            items = [o for o in items if o.emissions_category_id == emissions_category_id]
        return items[skip: skip + limit]

    async def update_default_transport_distance(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_default_transport_distance(_db, rid: UUID) -> bool:
        return default_transport_distance_store.pop(rid, None) is not None

    monkeypatch.setattr(dtd_router, "create_default_transport_distance", create_default_transport_distance)
    monkeypatch.setattr(dtd_router, "get_default_transport_distance", get_default_transport_distance)
    monkeypatch.setattr(dtd_router, "get_default_transport_distance_by_key", get_default_transport_distance_by_key)
    monkeypatch.setattr(dtd_router, "list_default_transport_distances", list_default_transport_distances)
    monkeypatch.setattr(dtd_router, "update_default_transport_distance", update_default_transport_distance)
    monkeypatch.setattr(dtd_router, "delete_default_transport_distance", delete_default_transport_distance)


@pytest.fixture(autouse=True)
def patch_default_waste_rates_crud(
    monkeypatch: pytest.MonkeyPatch,
    default_waste_rate_store: Dict[UUID, DummyDefaultWasteRate],
):
    import routers.default_waste_rates as dwr_router

    async def create_default_waste_rate(_db, payload):
        d = payload.model_dump()
        obj = DummyDefaultWasteRate(id=uuid4(), **d)
        default_waste_rate_store[obj.id] = obj
        return obj

    async def get_default_waste_rate(_db, rid: UUID):
        return default_waste_rate_store.get(rid)

    async def list_default_waste_rates(_db, jurisdiction_id=None, material_id=None, waste_treatment_id=None, skip=0, limit=100):
        items = list(default_waste_rate_store.values())
        if jurisdiction_id:
            items = [o for o in items if o.jurisdiction_id == jurisdiction_id]
        if material_id:
            items = [o for o in items if o.material_id == material_id]
        if waste_treatment_id:
            items = [o for o in items if o.waste_treatment_id == waste_treatment_id]
        return items[skip: skip + limit]

    async def update_default_waste_rate(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_default_waste_rate(_db, rid: UUID) -> bool:
        return default_waste_rate_store.pop(rid, None) is not None

    monkeypatch.setattr(dwr_router, "create_default_waste_rate", create_default_waste_rate)
    monkeypatch.setattr(dwr_router, "get_default_waste_rate", get_default_waste_rate)
    monkeypatch.setattr(dwr_router, "list_default_waste_rates", list_default_waste_rates)
    monkeypatch.setattr(dwr_router, "update_default_waste_rate", update_default_waste_rate)
    monkeypatch.setattr(dwr_router, "delete_default_waste_rate", delete_default_waste_rate)


@pytest.fixture(autouse=True)
def patch_base_case_assumptions_crud(
    monkeypatch: pytest.MonkeyPatch,
    base_case_assumption_store: Dict[UUID, DummyBaseCaseAssumption],
):
    import routers.base_case_assumptions as bca_router

    async def create_base_case_assumption(_db, payload):
        d = payload.model_dump()
        obj = DummyBaseCaseAssumption(id=uuid4(), **d)
        base_case_assumption_store[obj.id] = obj
        return obj

    async def get_base_case_assumption(_db, aid: UUID):
        return base_case_assumption_store.get(aid)

    async def get_base_case_assumption_by_category_name(_db, emissions_category_id, name):
        for o in base_case_assumption_store.values():
            if o.emissions_category_id == emissions_category_id and o.name == name:
                return o
        return None

    async def list_base_case_assumptions(_db, emissions_category_id=None, is_anz_default=None, dataset_revision_id=None, skip=0, limit=100):
        items = list(base_case_assumption_store.values())
        if emissions_category_id:
            items = [o for o in items if o.emissions_category_id == emissions_category_id]
        if is_anz_default is not None:
            items = [o for o in items if o.is_anz_default is is_anz_default]
        return items[skip: skip + limit]

    async def update_base_case_assumption(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_base_case_assumption(_db, aid: UUID) -> bool:
        return base_case_assumption_store.pop(aid, None) is not None

    monkeypatch.setattr(bca_router, "create_base_case_assumption", create_base_case_assumption)
    monkeypatch.setattr(bca_router, "get_base_case_assumption", get_base_case_assumption)
    monkeypatch.setattr(bca_router, "get_base_case_assumption_by_category_name", get_base_case_assumption_by_category_name)
    monkeypatch.setattr(bca_router, "list_base_case_assumptions", list_base_case_assumptions)
    monkeypatch.setattr(bca_router, "update_base_case_assumption", update_base_case_assumption)
    monkeypatch.setattr(bca_router, "delete_base_case_assumption", delete_base_case_assumption)


@pytest.fixture(autouse=True)
def patch_proponent_assumption_overrides_crud(
    monkeypatch: pytest.MonkeyPatch,
    proponent_assumption_override_store: Dict[UUID, DummyProponentAssumptionOverride],
):
    import routers.proponent_assumption_overrides as pao_router

    async def create_proponent_assumption_override(_db, payload):
        d = payload.model_dump()
        obj = DummyProponentAssumptionOverride(id=uuid4(), **d)
        proponent_assumption_override_store[obj.id] = obj
        return obj

    async def get_proponent_assumption_override(_db, oid: UUID):
        return proponent_assumption_override_store.get(oid)

    async def get_proponent_assumption_override_by_key(_db, proponent_org_id, assumption_id, effective_from):
        for o in proponent_assumption_override_store.values():
            if (o.proponent_org_id == proponent_org_id
                    and o.assumption_id == assumption_id
                    and o.effective_from == effective_from):
                return o
        return None

    async def list_proponent_assumption_overrides(_db, proponent_org_id=None, assumption_id=None, skip=0, limit=100):
        items = list(proponent_assumption_override_store.values())
        if proponent_org_id:
            items = [o for o in items if o.proponent_org_id == proponent_org_id]
        if assumption_id:
            items = [o for o in items if o.assumption_id == assumption_id]
        return items[skip: skip + limit]

    async def update_proponent_assumption_override(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_proponent_assumption_override(_db, oid: UUID) -> bool:
        return proponent_assumption_override_store.pop(oid, None) is not None

    monkeypatch.setattr(pao_router, "create_proponent_assumption_override", create_proponent_assumption_override)
    monkeypatch.setattr(pao_router, "get_proponent_assumption_override", get_proponent_assumption_override)
    monkeypatch.setattr(pao_router, "get_proponent_assumption_override_by_key", get_proponent_assumption_override_by_key)
    monkeypatch.setattr(pao_router, "list_proponent_assumption_overrides", list_proponent_assumption_overrides)
    monkeypatch.setattr(pao_router, "update_proponent_assumption_override", update_proponent_assumption_override)
    monkeypatch.setattr(pao_router, "delete_proponent_assumption_override", delete_proponent_assumption_override)


# ---------------------------------------------------------------------------
# Package F — Dataset Revisions & Factor Sets / Package G — Grade Metrics
# ---------------------------------------------------------------------------


@dataclass
class DummyGradeDefinition:
    id: int
    name: str


@dataclass
class DummyValueBand:
    code: str
    sort_order: Optional[int] = None


@dataclass
class DummyMetricType:
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class DummyDatasetRevision:
    id: UUID
    name: str
    status: str = "draft"
    scope_type: str = "DEFAULT"
    scope_id: Optional[UUID] = None
    applicable_from: Optional[object] = None
    applicable_to: Optional[object] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    parent_revision_id: Optional[UUID] = None


@dataclass
class DummyBackgroundGradeMetric:
    id: UUID
    dataset_revision_id: Optional[UUID] = None
    grade_id: int = 1
    metric_type_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    super_sector: Optional[str] = None
    mastertype_id: Optional[UUID] = None
    mastertype: Optional[str] = None
    typecast_id: Optional[UUID] = None
    typecast_name: Optional[str] = None
    emissions_category: Optional[str] = None
    emissions_subcategory: Optional[str] = None
    emissions_source: Optional[str] = None
    lifecycle_module_code: Optional[str] = None
    ghg_scope_id: Optional[int] = None
    band_code: Optional[str] = None
    unit_id: Optional[UUID] = None
    value: Optional[Decimal] = None
    assumed_quantity_default: Optional[Decimal] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    emissions_category_id: Optional[UUID] = None
    emissions_subcategory_id: Optional[UUID] = None


@dataclass
class DummyEmissionsFactorSet:
    id: UUID
    name: str
    version: str
    dataset_revision_id: Optional[UUID] = None
    notes: Optional[str] = None
    is_locked: bool = False
    created_at: Optional[datetime] = None


@dataclass
class DummyDatasetRevisionChange:
    id: UUID
    dataset_revision_id: UUID
    metric_natural_key: dict = field(default_factory=dict)
    change_type: Optional[str] = None
    changed_by: Optional[UUID] = None
    changed_at: Optional[datetime] = None
    old_value: Optional[object] = None
    new_value: Optional[object] = None
    reason: Optional[str] = None


@dataclass
class DummyProjectDatasetRevision:
    id: UUID
    project_id: UUID
    dataset_revision_id: UUID
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    is_locked: bool = False
    calculation_report: Dict = field(default_factory=dict)


@dataclass
class DummyProjectDatasetExclusion:
    id: UUID
    project_id: UUID
    metric_id: UUID
    excluded_from_revision: bool = True
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


# -- stores ------------------------------------------------------------------


@pytest.fixture
def grade_definition_store() -> Dict[int, DummyGradeDefinition]:
    return {}


@pytest.fixture
def value_band_store() -> Dict[str, DummyValueBand]:
    return {}


@pytest.fixture
def metric_type_store() -> Dict[UUID, DummyMetricType]:
    return {}


@pytest.fixture
def dataset_revision_store() -> Dict[UUID, DummyDatasetRevision]:
    return {}


@pytest.fixture
def emissions_factor_set_store() -> Dict[UUID, DummyEmissionsFactorSet]:
    return {}


@pytest.fixture
def background_grade_metric_store() -> Dict[UUID, DummyBackgroundGradeMetric]:
    return {}


@pytest.fixture
def dataset_revision_change_store() -> Dict[UUID, DummyDatasetRevisionChange]:
    return {}


@pytest.fixture
def project_dataset_revision_store() -> Dict[UUID, DummyProjectDatasetRevision]:
    return {}


@pytest.fixture
def project_dataset_exclusion_store() -> Dict[UUID, DummyProjectDatasetExclusion]:
    return {}


# -- patches -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_grade_definitions_crud(
    monkeypatch: pytest.MonkeyPatch,
    grade_definition_store: Dict[int, DummyGradeDefinition],
):
    import routers.grade_definitions as gd_router

    async def create_grade_definition(_db, payload):
        obj = DummyGradeDefinition(id=payload.id, name=payload.name)
        if obj.id in grade_definition_store:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Grade definition already exists")
        grade_definition_store[obj.id] = obj
        return obj

    async def get_grade_definition(_db, gid: int):
        return grade_definition_store.get(gid)

    async def list_grade_definitions(_db):
        return list(grade_definition_store.values())

    async def update_grade_definition(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_grade_definition(_db, gid: int) -> bool:
        return grade_definition_store.pop(gid, None) is not None

    monkeypatch.setattr(gd_router, "create_grade_definition", create_grade_definition)
    monkeypatch.setattr(gd_router, "get_grade_definition", get_grade_definition)
    monkeypatch.setattr(gd_router, "list_grade_definitions", list_grade_definitions)
    monkeypatch.setattr(gd_router, "update_grade_definition", update_grade_definition)
    monkeypatch.setattr(gd_router, "delete_grade_definition", delete_grade_definition)


@pytest.fixture(autouse=True)
def patch_value_bands_crud(
    monkeypatch: pytest.MonkeyPatch,
    value_band_store: Dict[str, DummyValueBand],
):
    import routers.value_bands as vb_router

    async def create_value_band(_db, payload):
        d = payload.model_dump()
        obj = DummyValueBand(**d)
        if obj.code in value_band_store:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Value band code already exists")
        value_band_store[obj.code] = obj
        return obj

    async def get_value_band(_db, code: str):
        return value_band_store.get(code)

    async def list_value_bands(_db):
        return list(value_band_store.values())

    async def update_value_band(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_value_band(_db, code: str) -> bool:
        return value_band_store.pop(code, None) is not None

    monkeypatch.setattr(vb_router, "create_value_band", create_value_band)
    monkeypatch.setattr(vb_router, "get_value_band", get_value_band)
    monkeypatch.setattr(vb_router, "list_value_bands", list_value_bands)
    monkeypatch.setattr(vb_router, "update_value_band", update_value_band)
    monkeypatch.setattr(vb_router, "delete_value_band", delete_value_band)


@pytest.fixture(autouse=True)
def patch_metric_types_crud(
    monkeypatch: pytest.MonkeyPatch,
    metric_type_store: Dict[UUID, DummyMetricType],
):
    import routers.metric_types as mt_router

    async def create_metric_type(_db, payload):
        d = payload.model_dump()
        # unique code check
        for o in metric_type_store.values():
            if o.code == d["code"]:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Metric type code already exists")
        obj = DummyMetricType(id=uuid4(), created_at=datetime.utcnow(), **d)
        metric_type_store[obj.id] = obj
        return obj

    async def get_metric_type(_db, mid: UUID):
        return metric_type_store.get(mid)

    async def get_metric_type_by_code(_db, code: str):
        for o in metric_type_store.values():
            if o.code == code:
                return o
        return None

    async def list_metric_types(_db):
        return list(metric_type_store.values())

    async def update_metric_type(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_metric_type(_db, mid: UUID) -> bool:
        return metric_type_store.pop(mid, None) is not None

    monkeypatch.setattr(mt_router, "create_metric_type", create_metric_type)
    monkeypatch.setattr(mt_router, "get_metric_type", get_metric_type)
    monkeypatch.setattr(mt_router, "get_metric_type_by_code", get_metric_type_by_code)
    monkeypatch.setattr(mt_router, "list_metric_types", list_metric_types)
    monkeypatch.setattr(mt_router, "update_metric_type", update_metric_type)
    monkeypatch.setattr(mt_router, "delete_metric_type", delete_metric_type)


@pytest.fixture(autouse=True)
def patch_emissions_factor_sets(monkeypatch: pytest.MonkeyPatch, emissions_factor_set_store):
    from routers import emissions_factor_sets as efs_router

    async def create_emissions_factor_set(_db, payload):
        obj = DummyEmissionsFactorSet(id=uuid4(), created_at=datetime.utcnow(), **payload.model_dump())
        emissions_factor_set_store[obj.id] = obj
        return obj

    async def get_emissions_factor_set(_db, factor_set_id):
        return emissions_factor_set_store.get(factor_set_id)

    async def update_emissions_factor_set(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_emissions_factor_set(_db, factor_set_id):
        return emissions_factor_set_store.pop(factor_set_id, None) is not None

    async def count_factor_sets_for_revision(_db, revision_id):
        return sum(1 for x in emissions_factor_set_store.values() if x.dataset_revision_id == revision_id)

    monkeypatch.setattr(efs_router, "create_emissions_factor_set", create_emissions_factor_set)
    monkeypatch.setattr(efs_router, "get_emissions_factor_set", get_emissions_factor_set)
    monkeypatch.setattr(efs_router, "update_emissions_factor_set", update_emissions_factor_set)
    monkeypatch.setattr(efs_router, "delete_emissions_factor_set", delete_emissions_factor_set)
    monkeypatch.setattr(efs_router, "count_factor_sets_for_revision", count_factor_sets_for_revision)


@pytest.fixture(autouse=True)
def patch_dataset_revisions_crud(
    monkeypatch: pytest.MonkeyPatch,
    dataset_revision_store: Dict[UUID, DummyDatasetRevision],
    project_dataset_revision_store: Dict[UUID, "DummyProjectDatasetRevision"],
    emissions_factor_set_store,
):
    import routers.dataset_revisions as dr_router
    import core.dataset_authorization as dataset_auth
    original_auth_revision_lookup = dataset_auth.get_dataset_revision

    async def create_dataset_revision(_db, payload):
        d = payload.model_dump()
        for o in dataset_revision_store.values():
            if o.name == d["name"]:
                from fastapi import HTTPException, status as http_status
                raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Dataset revision name already exists")
        obj = DummyDatasetRevision(id=uuid4(), created_at=datetime.utcnow(), **d)
        dataset_revision_store[obj.id] = obj
        return obj

    async def get_dataset_revision(_db, rid: UUID):
        revision = dataset_revision_store.get(rid)
        if revision is not None:
            return revision
        return await original_auth_revision_lookup(_db, rid)

    # Revisioned dataset endpoints use the shared authorization helper, which
    # resolves revisions through the CRUD module rather than this router's
    # patched CRUD functions. Prefer the in-memory store, with CRUD fallback
    # for unit tests that provide their own fake database session.
    monkeypatch.setattr(dataset_auth, "get_dataset_revision", get_dataset_revision)

    async def get_dataset_revision_by_name(_db, name: str, scope_type=None, scope_id=None):
        for o in dataset_revision_store.values():
            if o.name == name:
                return o
        return None

    async def list_dataset_revisions(_db, status=None, scope_type=None, scope_id=None, skip: int = 0, limit: int = 100):
        items = list(dataset_revision_store.values())
        if status is not None:
            items = [o for o in items if o.status == status]
        if scope_type is not None:
            items = [o for o in items if o.scope_type == scope_type]
        if scope_id is not None:
            items = [o for o in items if o.scope_id == scope_id]
        return items[skip: skip + limit]

    async def update_dataset_revision(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_dataset_revision(_db, rid: UUID) -> bool:
        return dataset_revision_store.pop(rid, None) is not None

    async def count_bound_projects(_db, revision_id: UUID) -> int:
        return sum(
            1 for pdr in project_dataset_revision_store.values()
            if pdr.dataset_revision_id == revision_id
        )

    async def set_revision_status(_db, obj, new_status: str):
        obj.status = new_status
        return obj

    async def count_factor_sets(_db, revision_id: UUID) -> int:
        return sum(1 for x in emissions_factor_set_store.values() if x.dataset_revision_id == revision_id)

    async def branch_dataset_revision(_db, source_id: UUID, name: str, notes, scope_type, scope_id):
        source = dataset_revision_store.get(source_id)
        if not source:
            return None
        new_rev = DummyDatasetRevision(
            id=uuid4(),
            name=name,
            status="draft",
            scope_type=scope_type or "DEFAULT",
            scope_id=scope_id,
            notes=notes,
            created_at=datetime.utcnow(),
        )
        dataset_revision_store[new_rev.id] = new_rev
        return new_rev

    monkeypatch.setattr(dr_router, "create_dataset_revision", create_dataset_revision)
    monkeypatch.setattr(dr_router, "get_dataset_revision", get_dataset_revision)
    monkeypatch.setattr(dr_router, "get_dataset_revision_by_name", get_dataset_revision_by_name)
    monkeypatch.setattr(dr_router, "list_dataset_revisions", list_dataset_revisions)
    monkeypatch.setattr(dr_router, "update_dataset_revision", update_dataset_revision)
    monkeypatch.setattr(dr_router, "delete_dataset_revision", delete_dataset_revision)
    monkeypatch.setattr(dr_router, "count_bound_projects", count_bound_projects)
    monkeypatch.setattr(dr_router, "set_revision_status", set_revision_status)
    monkeypatch.setattr(dr_router, "branch_dataset_revision", branch_dataset_revision)
    monkeypatch.setattr(dr_router, "count_factor_sets", count_factor_sets)




@pytest.fixture(autouse=True)
def patch_background_grade_metrics_crud(
    monkeypatch: pytest.MonkeyPatch,
    background_grade_metric_store: Dict[UUID, DummyBackgroundGradeMetric],
):
    import routers.background_grade_metrics as bgm_router

    async def assert_revision_edit_permission(
            db,
            principal,
            dataset_revision_id,
            dataset_type=None,  
    ):
        # Implement the permission check logic here
        return True

    async def create_background_grade_metric(db, payload):
        d = payload.model_dump()

        obj = DummyBackgroundGradeMetric(
            id=uuid4(),
            created_at=datetime.utcnow(),
            **d,
        )

        background_grade_metric_store[obj.id] = obj
        return obj

    async def get_background_grade_metric(db, metric_id: UUID):
        return background_grade_metric_store.get(metric_id)

    async def get_background_grade_metric_orm(db, metric_id: UUID):
        return background_grade_metric_store.get(metric_id)

    async def list_background_grade_metrics(
        db,
        dataset_revision_id=None,
        dataset_revision_ids=None,
        grade_id=None,
        jurisdiction_id=None,
        jurisdiction_name=None,
        jurisdiction_names=None,
        mastertype_id=None,
        typecast_id=None,
        band_code=None,
        emissions_category_id=None,
        emissions_subcategory_id=None,
        super_sector=None,
        super_sectors=None,
        mastertype=None,
        typecast_name=None,
        emissions_categories=None,
        emissions_subcategories=None,
        emissions_source=None,
        lifecycle_module_code=None,
        unit_codes=None,
        metric_type_codes=None,
        skip=0,
        limit=500,
    ):
        items = list(background_grade_metric_store.values())

        if dataset_revision_id is not None:
            items = [
                o for o in items
                if o.dataset_revision_id == dataset_revision_id
            ]

        if dataset_revision_ids:
            ids = set(dataset_revision_ids)
            items = [
                o for o in items
                if o.dataset_revision_id in ids
            ]

        if grade_id is not None:
            items = [
                o for o in items
                if o.grade_id == grade_id
            ]

        if jurisdiction_id is not None:
            items = [
                o for o in items
                if getattr(o, "jurisdiction_id", None) == jurisdiction_id
            ]

        if jurisdiction_name is not None:
            items = [
                o for o in items
                if getattr(o, "jurisdiction_name", None) == jurisdiction_name
            ]

        if jurisdiction_names:
            names = set(jurisdiction_names)
            items = [
                o for o in items
                if getattr(o, "jurisdiction_name", None) in names
            ]

        if mastertype_id is not None:
            items = [
                o for o in items
                if getattr(o, "mastertype_id", None) == mastertype_id
            ]

        if typecast_id is not None:
            items = [
                o for o in items
                if getattr(o, "typecast_id", None) == typecast_id
            ]

        if band_code is not None:
            items = [
                o for o in items
                if getattr(o, "band_code", None) == band_code
            ]

        if emissions_category_id is not None:
            items = [
                o for o in items
                if getattr(o, "emissions_category_id", None)
                == emissions_category_id
            ]

        if emissions_subcategory_id is not None:
            items = [
                o for o in items
                if getattr(o, "emissions_subcategory_id", None)
                == emissions_subcategory_id
            ]

        if super_sector is not None:
            items = [
                o for o in items
                if getattr(o, "super_sector", None) == super_sector
            ]

        if super_sectors:
            sectors = set(super_sectors)
            items = [
                o for o in items
                if getattr(o, "super_sector", None) in sectors
            ]

        if mastertype is not None:
            items = [
                o for o in items
                if getattr(o, "mastertype", None) == mastertype
            ]

        if typecast_name is not None:
            items = [
                o for o in items
                if getattr(o, "typecast_name", None) == typecast_name
            ]

        if emissions_source is not None:
            items = [
                o for o in items
                if getattr(o, "emissions_source", None)
                == emissions_source
            ]

        if lifecycle_module_code is not None:
            items = [
                o for o in items
                if getattr(o, "lifecycle_module_code", None)
                == lifecycle_module_code
            ]

        if emissions_categories:
            categories = set(emissions_categories)
            items = [
                o for o in items
                if getattr(o, "emissions_category", None) in categories
            ]

        if emissions_subcategories:
            subcategories = set(emissions_subcategories)
            items = [
                o for o in items
                if getattr(o, "emissions_subcategory", None)
                in subcategories
            ]

        return items[skip: skip + limit]

    async def supersede_background_grade_metric(
        db,
        obj,
        update_data: dict,
    ):
        for k, v in update_data.items():
            setattr(obj, k, v)
        return obj

    async def delete_background_grade_metric(
        db,
        metric_id: UUID,
    ) -> bool:
        return background_grade_metric_store.pop(
            metric_id,
            None,
        ) is not None

    monkeypatch.setattr(
        bgm_router,
        "create_background_grade_metric",
        create_background_grade_metric,
    )
    monkeypatch.setattr(
        bgm_router,
        "get_background_grade_metric",
        get_background_grade_metric,
    )
    monkeypatch.setattr(
        bgm_router,
        "get_background_grade_metric_orm",
        get_background_grade_metric_orm,
    )
    monkeypatch.setattr(
        bgm_router,
        "list_background_grade_metrics",
        list_background_grade_metrics,
    )
    monkeypatch.setattr(
        bgm_router,
        "supersede_background_grade_metric",
        supersede_background_grade_metric,
    )
    monkeypatch.setattr(
        bgm_router,
        "delete_background_grade_metric",
        delete_background_grade_metric,
    )
    monkeypatch.setattr(
        bgm_router,
        "assert_revision_edit_permission",
        assert_revision_edit_permission,
    )

@pytest.fixture(autouse=True)
def patch_dataset_revision_changes_crud(
    monkeypatch: pytest.MonkeyPatch,
    dataset_revision_change_store: Dict[UUID, DummyDatasetRevisionChange],
):
    import routers.dataset_revision_changes as drc_router

    async def create_dataset_revision_change(_db, payload):
        d = payload.model_dump()
        obj = DummyDatasetRevisionChange(id=uuid4(), changed_at=datetime.utcnow(), **d)
        dataset_revision_change_store[obj.id] = obj
        return obj

    async def get_dataset_revision_change(_db, cid: UUID):
        return dataset_revision_change_store.get(cid)

    async def list_changes_by_revision(_db, revision_id: UUID, skip: int = 0, limit: int = 500):
        items = [o for o in dataset_revision_change_store.values() if o.dataset_revision_id == revision_id]
        return items[skip: skip + limit]

    monkeypatch.setattr(drc_router, "create_dataset_revision_change", create_dataset_revision_change)
    monkeypatch.setattr(drc_router, "get_dataset_revision_change", get_dataset_revision_change)
    monkeypatch.setattr(drc_router, "list_changes_by_revision", list_changes_by_revision)


@pytest.fixture(autouse=True)
def patch_project_dataset_revisions_crud(
    monkeypatch: pytest.MonkeyPatch,
    project_dataset_revision_store: Dict[UUID, DummyProjectDatasetRevision],
    dataset_revision_store: Dict[UUID, DummyDatasetRevision],
):
    import routers.project_dataset_revisions as pdr_router

    async def create_project_dataset_revision(_db, payload):
        d = payload.model_dump()
        to_del = [k for k, v in project_dataset_revision_store.items() if v.project_id == payload.project_id]
        for k in to_del:
            project_dataset_revision_store.pop(k, None)
        obj = DummyProjectDatasetRevision(id=uuid4(), applied_at=datetime.utcnow(), **d)
        project_dataset_revision_store[obj.id] = obj
        return obj

    async def upsert_project_dataset_revision(_db, payload):
        return await create_project_dataset_revision(_db, payload)

    async def get_project_dataset_revision(_db, pdr_id: UUID):
        return project_dataset_revision_store.get(pdr_id)

    async def list_project_dataset_revisions_by_project(_db, project_id: UUID):
        return [o for o in project_dataset_revision_store.values() if o.project_id == project_id]

    async def update_project_dataset_revision(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_project_dataset_revision(_db, pdr_id: UUID) -> bool:
        return project_dataset_revision_store.pop(pdr_id, None) is not None

    async def get_revision_status(_db, revision_id: UUID):
        rev = dataset_revision_store.get(revision_id)
        if rev is None:
            # Default to 'published' for revisions not set up in the store,
            # so that old tests that don't configure the store still pass.
            return "published"
        return rev.status

    async def get_project(_db, project_id: UUID):
        # Return a dummy object with proponent_org_id so routes needing project context work in mock tests
        from types import SimpleNamespace
        return SimpleNamespace(id=project_id, proponent_org_id=None)

    monkeypatch.setattr(pdr_router, "get_project", get_project)
    monkeypatch.setattr(pdr_router, "create_project_dataset_revision", create_project_dataset_revision)
    monkeypatch.setattr(pdr_router, "upsert_project_dataset_revision", upsert_project_dataset_revision)
    monkeypatch.setattr(pdr_router, "get_project_dataset_revision", get_project_dataset_revision)
    monkeypatch.setattr(pdr_router, "list_project_dataset_revisions_by_project", list_project_dataset_revisions_by_project)
    monkeypatch.setattr(pdr_router, "update_project_dataset_revision", update_project_dataset_revision)
    monkeypatch.setattr(pdr_router, "delete_project_dataset_revision", delete_project_dataset_revision)
    monkeypatch.setattr(pdr_router, "get_revision_status", get_revision_status)


@pytest.fixture(autouse=True)
def patch_project_dataset_exclusions_crud(
    monkeypatch: pytest.MonkeyPatch,
    project_dataset_exclusion_store: Dict[UUID, DummyProjectDatasetExclusion],
):
    import routers.project_dataset_exclusions as pde_router

    async def create_project_dataset_exclusion(_db, payload):
        d = payload.model_dump()
        obj = DummyProjectDatasetExclusion(id=uuid4(), created_at=datetime.utcnow(), **d)
        project_dataset_exclusion_store[obj.id] = obj
        return obj

    async def get_project_dataset_exclusion(_db, eid: UUID):
        return project_dataset_exclusion_store.get(eid)

    async def list_exclusions_by_project(_db, project_id: UUID):
        return [o for o in project_dataset_exclusion_store.values() if o.project_id == project_id]

    async def update_project_dataset_exclusion(_db, obj, payload):
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        return obj

    async def delete_project_dataset_exclusion(_db, eid: UUID) -> bool:
        return project_dataset_exclusion_store.pop(eid, None) is not None

    monkeypatch.setattr(pde_router, "create_project_dataset_exclusion", create_project_dataset_exclusion)
    monkeypatch.setattr(pde_router, "get_project_dataset_exclusion", get_project_dataset_exclusion)
    monkeypatch.setattr(pde_router, "list_exclusions_by_project", list_exclusions_by_project)
    monkeypatch.setattr(pde_router, "update_project_dataset_exclusion", update_project_dataset_exclusion)
    monkeypatch.setattr(pde_router, "delete_project_dataset_exclusion", delete_project_dataset_exclusion)
