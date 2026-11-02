import type { StageAccessLevel } from "@/types/authorization";
import type { UploadKey } from "./stageConstants";

export type ProjectClass = "SMALL" | "LARGE" | "RECURRING";
export type StageLabel = "Business case" | "Design" | "Construction" | "Recurring";
export type StageCode = "BUSINESS_CASE" | "DESIGN" | "CONSTRUCTION" | "RECURRING";

export interface StageInstance {
  id: string;
  stage: StageCode;
  sequence?: number | null;
  num_reports_required?: number | null;
  approval_status?: string | null;
  frequency?: string | null;
}

export interface StageConfig {
  stage: StageCode;
  frequency?: string | null;
}

export interface ProjectPostcode {
  created_on?: string | null;
  jurisdiction_name?: string | null;
  grid_region?: string | null;
}

export interface ProjectDetails {
  id?: string;
  name?: string | null;
  project_name?: string | null;
  program_name?: string | null;
  project_class?: ProjectClass | null;
  project_type_name?: string | null;
  stage_configs?: StageConfig[];
  stage_instances?: StageInstance[];
  first_submission_month?: string | null;
  is_active?: boolean | null;
  operational_life_years?: number | null;
  commencement_of_operations?: string | null;
  construction_start_date?: string | null;
  construction_end_date?: string | null;
  postcodes?: ProjectPostcode[];
}

export interface ActivityExtraFields {
  reporting_boundary_id?: string | null;
  stage_or_activity?: string | null;
  [key: string]: unknown;
}

export interface ReportingBoundary {
  id: string;
  stage_or_activity: string;
  category: string;
  sub_category: string;
  source?: string | null;
}

export interface FugitiveOption {
  id: string;
  name?: string | null;
  gas?: string | null;
  equipment_type?: string | null;
  default_annual_leakage_rate?: string | number | null;
  [key: string]: unknown;
}

export interface LookupChoice {
  id?: string | null;
  value?: string | null;
  name?: string | null;
  label?: string | null;
}

export interface JurisdictionContext {
  jurisdiction: "Australia" | "New Zealand";
  region: string;
}

export interface DataEntryRow {
  id?: string | number;
  mastertype_id?: string | null;
  typecast_id?: string | null;
  band_code?: string | null;
  emissions_category_id?: string | null;
  emissions_subcategory_id?: string | null;
  emission_subcategory_id?: string | null;
  metric_id?: string | null;
  dataset_revision_id?: string | null;
  quantity?: number | string | null;
  unit_id?: string | null;
  emissions_tco2e?: number | string | null;
  total_emissions_tco2e?: number | string | null;
  location_based_tco2e?: number | string | null;
  market_based_tco2e?: number | string | null;
  extra_fields?: ActivityExtraFields;
  reporting_boundary_id?: string | null;
  stage_or_activity?: string | null;
  _fromApi?: boolean;
  _fromBoundary?: boolean;
  [key: string]: unknown;
}

export type DataEntryRowId = string | number;

export interface DataEntryCellChange {
  id: DataEntryRowId;
  key: string;
  value: unknown;
  item: DataEntryRow;
}

export interface DataEntryRowPatch {
  id: DataEntryRowId;
  patch: Partial<DataEntryRow>;
  item: DataEntryRow;
}

export type TableRowMap = Record<UploadKey, DataEntryRow[]>;

export interface StageViewState {
  activeStage: StageLabel;
  activeSubStage: string;
  activeReportNumber: number;
  stageAccess: StageAccessLevel;
}

export function normalizeProjectClass(value: unknown): ProjectClass | null {
  return value === "SMALL" || value === "LARGE" || value === "RECURRING"
    ? value
    : null;
}
