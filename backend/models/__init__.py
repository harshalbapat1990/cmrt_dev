# backend/models/__init__.py

# Existing models (keep these)
from .project import Project
from .emissions_entries import EmissionEntry, EmissionEntrySummary
from .lookup_data import (
    EmissionSource,
    EmissionFactor,
    EmissionFactorValue,
)
from .project_reporting_submission import ProjectReportingSubmission
from .roles import Role
from .users import User

from .organizations import Organization
from .project_stage_config import ProjectStageConfig
from .project_organizations import ProjectOrganization
from .postcode import PostcodeReference, ProjectPostcode
from .project_type import ProjectType, ProjectTypecast

# New security/auth models
from .permissions import Permission
from .role_permissions import RolePermission
from .user_roles import UserRole

# Optional audit model (kept import-safe)
from .audit_logs import AuditLog

# Organization domains
from .organisation_domains import OrganizationDomain

# Joint ventures + parties
from .joint_ventures import JointVenture
from .joint_venture_members import JointVentureMember
from .project_parties import ProjectParty
from .project_stage_instances import ProjectStageInstance
from .project_stage_parties import ProjectStageParty

# Jurisdictions & Staging Model package
from .jurisdictions import Jurisdiction
from .anz_reporting_stages import AnzReportingStage
from .jurisdiction_reporting_stages import JurisdictionReportingStage
from .ghg_scopes import GhgScope
from .units import Unit
from .unit_conversions import UnitConversion
from .emissions_categories_new import EmissionsCategoryRecord
from .user_guides import UserGuide
from .user_guide_videos import UserGuideVideo
from .terms_documents import TermsDocument

# Defaults & Materials package
from .materials import Material
from .material_recycled_content import MaterialRecycledContent
from .densities import Density
from .waste_treatments import WasteTreatment
from .default_transport_distances import DefaultTransportDistance
from .default_waste_rates import DefaultWasteRate
from .base_case_assumptions import BaseCaseAssumption
from .proponent_assumption_overrides import ProponentAssumptionOverride

# Lifecycle module lookup
from .lifecycle_modules import LifecycleModule

# Dataset revisions & grade metrics (Package F & G)
from .grade_definitions import GradeDefinition
from .value_bands import ValueBand
from .metric_types import MetricType
from .dataset_revisions import DatasetRevision
from .background_grade_metrics import BackgroundGradeMetric
from .dataset_revision_changes import DatasetRevisionChange
from .project_dataset_revisions import ProjectDatasetRevision
from .project_dataset_exclusions import ProjectDatasetExclusion
from .benchmark_mastertypes import BenchmarkMastertype
from .benchmark_typecasts import BenchmarkTypecast

# Electricity Decarbonisation Scenarios
from .decarb_factor_types import DecarbFactorType
from .grid_regions import GridRegion
from .electric_decarb_factors import ElectricDecarbFactor

# EV Uptake, VEPM & Freight Rail
from .ev_scenario_types import EvScenarioType
from .ev_vehicle_categories import EvVehicleCategory
from .ev_energy_types import EvEnergyType
from .ev_uptake_factors import EvUptakeFactor
from .vepm_factors import VepmFactor
from .freight_rail_factors import FreightRailFactor
from .maintenance_replacement_factors import MaintenanceReplacementFactor
from .fugitives import Fugitive
from .energy_density_conversions import EnergyDensityConversion
from .operational_equipment import OperationalEquipment

# Project Reporting Boundary
from .project_reporting_boundary import ProjectReportingBoundary

# Activity Data & Emissions Results (data entry storage layer)
from .project_options import ProjectOption
from .project_mitigations import ProjectMitigation
from .activity_data import ActivityData
from .emissions_results import EmissionsResult
# Concrete Register production factors (reference data only)

# Business-as-usual Assumptions — Default concrete mix designs
from .concrete_mix_design import ConcreteMixAssumption, ConcreteMixDesign
from .electricity_recycling_assumption import ElectricityRecyclingAssumption

from .direct_substitution_factors import DirectSubstitutionFactor