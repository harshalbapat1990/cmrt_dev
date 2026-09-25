"""
Tests for the activity-data endpoints covering the Business Case / Construction
sub-stage scenario:

  - Asset level  entry  →  backed by a Grade 1 BGM record
  - Component level entry  →  backed by a Grade 2 BGM record

The suite uses the shared `client` fixture (in-process ASGI, no real DB).
All CRUD calls that touch the real database are monkeypatched with lightweight
in-memory implementations that mirror the router's expectations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest


# ---------------------------------------------------------------------------
# Lightweight in-memory data classes mirroring the ORM models
# ---------------------------------------------------------------------------

@dataclass
class _StageInstance:
    id: UUID
    project_id: UUID
    stage: str
    approval_status: str = "draft"
    num_reports_required: int = 2
    sequence: int = 1
    frequency: Optional[str] = None


@dataclass
class _ProjectOption:
    id: UUID
    project_id: UUID
    stage_instance_id: UUID
    option_number: int
    label: str
    created_at: Optional[datetime] = None


@dataclass
class _BGM:
    id: UUID
    dataset_revision_id: Optional[UUID]
    grade_id: int
    metric_type_id: UUID
    mastertype_id: Optional[UUID] = None
    typecast_id: Optional[UUID] = None
    emissions_category_id: Optional[UUID] = None
    emissions_subcategory_id: Optional[UUID] = None
    band_code: Optional[str] = None
    unit_id: Optional[UUID] = None
    value: Optional[Decimal] = None
    lifecycle_module_code: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class _ActivityData:
    id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    quantity: Decimal
    unit_id: UUID
    ui_table_key: str
    metric_id: Optional[UUID] = None
    project_option_id: Optional[UUID] = None
    extra_fields: Optional[dict] = None
    lifecycle_module_code: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    # Computed after create
    emissions_tco2e: Optional[Decimal] = None


@dataclass
class _EmissionsResult:
    id: UUID
    activity_data_id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    value: Optional[Decimal]
    unit_id: Optional[UUID]
    lifecycle_module_code: Optional[str]
    computed_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Module-level stores shared across fixtures within a test
# ---------------------------------------------------------------------------

class _Stores:
    """Holds all in-memory stores for a single test run."""

    def __init__(self):
        self.stage_instances: Dict[UUID, _StageInstance] = {}
        self.bgm: Dict[UUID, _BGM] = {}
        self.activity_data: Dict[UUID, _ActivityData] = {}
        self.emissions_results: Dict[UUID, _EmissionsResult] = {}
        self.project_options: Dict[UUID, _ProjectOption] = {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def stores() -> _Stores:
    return _Stores()


@pytest.fixture
def bc_stage_instance(stores: _Stores) -> _StageInstance:
    """A BUSINESS_CASE stage instance with 2 reports required."""
    si = _StageInstance(
        id=uuid4(),
        project_id=uuid4(),
        stage="BUSINESS_CASE",
        num_reports_required=2,
    )
    stores.stage_instances[si.id] = si
    return si


@pytest.fixture(autouse=True)
def grant_activity_stage_edit_access(monkeypatch, bc_stage_instance):
    """
    Activity-data CRUD tests require EDIT access to the stage.
    The new authorization model does not give SUPER_ADMIN implicit
    project/stage access.
    """
    import routers.activity_data as ad_router

    async def _require_stage_access(
        db,
        principal,
        project_id,
        stage_instance_id,
        minimum_access,
    ):
        return None

    monkeypatch.setattr(
        ad_router,
        "require_stage_access",
        _require_stage_access,
    )

    
@pytest.fixture
def grade1_bgm(stores: _Stores) -> _BGM:
    """Grade 1 BGM record – used for asset-level entries."""
    bgm = _BGM(
        id=uuid4(),
        dataset_revision_id=uuid4(),
        grade_id=1,
        metric_type_id=uuid4(),
        band_code="Mid",
        unit_id=uuid4(),
        value=Decimal("1.250"),
        lifecycle_module_code="A1-A3",
    )
    stores.bgm[bgm.id] = bgm
    return bgm


@pytest.fixture
def grade2_bgm(stores: _Stores) -> _BGM:
    """Grade 2 BGM record – used for component-level entries."""
    bgm = _BGM(
        id=uuid4(),
        dataset_revision_id=uuid4(),
        grade_id=2,
        metric_type_id=uuid4(),
        emissions_category_id=uuid4(),
        emissions_subcategory_id=uuid4(),
        unit_id=uuid4(),
        value=Decimal("0.750"),
        lifecycle_module_code="A4",
    )
    stores.bgm[bgm.id] = bgm
    return bgm


@pytest.fixture
def option1(stores: _Stores, bc_stage_instance: _StageInstance) -> _ProjectOption:
    """Option 1 for the Business Case stage instance."""
    opt = _ProjectOption(
        id=uuid4(),
        project_id=bc_stage_instance.project_id,
        stage_instance_id=bc_stage_instance.id,
        option_number=1,
        label="Option 1",
        created_at=datetime.utcnow(),
    )
    stores.project_options[opt.id] = opt
    return opt


@pytest.fixture(autouse=True)
def patch_activity_data_deps(monkeypatch: pytest.MonkeyPatch, stores: _Stores):
    """
    Monkeypatch all CRUD and service calls used by the activity-data router so
    tests never touch a real database.
    """
    import routers.activity_data as ad_router
    from decimal import Decimal as _D

    # ---- get_project_stage_instance ----------------------------------------
    async def _get_stage_instance(_db, instance_id: UUID):
        return stores.stage_instances.get(instance_id)

    monkeypatch.setattr(ad_router, "get_project_stage_instance", _get_stage_instance)

    # ---- create_activity_data -----------------------------------------------
    async def _create_activity_data(_db, payload):
        obj = _ActivityData(
            id=uuid4(),
            project_id=payload.project_id,
            project_stage_instance_id=payload.project_stage_instance_id,
            metric_id=payload.metric_id,
            quantity=payload.quantity,
            unit_id=payload.unit_id,
            ui_table_key=payload.ui_table_key,
            project_option_id=payload.project_option_id,
            extra_fields=payload.extra_fields,
            lifecycle_module_code=payload.lifecycle_module_code,
        )
        stores.activity_data[obj.id] = obj
        return obj

    monkeypatch.setattr(ad_router, "create_activity_data", _create_activity_data)

    # ---- get_activity_data --------------------------------------------------
    async def _get_activity_data(_db, row_id: UUID):
        return stores.activity_data.get(row_id)

    monkeypatch.setattr(ad_router, "get_activity_data", _get_activity_data)

    # ---- list_activity_data -------------------------------------------------
    async def _list_activity_data(_db, stage_instance_id, ui_table_key, project_option_id=None, skip=0, limit=500):
        results = [
            r for r in stores.activity_data.values()
            if r.project_stage_instance_id == stage_instance_id
            and r.ui_table_key == ui_table_key
        ]
        if project_option_id is not None:
            results = [r for r in results if r.project_option_id == project_option_id]
        return results[skip: skip + limit]

    monkeypatch.setattr(ad_router, "list_activity_data", _list_activity_data)

    # ---- update_activity_data -----------------------------------------------
    async def _update_activity_data(_db, row_id: UUID, patch):
        obj = stores.activity_data.get(row_id)
        if not obj:
            return None
        for k, v in patch.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        return obj

    monkeypatch.setattr(ad_router, "update_activity_data", _update_activity_data)

    # ---- delete_activity_data -----------------------------------------------
    async def _delete_activity_data(_db, row_id: UUID):
        if row_id in stores.activity_data:
            del stores.activity_data[row_id]
            return True
        return False

    monkeypatch.setattr(ad_router, "delete_activity_data", _delete_activity_data)

    # ---- calculate_and_store ------------------------------------------------
    async def _calculate_and_store(_db, activity_row):
        """Simulate emission = quantity × bgm.value and attach to the row."""
        bgm = stores.bgm.get(activity_row.metric_id)
        if bgm and bgm.value is not None:
            tco2e = activity_row.quantity * bgm.value
            activity_row.emissions_tco2e = tco2e
            # Store a synthetic emissions result
            er = _EmissionsResult(
                id=uuid4(),
                activity_data_id=activity_row.id,
                project_id=activity_row.project_id,
                project_stage_instance_id=activity_row.project_stage_instance_id,
                value=tco2e,
                unit_id=bgm.unit_id,
                lifecycle_module_code=bgm.lifecycle_module_code,
            )
            stores.emissions_results[er.id] = er
        return activity_row.emissions_tco2e

    monkeypatch.setattr(ad_router, "calculate_and_store", _calculate_and_store)

    # ---- enrich_with_emissions ----------------------------------------------
    async def _enrich_with_emissions(_db, obj):
        """Return a dict shaped like ActivityDataOut so the router can serialise it."""
        from schemas.activity_data import ActivityDataOut
        return ActivityDataOut(
            id=obj.id,
            project_id=obj.project_id,
            project_stage_instance_id=obj.project_stage_instance_id,
            metric_id=obj.metric_id,
            quantity=obj.quantity,
            unit_id=obj.unit_id,
            ui_table_key=obj.ui_table_key,
            project_option_id=obj.project_option_id,
            extra_fields=obj.extra_fields,
            lifecycle_module_code=obj.lifecycle_module_code,
            created_by=obj.created_by,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            emissions_tco2e=obj.emissions_tco2e,
        )

    monkeypatch.setattr(ad_router, "enrich_with_emissions", _enrich_with_emissions)


def _asset_payload(
    project_id: UUID,
    stage_instance_id: UUID,
    metric_id: UUID,
    unit_id: UUID,
    project_option_id: Optional[UUID] = None,
    quantity: str = "100.00",
) -> dict:
    return {
        "project_id": str(project_id),
        "project_stage_instance_id": str(stage_instance_id),
        "metric_id": str(metric_id),
        "unit_id": str(unit_id),
        "quantity": quantity,
        "ui_table_key": "asset",
        "project_option_id": str(project_option_id) if project_option_id else None,
        "extra_fields": {
            "mastertype_name": "New Construction",
            "band_code": "Mid",
            "notes": "Asset level test row",
        },
    }


def _component_payload(
    project_id: UUID,
    stage_instance_id: UUID,
    metric_id: UUID,
    unit_id: UUID,
    project_option_id: Optional[UUID] = None,
    quantity: str = "50.00",
) -> dict:
    return {
        "project_id": str(project_id),
        "project_stage_instance_id": str(stage_instance_id),
        "metric_id": str(metric_id),
        "unit_id": str(unit_id),
        "quantity": quantity,
        "ui_table_key": "component",
        "project_option_id": str(project_option_id) if project_option_id else None,
        "extra_fields": {
            "emissions_category": "Materials",
            "emissions_subcategory": "Road base",
            "emissions_source_name": "Crushed rock",
            "notes": "Component level test row",
        },
    }


class TestAssetLevelEntryGrade1:
    """
    Verify that a data-entry row can be created for the Asset level table
    in the Business Case / Construction sub-stage, backed by a Grade 1 BGM.
    """

    async def test_create_asset_row_returns_201(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        resp = await client.post("/api/activity-data", json=payload)
        assert resp.status_code == 201

    async def test_create_asset_row_has_correct_ui_table_key(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["ui_table_key"] == "asset"

    async def test_create_asset_row_stores_metric_id(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["metric_id"] == str(grade1_bgm.id)

    async def test_create_asset_row_calculates_emissions_tco2e(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        """
        100 units × Grade 1 factor (1.250) = 125.000 tCO₂e
        """
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
            quantity="100",
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["emissions_tco2e"] is not None
        assert Decimal(data["emissions_tco2e"]) == Decimal("125.000")

    async def test_create_asset_row_links_to_option(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["project_option_id"] == str(option1.id)

    async def test_list_asset_rows_returns_created_entry(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        created = (await client.post("/api/activity-data", json=payload)).json()

        resp = await client.get(
            "/api/activity-data",
            params={
                "stage_instance_id": str(bc_stage_instance.id),
                "ui_table_key": "asset",
                "project_option_id": str(option1.id),
            },
        )
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert created["id"] in ids

    async def test_patch_asset_row_recalculates_emissions(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        """
        After patching quantity to 200, emissions_tco2e should be 200 × 1.250 = 250.000
        """
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
            quantity="100",
        )
        row_id = (await client.post("/api/activity-data", json=payload)).json()["id"]

        patch_resp = await client.patch(
            f"/api/activity-data/{row_id}",
            json={"quantity": "200"},
        )
        assert patch_resp.status_code == 200
        assert Decimal(patch_resp.json()["emissions_tco2e"]) == Decimal("250.000")

    async def test_delete_asset_row(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _asset_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
            project_option_id=option1.id,
        )
        row_id = (await client.post("/api/activity-data", json=payload)).json()["id"]

        del_resp = await client.delete(f"/api/activity-data/{row_id}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/activity-data/{row_id}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — Component level (Grade 2 BGM)
# ---------------------------------------------------------------------------

class TestComponentLevelEntryGrade2:
    """
    Verify that a data-entry row can be created for the Component level table
    in the Business Case / Construction sub-stage, backed by a Grade 2 BGM.
    """

    async def test_create_component_row_returns_201(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
        )
        resp = await client.post("/api/activity-data", json=payload)
        assert resp.status_code == 201

    async def test_create_component_row_has_correct_ui_table_key(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["ui_table_key"] == "component"

    async def test_create_component_row_stores_grade2_metric_id(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["metric_id"] == str(grade2_bgm.id)

    async def test_create_component_row_calculates_emissions_tco2e(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        """
        50 units × Grade 2 factor (0.750) = 37.500 tCO₂e
        """
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
            quantity="50",
        )
        data = (await client.post("/api/activity-data", json=payload)).json()
        assert data["emissions_tco2e"] is not None
        assert Decimal(data["emissions_tco2e"]) == Decimal("37.500")

    async def test_component_row_isolated_from_asset_rows(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        """Listing component rows must not return asset rows and vice versa."""
        await client.post(
            "/api/activity-data",
            json=_asset_payload(
                project_id=bc_stage_instance.project_id,
                stage_instance_id=bc_stage_instance.id,
                metric_id=grade1_bgm.id,
                unit_id=grade1_bgm.unit_id,
                project_option_id=option1.id,
            ),
        )
        comp_id = (await client.post(
            "/api/activity-data",
            json=_component_payload(
                project_id=bc_stage_instance.project_id,
                stage_instance_id=bc_stage_instance.id,
                metric_id=grade2_bgm.id,
                unit_id=grade2_bgm.unit_id,
                project_option_id=option1.id,
            ),
        )).json()["id"]

        asset_list = (await client.get(
            "/api/activity-data",
            params={
                "stage_instance_id": str(bc_stage_instance.id),
                "ui_table_key": "asset",
                "project_option_id": str(option1.id),
            },
        )).json()
        comp_list = (await client.get(
            "/api/activity-data",
            params={
                "stage_instance_id": str(bc_stage_instance.id),
                "ui_table_key": "component",
                "project_option_id": str(option1.id),
            },
        )).json()

        assert all(r["ui_table_key"] == "asset" for r in asset_list)
        assert all(r["ui_table_key"] == "component" for r in comp_list)
        assert comp_id in [r["id"] for r in comp_list]
        assert comp_id not in [r["id"] for r in asset_list]

    async def test_patch_component_row_recalculates_emissions(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        """
        After patching quantity to 80, emissions = 80 × 0.750 = 60.000
        """
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
            quantity="50",
        )
        row_id = (await client.post("/api/activity-data", json=payload)).json()["id"]

        patch_resp = await client.patch(
            f"/api/activity-data/{row_id}",
            json={"quantity": "80"},
        )
        assert patch_resp.status_code == 200
        assert Decimal(patch_resp.json()["emissions_tco2e"]) == Decimal("60.000")

    async def test_delete_component_row(
        self,
        client,
        bc_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
        option1: _ProjectOption,
    ):
        payload = _component_payload(
            project_id=bc_stage_instance.project_id,
            stage_instance_id=bc_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
            project_option_id=option1.id,
        )
        row_id = (await client.post("/api/activity-data", json=payload)).json()["id"]

        del_resp = await client.delete(f"/api/activity-data/{row_id}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/activity-data/{row_id}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — Stage-locked guard (final_approved stage rejects writes)
# ---------------------------------------------------------------------------

class TestStageLockGuard:
    """
    Both asset-level and component-level writes must be rejected with 403
    when the stage instance is final_approved.
    """

    @pytest.fixture
    def locked_stage_instance(self, stores: _Stores) -> _StageInstance:
        si = _StageInstance(
            id=uuid4(),
            project_id=uuid4(),
            stage="BUSINESS_CASE",
            approval_status="final_approved",
        )
        stores.stage_instances[si.id] = si
        return si

    async def test_asset_row_rejected_when_stage_locked(
        self,
        client,
        locked_stage_instance: _StageInstance,
        grade1_bgm: _BGM,
    ):
        payload = _asset_payload(
            project_id=locked_stage_instance.project_id,
            stage_instance_id=locked_stage_instance.id,
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
        )
        resp = await client.post("/api/activity-data", json=payload)
        assert resp.status_code == 403

    async def test_component_row_rejected_when_stage_locked(
        self,
        client,
        locked_stage_instance: _StageInstance,
        grade2_bgm: _BGM,
    ):
        payload = _component_payload(
            project_id=locked_stage_instance.project_id,
            stage_instance_id=locked_stage_instance.id,
            metric_id=grade2_bgm.id,
            unit_id=grade2_bgm.unit_id,
        )
        resp = await client.post("/api/activity-data", json=payload)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests — Stage instance not found
# ---------------------------------------------------------------------------

class TestStageInstanceNotFound:

    async def test_create_asset_row_404_when_stage_instance_missing(self, client, grade1_bgm: _BGM):
        payload = _asset_payload(
            project_id=uuid4(),
            stage_instance_id=uuid4(),     # random — not in stores
            metric_id=grade1_bgm.id,
            unit_id=grade1_bgm.unit_id,
        )
        resp = await client.post("/api/activity-data", json=payload)
        assert resp.status_code == 404
