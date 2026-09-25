import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.bootstrap import ensure_super_admin
from core.config import settings
from core.limiter import limiter
from core.session import get_engine
from routers.lookup_data import router as lookup_router
from routers.emissions_entries import router as entries_router
from routers.view_emission_factor_values_pivot import router as pivot_router
from routers.project import router as project_router
from routers.project_reporting_submission import router as submission_router
from routers.roles import router as roles_router
from routers.users import router as users_router

from routers.postcode_admin import router as postcode_admin_router
from routers.postcode import router as postcode_router
from routers.organization import router as organizations_router
from routers.project_type import router as project_type_router

# Jurisdictions & Staging Model package
from routers.jurisdictions import router as jurisdictions_router
from routers.anz_reporting_stages import router as anz_reporting_stages_router
from routers.jurisdiction_reporting_stages import router as jurisdiction_reporting_stages_router
from routers.ghg_scopes import router as ghg_scopes_router
from routers.units import router as units_router
from routers.unit_conversions import router as unit_conversions_router
from routers.emissions_categories import router as emissions_categories_router

from routers.permissions import router as permissions_router
from routers.role_permissions import router as role_permissions_router
from routers.user_roles import router as user_roles_router
from routers.org_admin import router as org_admin_router
from routers.project_access import router as project_access_router

#Identity, Auth & Access Management
from routers.identity import router as identity_router
from routers.access_requests import router as access_requests_router
from routers.organization_domains import router as org_domains_router
from routers.me import router as me_router

# Defaults & Materials package
from routers.materials import router as materials_router
from routers.material_recycled_content import router as material_recycled_content_router
from routers.densities import router as densities_router
from routers.waste_treatments import router as waste_treatments_router
from routers.default_transport_distances import router as default_transport_distances_router
from routers.default_waste_rates import router as default_waste_rates_router
from routers.base_case_assumptions import router as base_case_assumptions_router
from routers.proponent_assumption_overrides import router as proponent_assumption_overrides_router

# Package F — Dataset Revisions
from routers.dataset_revisions import router as dataset_revisions_router
from routers.project_dataset_revisions import router as project_dataset_revisions_router
from routers.dataset_revision_changes import router as dataset_revision_changes_router
from routers.emissions_factor_sets import router as emissions_factor_sets_router

# Package G — Unified Grade Metrics
from routers.grade_definitions import router as grade_definitions_router
from routers.value_bands import router as value_bands_router
from routers.metric_types import router as metric_types_router
from routers.background_grade_metrics import router as background_grade_metrics_router
from routers.project_dataset_exclusions import router as project_dataset_exclusions_router
from routers.benchmark_mastertypes import router as benchmark_mastertypes_router
from routers.benchmark_typecasts import router as benchmark_typecasts_router

# Governance & Audit
from routers.audit_logs import router as audit_logs_router
from routers.project_stage_instances import router as project_stage_instances_router
from routers.project_stage_config import (
    router as project_stage_config_router
)
import models.stage_approval_events
import models.emissions_factor_sets

# Vehicle Reference Data
from routers.vehicle_classes import router as vehicle_classes_router
from routers.vehicle_masses import router as vehicle_masses_router
from routers.interrupted_vehicles import router as interrupted_vehicles_router
from routers.uninterrupted_vehicles import router as uninterrupted_vehicles_router
from routers.vehicle_energy_conversion_rates import router as vehicle_energy_conversion_rates_router
import models.vehicle_classes
import models.vehicle_masses
import models.interrupted_vehicles
import models.uninterrupted_vehicles
import models.vehicle_energy_conversion_rates

# Electricity Decarbonisation Scenarios & Carbon Values
from routers.electric_decarb_factors import router as electric_decarb_factors_router
from routers.carbon_values import router as carbon_values_router


#**************** Calculations Router *******************
# Grade 1 & 2 Calculations, b4 replacement calculations, Detailed Level Electricity Calculations
from routers.grade1_calculations import router as grade1_calculations_router
from routers.grade2_calculations import router as grade2_calculations_router
from routers.grade2_b4_replacement_calculations import router as grade2_b4_replacement_router
from routers.electricity_detailed_calculations import router as electricity_detailed_calculations_router
# Grade 3/4 Detailed Level - Construction Stage Calculations
from routers.grade34_detailed_level_construction_calcs import router as grade34_detailed_level_construction_calcs_router
# Component Level - Maintenance (B2-5) Stage Calculations
from routers.maintenance_replacement_component_level_calcs import router as maintenance_replacement_component_level_calcs_router
# Detailed Level - Maintenance (B2-5) Stage Calculations
from routers.grade34_detailed_level_maintenance_calcs import router as grade34_detailed_level_maintenance_calcs_router
# Component Level - Operational Energy (B6) Calculations
from routers.operational_component_level_calcs import router as operational_component_level_calcs_router
from routers.electricity_calculations import router as electricity_calculations_router
# Component Level - In Use (B1) Gases Calculations
from routers.inuse_gases_calculations import router as inuse_gases_calculations_router
# Detailed Level - Maintenance (B1) Stage Calculations
from routers.detailed_level_maintenance_calculations import router as detailed_level_maintenance_calculations_router
# Detailed Level - Maintenance (B2-B5) Stage Calculations
from routers.detailed_level_maintenance_b2_b5_calculations import router as detailed_level_maintenance_b2_b5_calculations_router
# Detailed Level - Operational Energy (B6) & Water (B7) - Fuel/Water
from routers.detailed_level_fuel_water import router as detailed_level_fuel_water_router
# Detailed Level - Operational Energy (B6) & Water (B7) - Electricity
from routers.detailed_level_calcs_operational_elec import router as detailed_level_operational_elec_router
# User Emissions (B8) Calculations - NZ, AUS Small & Rail
from routers.user_emissions_nz_calculations import router as user_emissions_nz_router
from routers.user_emissions_aus_small_calculations import router as user_emissions_aus_small_router
from routers.user_emissions_rail_calculations import router as user_emissions_rail_router
from routers.user_emissions_aus_large_road_calculations import router as user_emissions_aus_large_road_router
from routers.concrete_mix_register_calculations import router as concrete_mix_register_calculations_router
from routers.user_emissions_nz_large_road_calculations import router as user_emissions_nz_large_road_router


from routers.electricity_calculations import router as electricity_calculations_router

# EV Uptake, VEPM & Freight Rail
from routers.ev_uptake_factors import router as ev_uptake_factors_router
from routers.vepm_factors import router as vepm_factors_router
from routers.freight_rail_factors import router as freight_rail_factors_router
from routers.maintenance_replacement_factors import router as maintenance_replacement_factors_router
from routers.fugitives import router as fugitives_router
from routers.default_wastage_rate import router as default_wastage_rate_router
from routers.renewable_energy_classification import router as renewable_energy_classification_router
from routers.energy_density_conversions import router as energy_density_conversions_router
from routers.operational_equipment import router as operational_equipment_router
from routers.user_guide import router as user_guide_router
from routers.user_guide_videos import router as user_guide_videos_router
from routers.terms_documents import router as terms_documents_router

# Data Entry Storage Layer
from routers.activity_data import router as activity_data_router
from routers.project_mitigations import router as project_mitigations_router
from routers.construction_periods import router as construction_periods_router
from routers.project_options import router as project_options_router

# Concrete Register (grade 3/4)
from routers.concrete_register import router as concrete_register_router

# Business-as-usual Assumptions — Default concrete mix designs
from routers.concrete_mix_design import router as concrete_mix_design_router
from routers.direct_substitutions import router as direct_substitutions_router
from routers.electricity_recycling_assumptions import router as electricity_recycling_assumptions_router

# Recycled Content Factors
from routers.recycled_content_factors import router as recycled_content_factors_router


# Dashboard Results
from routers.org_dashboard_energy import router as org_dashboard_energy_router
from routers.org_dashboard_hotspots import router as org_dashboard_hotspots_router
from routers.org_dashboard_waste import router as org_dashboard_waste_router
from routers.org_dashboard_materials import router as org_dashboard_materials_router
from routers.org_dashboard_emissions_breakdown import router as org_dashboard_emissions_breakdown_router
from routers.org_dashboard_user_emissions import router as org_dashboard_user_emissions_router
from routers.org_dashboard_carbon_valuation import router as org_dashboard_carbon_valuation_router
from routers.org_dashboard_carbon_storage import router as org_dashboard_carbon_storage_router
from routers.org_dashboard_scope_breakdown import router as org_dashboard_scope_breakdown_router

from routers.dashboard_offsetting import router as dashboard_offsetting_router
from routers.dashboard_waste import router as dashboard_waste_router
from routers.dashboard_materials import router as dashboard_materials_router
from routers.dashboard_energy import router as dashboard_energy_router
from routers.dashboard_hotspots import router as dashboard_hotspots_router
from routers.dashboard_comparison import router as dashboard_comparison_router
from routers.dashboard_user_emissions import router as dashboard_user_emissions_router
from routers.dashboard_emissions_breakdown import router as dashboard_emissions_breakdown_router
from routers.completeness_emissions_breakdown import router as completeness_emissions_breakdown_router
from routers.dashboard_scope_breakdown import router as dashboard_scope_breakdown_router
from routers.dashboard_options_comparison import router as dashboard_options_comparison_router
from routers.dashboard_carbon_valuation import router as dashboard_carbon_valuation_router
from routers.dashboard_carbon_storage import router as dashboard_carbon_storage_router
from routers.dashboard_mitigation_summary import router as dashboard_mitigation_summary_router
from routers.dashboard_itmm_reporting import router as dashboard_itmm_reporting_router
from routers.dashboard_ratings import router as dashboard_ratings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_super_admin(get_engine())
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = settings.cors_origins_list
print(f"CORS allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

logger = logging.getLogger("uvicorn.error")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception for %s %s", request.method, request.url)
    origin = request.headers.get("origin", "")
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
    } if origin in origins else {}
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
        headers=headers,
    )

app.include_router(lookup_router)
app.include_router(entries_router)
app.include_router(pivot_router)
app.include_router(project_router)
app.include_router(submission_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(postcode_admin_router)
app.include_router(postcode_router)
app.include_router(organizations_router)
app.include_router(project_type_router)
app.include_router(jurisdictions_router)
app.include_router(anz_reporting_stages_router)
app.include_router(jurisdiction_reporting_stages_router)
app.include_router(ghg_scopes_router)
app.include_router(units_router)
app.include_router(unit_conversions_router)
app.include_router(emissions_categories_router)
app.include_router(permissions_router)
app.include_router(role_permissions_router)
app.include_router(user_roles_router)
app.include_router(org_admin_router)
app.include_router(project_access_router)
# Identity, Auth & Access Management
app.include_router(identity_router)
app.include_router(access_requests_router)
app.include_router(org_domains_router)
app.include_router(me_router)
# Development-only token minting — registered ONLY when APP_ENV=local
if settings.app_env == "local":
    from routers.auth_dev import router as _auth_dev_router
    app.include_router(_auth_dev_router)
# Defaults & Materials package
app.include_router(materials_router)
app.include_router(material_recycled_content_router)
app.include_router(densities_router)
app.include_router(waste_treatments_router)
app.include_router(default_transport_distances_router)
app.include_router(default_waste_rates_router)
app.include_router(base_case_assumptions_router)
app.include_router(proponent_assumption_overrides_router)
# Package F — Dataset Revisions
app.include_router(dataset_revisions_router)
app.include_router(project_dataset_revisions_router)
app.include_router(dataset_revision_changes_router)
app.include_router(emissions_factor_sets_router)
# Package G — Unified Grade Metrics
app.include_router(grade_definitions_router)
app.include_router(value_bands_router)
app.include_router(metric_types_router)
app.include_router(background_grade_metrics_router)
app.include_router(project_dataset_exclusions_router)
app.include_router(benchmark_mastertypes_router)
app.include_router(benchmark_typecasts_router)
# Governance & Audit
app.include_router(audit_logs_router)
app.include_router(project_stage_instances_router)
app.include_router(project_stage_config_router)

# Vehicle Reference Data
app.include_router(vehicle_classes_router)
app.include_router(vehicle_masses_router)
app.include_router(interrupted_vehicles_router)
app.include_router(uninterrupted_vehicles_router)
app.include_router(vehicle_energy_conversion_rates_router)

#Electricity Decarbonisation Scenarios & Carbon Values
app.include_router(electric_decarb_factors_router)
app.include_router(carbon_values_router)


#**************** Calculations Router *******************
# Grade 1 & 2 Calculations, b4 replacement calculations, Detailed Level Electricity Calculations
app.include_router(grade1_calculations_router)
app.include_router(grade2_calculations_router)
app.include_router(grade2_b4_replacement_router)
app.include_router(electricity_detailed_calculations_router)
app.include_router(maintenance_replacement_component_level_calcs_router)
app.include_router(grade34_detailed_level_maintenance_calcs_router)
app.include_router(operational_component_level_calcs_router)
app.include_router(electricity_calculations_router)
app.include_router(grade34_detailed_level_construction_calcs_router)
app.include_router(inuse_gases_calculations_router)
app.include_router(detailed_level_maintenance_calculations_router)
app.include_router(detailed_level_maintenance_b2_b5_calculations_router)
app.include_router(detailed_level_fuel_water_router)
# app.include_router(detailed_level_operational_elec_router)
# User Emissions (B8) Calculations - NZ, AUS Small & Rail
app.include_router(user_emissions_nz_router)
app.include_router(user_emissions_aus_small_router)
app.include_router(user_emissions_rail_router)
app.include_router(user_emissions_aus_large_road_router)
app.include_router(concrete_mix_register_calculations_router)
app.include_router(user_emissions_nz_large_road_router)

# EV Uptake, VEPM & Freight Rail
app.include_router(ev_uptake_factors_router)
app.include_router(vepm_factors_router)
app.include_router(freight_rail_factors_router)
app.include_router(maintenance_replacement_factors_router)
app.include_router(fugitives_router)
app.include_router(default_wastage_rate_router)
app.include_router(renewable_energy_classification_router)
app.include_router(energy_density_conversions_router)
app.include_router(operational_equipment_router)

# User Guide
app.include_router(user_guide_router)
app.include_router(user_guide_videos_router)
app.include_router(terms_documents_router)

# Data Entry Storage Layer
app.include_router(activity_data_router)
app.include_router(project_mitigations_router)
app.include_router(construction_periods_router)
app.include_router(project_options_router)

# Concrete Register (grade 3/4)
app.include_router(concrete_register_router)

# Business-as-usual Assumptions — Default concrete mix designs
app.include_router(concrete_mix_design_router)
app.include_router(direct_substitutions_router)
app.include_router(electricity_recycling_assumptions_router)

# Recycled Content Factors
app.include_router(recycled_content_factors_router)

# Dashboard Results
app.include_router(org_dashboard_energy_router)
app.include_router(org_dashboard_hotspots_router)
app.include_router(org_dashboard_waste_router)
app.include_router(org_dashboard_materials_router)
app.include_router(org_dashboard_emissions_breakdown_router)
app.include_router(org_dashboard_user_emissions_router)
app.include_router(org_dashboard_carbon_valuation_router)
app.include_router(org_dashboard_carbon_storage_router)
app.include_router(org_dashboard_scope_breakdown_router)

app.include_router(dashboard_offsetting_router)
app.include_router(dashboard_waste_router)
app.include_router(dashboard_materials_router)
app.include_router(dashboard_energy_router)
app.include_router(dashboard_hotspots_router)
app.include_router(dashboard_comparison_router)
app.include_router(dashboard_user_emissions_router)
app.include_router(dashboard_emissions_breakdown_router)
app.include_router(completeness_emissions_breakdown_router)
app.include_router(dashboard_scope_breakdown_router)
app.include_router(dashboard_options_comparison_router)
app.include_router(dashboard_carbon_valuation_router)
app.include_router(dashboard_carbon_storage_router)
app.include_router(dashboard_mitigation_summary_router)
app.include_router(dashboard_itmm_reporting_router)
app.include_router(dashboard_ratings_router)

@app.get('/')
async def root():
    return {'app': settings.app_name, 'env': settings.app_env}