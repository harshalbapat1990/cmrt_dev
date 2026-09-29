# """
# services/grade1_asset_calculations.py

# Clean backend service for Grade 1 asset-level emissions calculations.

# Based on formula:
#   Product Stage (A1-A3) Emissions = 
#     Material Share (%) * Quantity * Product Stage Emission Intensity (tCO2e/$ material spend)
    
# Flow:
#   1. User inputs: Jurisdiction, Mastertype, Typecast, Sensitivity, Quantity, Functional Unit
#   2. Query v_grade1_asset_level_pivoted view for lookup data
#   3. Extract: Material Share + Emission Intensity for each stage (A1-A3, A4, A5)
#   4. Calculate: Emissions per stage
#   5. Return: Breakdown by stage + total
# """

from typing import List, Optional, Union
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services._calc_utils import round_result


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class Grade1CalculationRequest(BaseModel):
    """Input parameters for Grade 1 asset-level calculation"""
    jurisdiction: str              # e.g., "Australia"
    mastertype: str                # e.g., "Road"
    typecast: str                  # e.g., "Low Use Road"
    sensitivity: str               # "Low", "Mid", or "High"
    quantity: float                # CAPEX amount in dollars (or units depending on functional_unit)
    functional_unit: str = "CAPEX" # "CAPEX" or other functional unit types
    source: Optional[str] = None   # e.g., "CMRT MVP" - specific data source (optional)
    dataset_revision_id: Optional[UUID] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction": "Australia",
                "mastertype": "Road",
                "typecast": "Low Use Road",
                "sensitivity": "Mid",
                "quantity": 150000000,
                "functional_unit": "aud_material_spend",
                "source": "Grade 1 CAPEX Benchmarks (AU)"
            }
        }


class EmissionByStage(BaseModel):
    """Emissions for a single lifecycle stage"""
    stage: str                     # "A1-A3", "A4", "A5"
    material_share_pct: float      # Material share of capex (%)
    emission_intensity: float      # tCO2e/$ material spend or tCO2e/unit
    emissions_tco2e: float         # Calculated emissions in tCO2e


class Grade1CalculationResponse(BaseModel):
    """Response with emissions breakdown by stage"""
    jurisdiction: str
    mastertype: str
    typecast: str
    sensitivity: str
    quantity: float
    functional_unit: str
    source: Optional[str] = None
    
    # Breakdown by stage (simple float values in tCO2e)
    product_stage_a1a3: float      # Product Stage (A1-A3) emissions
    transport_a4: float            # Transport (A4) emissions
    construction_a5: float         # Construction (A5) emissions
    
    # Total
    total_emissions_tco2e: float
    
    # Debug: lookup data retrieved
    lookup_data: dict = None


class Grade1BatchCalculationRequest(BaseModel):
    """Batch wrapper — accepts a list of Grade 1 calculation requests"""
    items: List[Grade1CalculationRequest]


class Grade1BatchCalculationResponse(BaseModel):
    """Batch response with per-item results and error reporting"""
    results: List[Grade1CalculationResponse]
    total_count: int
    error_count: int
    errors: List[dict] = []  # {"index": int, "input": dict, "error": str}


# ─────────────────────────────────────────────────────────────────────────────
# Calculator Service
# ─────────────────────────────────────────────────────────────────────────────

class Grade1AssetCalculator:
    """Service for Grade 1 asset-level emissions calculations using PostgreSQL view"""
    
    async def calculate(
        self,
        db: AsyncSession,
        request: Grade1CalculationRequest
    ) -> Grade1CalculationResponse:
        """
        Calculate emissions for Grade 1 asset based on view v_grade1_asset_level_pivoted
        
        Args:
            db: Database session
            request: Calculation request with jurisdiction, mastertype, typecast, etc.
            
        Returns:
            Grade1CalculationResponse with emissions breakdown
            
        Raises:
            ValueError: If lookup data not found or invalid inputs
        """
        
        # Validate inputs
        self._validate_inputs(request)
        
        # Query the view
        lookup_data = await self._fetch_lookup_data(db, request)
        
        if not lookup_data:
            raise ValueError(
                f"No lookup data found for: "
                f"Jurisdiction={request.jurisdiction}, "
                f"Mastertype={request.mastertype}, "
                f"Typecast={request.typecast}, "
                f"Functional_Unit={request.functional_unit}"
            )
        
        # Calculate emissions for each stage - returns float values
        # Use material share only when the looked-up row has CAPEX material share data
        # (non-CAPEX rows have NULL in those columns so material_share_pct will be 0)
        use_material_share = lookup_data.get("Material share of capex - Mid") is not None
        material_share_key = "Material share of capex" if use_material_share else None

        a1a3_emissions = self._calculate_stage_emissions(
            quantity=request.quantity,
            sensitivity=request.sensitivity,
            lookup_data=lookup_data,
            stage_key_material_share=material_share_key,
            stage_key_intensity="Product stage (A1-A3)",
        )
        
        a4_emissions = self._calculate_stage_emissions(
            quantity=request.quantity,
            sensitivity=request.sensitivity,
            lookup_data=lookup_data,
            stage_key_material_share=material_share_key,
            stage_key_intensity="transport (A4)",
        )
        
        a5_emissions = self._calculate_stage_emissions(
            quantity=request.quantity,
            sensitivity=request.sensitivity,
            lookup_data=lookup_data,
            stage_key_material_share=material_share_key,
            stage_key_intensity="Construction (A5)",
        )
        
        # Calculate total
        total = a1a3_emissions + a4_emissions + a5_emissions
        
        return Grade1CalculationResponse(
            jurisdiction=request.jurisdiction,
            mastertype=request.mastertype,
            typecast=request.typecast,
            sensitivity=request.sensitivity,
            quantity=request.quantity,
            functional_unit=request.functional_unit,
            source=lookup_data.get("Source") if lookup_data else None,
            product_stage_a1a3=round_result(a1a3_emissions),
            transport_a4=round_result(a4_emissions),
            construction_a5=round_result(a5_emissions),
            total_emissions_tco2e=round_result(total),
            lookup_data=lookup_data,
        )
    
    async def calculate_batch(
        self,
        db: AsyncSession,
        requests: List[Grade1CalculationRequest],
    ) -> Grade1BatchCalculationResponse:
        """
        Calculate emissions for multiple Grade 1 assets.
        Each item is processed independently; failures are captured per-item
        and do not abort the remaining calculations.
        """
        results: List[Grade1CalculationResponse] = []
        errors: List[dict] = []

        for i, req in enumerate(requests):
            try:
                result = await self.calculate(db, req)
                results.append(result)
            except Exception as e:
                errors.append({"index": i, "input": req.model_dump(), "error": str(e)})

        return Grade1BatchCalculationResponse(
            results=results,
            total_count=len(requests),
            error_count=len(errors),
            errors=errors,
        )

    def _validate_inputs(self, request: Grade1CalculationRequest) -> None:
        """Validate input parameters"""
        if request.sensitivity not in ["Low", "Mid", "High"]:
            raise ValueError(f"Invalid sensitivity: {request.sensitivity}. Must be Low, Mid, or High.")
        
        if request.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {request.quantity}")
        
        if not request.jurisdiction or not request.mastertype or not request.typecast:
            raise ValueError("Jurisdiction, Mastertype, and Typecast are required")
    
    async def _fetch_lookup_data(
        self,
        db: AsyncSession,
        request: Grade1CalculationRequest
    ) -> Optional[dict]:
        """
        Query v_grade1_asset_level_pivoted view for lookup data
        
        Returns dict with columns as keys:
          {
            "Jurisdiction": "Australia",
            "Mastertype": "Road",
            "Typecast": "Low Use Road",
            "Source": "CMRT MVP",
            "Functional_Unit": "CAPEX",
            "Material share of capex - Low": 0.18,
            "Material share of capex - Mid": 0.23,
            "Material share of capex - High": 0.29,
            "Product stage (A1-A3) - Low": 0.0,
            "Product stage (A1-A3) - Mid": 0.0,
            "Product stage (A1-A3) - High": 0.001,
            "transport (A4) - Low": 0.0,
            "transport (A4) - Mid": 0.0,
            "transport (A4) - High": 0.0,
            "Construction (A5) - Low": 0.0,
            "Construction (A5) - Mid": 0.0,
            "Construction (A5) - High": 0.0,
          }
        """
        
        # CAPEX rows are distinguished by Functional_Unit = 'CAPEX'.
        # Non-CAPEX rows carry their actual unit code (e.g. "aud_material_spend", "lane_km").
        # Source is NOT used for routing — Functional_Unit is the single source of truth.

        # The legacy pivot view combines values from every dataset revision. When
        # the project supplies a revision, pivot the source rows here so all stage
        # intensities come from that revision only.
        if request.dataset_revision_id is not None:
            query = text("""
                SELECT
                    j.name AS "Jurisdiction",
                    mastertype.name AS "Mastertype",
                    typecast.name AS "Typecast",
                    bgm.source AS "Source",
                    unit.code AS "Functional_Unit",
                    MAX(CASE WHEN metric.code = 'material_share_capex'
                              AND bgm.lifecycle_module_code IS NULL
                              AND bgm.band_code = 'Low' THEN bgm.value END)
                        AS "Material share of capex - Low",
                    MAX(CASE WHEN metric.code = 'material_share_capex'
                              AND bgm.lifecycle_module_code IS NULL
                              AND bgm.band_code = 'Mid' THEN bgm.value END)
                        AS "Material share of capex - Mid",
                    MAX(CASE WHEN metric.code = 'material_share_capex'
                              AND bgm.lifecycle_module_code IS NULL
                              AND bgm.band_code = 'High' THEN bgm.value END)
                        AS "Material share of capex - High",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A1-A3'
                              AND bgm.band_code = 'Low' THEN bgm.value END)
                        AS "Product stage (A1-A3) - Low",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A1-A3'
                              AND bgm.band_code = 'Mid' THEN bgm.value END)
                        AS "Product stage (A1-A3) - Mid",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A1-A3'
                              AND bgm.band_code = 'High' THEN bgm.value END)
                        AS "Product stage (A1-A3) - High",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A4'
                              AND bgm.band_code = 'Low' THEN bgm.value END)
                        AS "transport (A4) - Low",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A4'
                              AND bgm.band_code = 'Mid' THEN bgm.value END)
                        AS "transport (A4) - Mid",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A4'
                              AND bgm.band_code = 'High' THEN bgm.value END)
                        AS "transport (A4) - High",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A5'
                              AND bgm.band_code = 'Low' THEN bgm.value END)
                        AS "Construction (A5) - Low",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A5'
                              AND bgm.band_code = 'Mid' THEN bgm.value END)
                        AS "Construction (A5) - Mid",
                    MAX(CASE WHEN bgm.lifecycle_module_code = 'A5'
                              AND bgm.band_code = 'High' THEN bgm.value END)
                        AS "Construction (A5) - High"
                FROM background_grade_metrics bgm
                JOIN jurisdictions j ON j.id = bgm.jurisdiction_id
                JOIN benchmark_mastertypes mastertype ON mastertype.id = bgm.mastertype_id
                JOIN benchmark_typecasts typecast ON typecast.id = bgm.typecast_id
                JOIN metric_types metric ON metric.id = bgm.metric_type_id
                LEFT JOIN units unit ON unit.id = bgm.unit_id
                WHERE bgm.grade_id = 1
                  AND bgm.is_active = TRUE
                  AND bgm.dataset_revision_id = :dataset_revision_id
                  AND j.name = :jurisdiction
                  AND mastertype.name = :mastertype
                  AND typecast.name = :typecast
                  AND unit.code = :functional_unit
                  AND (CAST(:source AS TEXT) IS NULL OR bgm.source = :source)
                GROUP BY j.name, mastertype.name, typecast.name, bgm.source, unit.code
                ORDER BY bgm.source
            """)
            result = await db.execute(
                query,
                {
                    "dataset_revision_id": request.dataset_revision_id,
                    "jurisdiction": request.jurisdiction,
                    "mastertype": request.mastertype,
                    "typecast": request.typecast,
                    "functional_unit": request.functional_unit,
                    "source": request.source,
                },
            )
            rows = result.fetchall()
            if not rows:
                return None
            lookup_dict = dict(rows[0]._mapping)
            for key, value in lookup_dict.items():
                if isinstance(value, Decimal):
                    lookup_dict[key] = float(value)
            return lookup_dict

        if request.functional_unit == "CAPEX":
            query = text("""
                SELECT 
                    "Jurisdiction",
                    "Mastertype",
                    "Typecast",
                    "Source",
                    "Functional_Unit",
                    "Material share of capex - Low",
                    "Material share of capex - Mid",
                    "Material share of capex - High",
                    "Product stage (A1-A3) - Low",
                    "Product stage (A1-A3) - Mid",
                    "Product stage (A1-A3) - High",
                    "transport (A4) - Low",
                    "transport (A4) - Mid",
                    "transport (A4) - High",
                    "Construction (A5) - Low",
                    "Construction (A5) - Mid",
                    "Construction (A5) - High"
                FROM v_grade1_asset_level_pivoted
                WHERE "Jurisdiction" = :jurisdiction
                  AND "Mastertype" = :mastertype
                  AND "Typecast" = :typecast
                  AND "Functional_Unit" = 'CAPEX'
            """)
            result = await db.execute(
                query,
                {
                    "jurisdiction": request.jurisdiction,
                    "mastertype": request.mastertype,
                    "typecast": request.typecast,
                }
            )
        else:
            query = text("""
                SELECT 
                    "Jurisdiction",
                    "Mastertype",
                    "Typecast",
                    "Source",
                    "Functional_Unit",
                    "Material share of capex - Low",
                    "Material share of capex - Mid",
                    "Material share of capex - High",
                    "Product stage (A1-A3) - Low",
                    "Product stage (A1-A3) - Mid",
                    "Product stage (A1-A3) - High",
                    "transport (A4) - Low",
                    "transport (A4) - Mid",
                    "transport (A4) - High",
                    "Construction (A5) - Low",
                    "Construction (A5) - Mid",
                    "Construction (A5) - High"
                FROM v_grade1_asset_level_pivoted
                WHERE "Jurisdiction" = :jurisdiction
                  AND "Mastertype" = :mastertype
                  AND "Typecast" = :typecast
                  AND "Functional_Unit" = :functional_unit
                  AND (CAST(:source AS TEXT) IS NULL OR "Source" = :source)
            """)
            result = await db.execute(
                query,
                {
                    "jurisdiction": request.jurisdiction,
                    "mastertype": request.mastertype,
                    "typecast": request.typecast,
                    "functional_unit": request.functional_unit,
                    "source": request.source,
                }
            )
        
        rows = result.fetchall()
        if not rows:
            return None
        
        lookup_dict = dict(rows[0]._mapping)
        
        # Convert all numeric values from Decimal to float (PostgreSQL returns Decimal for numeric columns)
        for key, value in lookup_dict.items():
            if isinstance(value, Decimal):
                lookup_dict[key] = float(value)
        
        return lookup_dict
    
    def _calculate_stage_emissions(
        self,
        quantity: float,
        sensitivity: str,
        lookup_data: dict,
        stage_key_material_share: Optional[str],
        stage_key_intensity: str,
    ) -> float:
        """
        Calculate emissions for a single lifecycle stage.
        
        Returns: float value in tCO2e
        
        CAPEX rows apply the material share to each lifecycle stage:
          Emissions = Material Share * Quantity * Stage Emission Intensity
        Non-CAPEX rows have no material share and use quantity * intensity.
        """
        
        # Extract material share if applicable
        # Material share values are stored as decimals (e.g. 0.23, not 23.0)
        material_share_pct = 0.0
        if stage_key_material_share:
            material_share_key = f"{stage_key_material_share} - {sensitivity}"
            material_share_pct = float(lookup_data.get(material_share_key, 0.0) or 0.0)
        
        # Extract emission intensity
        intensity_key = f"{stage_key_intensity} - {sensitivity}"
        emission_intensity = float(lookup_data.get(intensity_key, 0.0) or 0.0)
        
        # Ensure quantity is float
        quantity = float(quantity)
        
        # Calculate emissions
        if stage_key_material_share:
            # A1-A3: includes material share
            emissions = material_share_pct * quantity * emission_intensity
        else:
            # A4, A5: no material share
            emissions = quantity * emission_intensity
        
        return emissions


# Singleton instance
calculator = Grade1AssetCalculator()
