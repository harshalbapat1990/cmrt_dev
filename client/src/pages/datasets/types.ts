export type PageTab = 'factors' | 'recycled' | 'content_recycled' | 'transport' | 'waste' | 'audit' | 'decarb' | 'ev_uptake' | 'vepm' | 'freight_rail' | 'maintenance_replacement' | 'densities' | 'unit_conversions' | 'fugitives' | 'energy_density_conversions' | 'vehicle_masses' | 'interrupted_vehicles' | 'uninterrupted_vehicles' | 'vehicle_energy' | 'operational_equipment' | 'carbon_values' | 'wastage_rates' | 'concrete_mix_designs' | 'direct_substitutions' | 'electricity_recycling_assumptions' | 'renewable_energy';

export interface DatasetRevision {
  id: string;
  name: string;
  status: string;
  scope_type: 'DEFAULT' | 'ORG' | 'PROJECT';
  scope_id: string | null;
}

export type DatasetScope =
  | { type: 'DEFAULT' }
  | { type: 'ORG'; orgId: string }
  | { type: 'PROJECT'; projectId: string; orgId: string };
export interface RecycledContentRow {
  id: string; material_id: string | null; material_name: string | null;
  recycled_from_material_id: string | null;
  percent: string | null; jurisdiction_id: string | null; jurisdiction_name: string | null;
  effective_from: string | null; effective_to: string | null; notes: string | null;
}
export interface TransportRow {
  id: string; material_id: string | null; material_name: string | null;
  emissions_category_id: string | null; emissions_category_name: string | null;
  jurisdiction_id: string; jurisdiction_name: string | null;
  truck_distance: string | null; truck_transport_mode: string | null;
  rail_distance: string | null; rail_transport_mode: string | null;
  sea_distance: string | null; sea_transport_mode: string | null;
  source: string | null; grade_applicability: string | null;
  effective_from: string | null; effective_to: string | null;
}
export interface WasteRateRow {
  id: string; jurisdiction_id: string; material_id: string; waste_treatment_id: string;
  applicable_lifecycle_module_code: string | null; basis: string; rate: string;
  rate_unit_id: string | null;
  effective_from: string | null; effective_to: string | null; notes: string | null;
  material_name: string | null; waste_treatment_name: string | null; jurisdiction_name: string | null;
}
export interface AuditLogRow {
  id: string; entity_type: string; entity_id: string; action: string;
  field_name: string | null; old_value: string | null; new_value: string | null;
  performed_by: string | null; performed_at: string | null;
  event_metadata: Record<string, unknown> | null;
  performed_by_email: string | null;
  performed_by_org_name: string | null;
  entity_name: string | null;
}
export interface BgmRow {
  id: string;
  dataset_revision_id: string | null;
  grade_id: number;
  jurisdiction_id: string | null;
  jurisdiction_name: string | null;
  unit_id: string | null;
  metric_type_id: string | null;
  emissions_category_id: string | null;
  emissions_subcategory_id: string | null;
  mastertype_id: string | null;
  typecast_id: string | null;
  mastertype_name: string | null;
  typecast_name: string | null;
  emissions_category: string | null;
  emissions_subcategory: string | null;
  emissions_source: string | null;
  lifecycle_module_code: string | null;
  ghg_scope_id: number | null;
  metric_type_code: string | null;
  metric_type_name: string | null;
  band_code: string | null;
  unit_code: string | null;
  unit_label: string | null;
  value: string | null;
  assumed_quantity_default: string | null;
  source: string | null;
}

export interface G1Filter {
  mastertype_id: string;
  typecast_id: string;
  metrics: string[];
  units: string[];
  jurisdictions: string[];
}
export interface G234Filter {
  categories: string[];
  subcategories: string[];
  emissionsSource: string;
  units: string[];
  jurisdictions: string[];
}
export interface RcFilter { material: string; jurisdictions: string[]; percentMin: string; percentMax: string; }
export interface TrFilter { materialCategory: string; jurisdictions: string[]; transportMode: string; }
export interface DecarbFilter { jurisdictions: string[]; }
export interface DensityFilter {
  jurisdictions: string[];
  datasets: string[];
  categories: string[];
  subcategories: string[];
  emissionsSource: string;
  units: string[];
}
export interface DecarbEditCtx {
  editCellId: string | null;
  cellDraft: string;
  adding: boolean;
  addDraft: { jurisdictionId: string; regionId: string };
  jurOpts: NamedOption[];
  allRegions: Array<{ id: string; name: string; jurisdictionId: string }>;
  activeFtHasRegion: boolean;
  onEditCell: (rowId: string) => void;
  onCellChange: (val: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  onAddField: (f: 'jurisdictionId' | 'regionId', v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  saving: boolean;
  saveError: string;
}
export interface DecarbRow {
  id: string;
  dataset_revision_id: string;
  factor_type_code: string;
  factor_type_name: string | null;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  region_id: string | null;
  region_name: string | null;
  unit_id: string | null;
  unit: RelatedUnit | null;
  year: number;
  value: number | null;
  value_qualifier: string | null;
}

export interface EvUptakeRow {
  id: string;
  dataset_revision_id: string;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  scenario_code: string;
  scenario_name: string | null;
  vehicle_category_code: string;
  vehicle_category_name: string | null;
  energy_type_code: string;
  energy_type_name: string | null;
  year: number;
  uptake_pct: number | null;
}

export interface VepmRow {
  id: string;
  dataset_revision_id: string;
  year: number;
  speed_kmh: number;
  fleet_average_co2e_g_km: number | null;
  light_vehicle_co2e_g_km: number | null;
  heavy_vehicle_co2e_g_km: number | null;
  bus_co2e_g_km: number | null;
}

export interface FreightRailRow {
  id: string;
  dataset_revision_id: string;
  train_type: string;
  terrain: string;
  fuel_consumption_l_per_000_gtk: number | null;
  source_note: string | null;
}

export interface RelatedObject {
  id: string;
  name: string;
}

export interface RelatedUnit {
  id: string;
  code: string;
  label: string | null;
}

export interface DensityRow {
  id: string;
  dataset_revision_id: string | null;
  dataset_revision: RelatedObject | null;
  jurisdiction_id: string | null;
  jurisdiction: RelatedObject | null;
  dataset: 'component' | 'detailed';
  record_key: string;
  group: string | null;
  sub_group: string | null;
  item: string | null;
  item_description: string | null;
  emissions_category_id: string | null;
  emissions_category: RelatedObject | null;
  emissions_sub_category_id: string | null;
  emissions_sub_category: RelatedObject | null;
  emissions_source: string | null;
  density: string | null;
  unit_id: string;
  unit: RelatedUnit;
  source: string | null;
}

export interface UnitConversionRow {
  id: string;
  from_unit_id: string;
  from_unit: RelatedUnit;
  to_unit_id: string;
  to_unit: RelatedUnit;
  factor: string;
}

export interface UnitConversionEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface RelatedJurisdiction {
  id: string;
  name: string;
}

export interface FugitiveRow {
  id: string;
  dataset_revision_id: string | null;
  jurisdiction_id: string;
  jurisdiction: RelatedJurisdiction;
  equipment_type: string;
  default_annual_leakage_rate: number | null;
  source_comments: string | null;
}

export interface FugitiveEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface FugitiveFilter {
  jurisdictions: string[];
}

export interface EnergyDensityConversionRow {
  id: string;
  dataset_revision_id: string | null;
  category: string;
  name: string;
  unit_id: string;
  unit: RelatedUnit;
  energy_density: number | null;
  source_comments: string | null;
}

export interface EnergyDensityConversionEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface EvUptakeFilter {
  jurisdictions: string[];
  scenarioCodes: string[];
  vehicleCategoryCodes: string[];
  energyTypeCodes: string[];
}

export interface EvUptakeEditCtx {
  editCellId: string | null;
  cellDraft: string;
  adding: boolean;
  addDraft: { jurisdictionId: string; scenarioCode: string; vehicleCategoryCode: string; energyTypeCode: string };
  jurOpts: NamedOption[];
  scenarioOpts: NamedOption[];
  vehicleCategoryOpts: NamedOption[];
  energyTypeOpts: NamedOption[];
  onEditCell: (rowId: string) => void;
  onCellChange: (val: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  saving: boolean;
  saveError: string;
}

export interface VepmEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface FreightRailEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface MaintenanceReplacementRow {
  id: string;
  dataset_revision_id: string;
  jurisdiction_id: string | null;
  jurisdiction_name: string | null;
  activity_type: string;
  item: string;
  unit_id: string | null;
  unit: RelatedUnit | null;
  emissions_intensity_tco2e: number | null;
  default_frequency_years: number | null;
  source_note: string | null;
}

export interface MaintenanceReplacementEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface DensityEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (field: string, value: string) => void;
  onSaveEdit: () => Promise<void>;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface G1Row {
  mastertype: string; typecast: string;
  metric: string; unit: string; source: string; jurisdiction: string;
  low: number | null; mid: number | null; high: number | null;
  _low_id: string | null; _mid_id: string | null; _high_id: string | null;
  _unit_id: string | null; _metric_type_id: string | null; _metric_type_code: string | null;
  _dataset_revision_id: string | null; _grade_id: number;
  _mastertype_id: string | null; _typecast_id: string | null;
  _jurisdiction_id: string | null;
}
export interface G2Row {
  emissions_category: string; emissions_subcategory: string; emissions_source: string;
  quantity: number | null; unit: string; jurisdiction: string;
  carbon_storage: number | null; a1_a3: number | null; a4: number | null; a5: number | null;
  source: string;
  _cs_id: string | null; _a1a3_id: string | null; _a4_id: string | null; _a5_id: string | null;
  _unit_id: string | null; _cat_id: string | null; _subcat_id: string | null;
  _dataset_revision_id: string | null; _grade_id: number;
  _jurisdiction_id: string | null;
}
export interface G34Row {
  emissions_category: string; emissions_subcategory: string; emissions_source: string;
  unit: string; jurisdiction: string;
  carbon_storage: number | null; scope1: number | null; scope2: number | null; scope3: number | null;
  source: string;
  _cs_id: string | null; _s1_id: string | null; _s2_id: string | null; _s3_id: string | null;
  _unit_id: string | null; _cat_id: string | null; _subcat_id: string | null;
  _dataset_revision_id: string | null; _grade_id: number;
  _jurisdiction_id: string | null;
}

export interface NamedOption { id: string; name: string; }

export interface VehicleClassOption { id: string; name: string; }

export interface VehicleMassRow {
  id: string;
  vehicle_class_id: string;
  vehicle_class_name: string | null;
  reference_gcm_tonnes: string | null;
  max_payload_tonnes: string | null;
  gvm_tonnes: string | null;
  assumed_payload_pct: string | null;
}

export interface InterruptedVehicleRow {
  id: string;
  vehicle_class_id: string;
  vehicle_class_name: string | null;
  coefficient_a: string;
  coefficient_b: string;
}

export interface UninterruptedVehicleRow {
  id: string;
  vehicle_class_id: string;
  vehicle_class_name: string | null;
  gradient_m_per_km: string;
  curvature_deg_per_km: string;
  base_fuel_l_per_100km: string;
  k1: string;
  k2: string;
  k3: string;
  k4: string;
  k5: string;
}

export interface VehicleEnergyConversionRow {
  id: string;
  vehicle_class_id: string;
  vehicle_class_name: string | null;
  ev_projection_category: string;
  primary_ice_fuel: string;
  hybrid_fuel_savings_pct: string | null;
  phev_fuel_savings_pct: string | null;
  bev_energy_shift_kwh_per_l: string | null;
  fcev_hydrogen_consumption_kwh_per_l: string | null;
  source_comments: string | null;
}

export interface VehicleMassEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  vehicleClassOpts: VehicleClassOption[];
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onStartAdd: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface InterruptedVehicleEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  vehicleClassOpts: VehicleClassOption[];
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onStartAdd: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface UninterruptedVehicleEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  vehicleClassOpts: VehicleClassOption[];
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onStartAdd: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface VehicleEnergyEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  vehicleClassOpts: VehicleClassOption[];
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onStartAdd: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface InlineEditContext {
  matOpts: NamedOption[];
  jurOpts: NamedOption[];
  wtOpts: NamedOption[];
  ecOpts: NamedOption[];
  editingId: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface BgmEditCtx {
  unitOpts: NamedOption[];
  metricTypeOpts: NamedOption[];
  ecOpts: NamedOption[];
  jurOpts: NamedOption[];
  mastertypeOpts: NamedOption[];
  typecasts: NamedOption[];
  editKey: string | null;
  editDraft: Record<string, string>;
  adding: boolean;
  addDraft: Record<string, string>;
  onStartEdit: (key: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  saving: boolean;
  saveError: string;
}

export interface OperationalEquipmentRow {
  id: string;
  dataset_revision_id: string | null;
  group_name: string;
  item: string;
  power_kw: string;
  hours_per_day: string;
  days_per_year: string;
  annual_electricity_consumption_mwh: string;
  source: string | null;
  is_active: boolean;
}

export interface OperationalEquipmentEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (field: string, value: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface CarbonValueRow {
  id: string;
  dataset_revision_id: string;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  range_code: string;
  range_name: string | null;
  year: number;
  value: number | null;
  currency: string | null;
  source: string | null;
}

export interface CarbonValueFilter {
  jurisdictions: string[];
  rangeCodes: string[];
}

export interface CarbonValueEditCtx {
  editCellId: string | null;
  cellDraft: string;
  adding: boolean;
  addDraft: { jurisdictionId: string; rangeCode: string };
  jurOpts: NamedOption[];
  rangeOpts: NamedOption[];
  onEditCell: (rowId: string) => void;
  onCellChange: (val: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  onAddField: (f: 'jurisdictionId' | 'rangeCode', v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  saving: boolean;
  saveError: string;
}

export interface RelatedMaterial {
  id: string;
  name: string;
}

export interface WastageRateRow {
  id: string;
  dataset_revision_id: string | null;
  jurisdiction_id: string;
  jurisdiction: RelatedJurisdiction;
  material_id: string;
  material: RelatedMaterial;
  construction_wastage_rate: number | null;
  recycling_rate: number | null;
  landfill_rate: number | null;
  source: string | null;
}

export interface WastageRateFilter {
  jurisdictions: string[];
  materials: string[];
}

export interface WastageRateEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface ContentRecycledRow {
  id: string;
  jurisdiction_id: string | null;
  emissions_sub_category_id: string | null;
  emissions_source: string;
  recycled_content_pct: string | null;
  reused_content_pct: string | null;
  notes: string | null;
  jurisdiction_name?: string;
  category_name?: string;
}

export interface ContentRecycledFilter {
  jurisdictions: string[];
}

export type ContentRecycledEditableField = 'recycled_content_pct' | 'reused_content_pct' | 'notes';

export interface RenewableEnergyRow {
  id: string;
  dataset_revision_id: string | null;
  emissions_source: string;
  classification: string;
  notes: string | null;
  is_active: boolean;
}

export interface RenewableEnergyEditCtx {
  editingId: string | null;
  editDraft: Record<string, string>;
  onStartEdit: (id: string, draft: Record<string, string>) => void;
  onEditField: (f: string, v: string) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export interface ContentRecycledEditCtx {
  editCellKey: string | null;
  cellDraft: string;
  adding: boolean;
  addDraft: Record<string, string>;
  jurOpts: NamedOption[];
  catOpts: NamedOption[];
  onEditCell: (rowId: string, field: ContentRecycledEditableField, initial: string) => void;
  onCellChange: (value: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  onStartAdd: () => void;
  onAddField: (f: string, v: string) => void;
  onSaveAdd: () => void;
  onCancelAdd: () => void;
  onDelete?: (id: string) => void;
  saving: boolean;
  saveError: string;
}

export const CONCRETE_MIX_STRENGTHS = [20, 25, 32, 40, 50, 65, 80, 100] as const;
export type ConcreteMixStrength = typeof CONCRETE_MIX_STRENGTHS[number];

export type ConcreteMixStrengthField =
  | 'strength_20_kg_m3'
  | 'strength_25_kg_m3'
  | 'strength_32_kg_m3'
  | 'strength_40_kg_m3'
  | 'strength_50_kg_m3'
  | 'strength_65_kg_m3'
  | 'strength_80_kg_m3'
  | 'strength_100_kg_m3';

export interface ConcreteMixAssumption {
  id: string;
  dataset_revision_id: string | null;
  bau_scm_content_pct: string;
  default_max_fly_ash_pct: string;
  is_active: boolean;
}

export interface ConcreteMixDesignRow {
  id: string;
  dataset_revision_id: string | null;
  component_code: string;
  component_label: string;
  display_order: number;
  strength_20_kg_m3: string | number | null;
  strength_25_kg_m3: string | number | null;
  strength_32_kg_m3: string | number | null;
  strength_40_kg_m3: string | number | null;
  strength_50_kg_m3: string | number | null;
  strength_65_kg_m3: string | number | null;
  strength_80_kg_m3: string | number | null;
  strength_100_kg_m3: string | number | null;
  is_active: boolean;
}

export interface ConcreteMixBundle {
  assumptions: ConcreteMixAssumption;
  rows: ConcreteMixDesignRow[];
}

export interface DirectSubstitutionRow {
  id: string;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  user_emissions_source: string;
  user_unit: string;
  bau_equivalent_emission_source: string;
  bau_equivalent_unit: string;
  bau_quantity_per_user_unit: string | number;
  display_order: number;
}

export interface ElectricityRecyclingAssumptionRow {
  id: string;
  dataset_revision_id: string | null;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  metric_code: string;
  metric_label: string;
  default_bau_pct: string | number;
  is_calculated: boolean;
  display_order: number;
}

export interface ElectricityRecyclingEditCtx {
  editRowId: string | null;
  cellDraft: string;
  onEditCell: (rowId: string, current: string) => void;
  onCellChange: (v: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  saving: boolean;
  saveError: string;
}

export interface ConcreteMixEditCtx {
  editCellKey: string | null;
  cellDraft: string;
  onEditCell: (rowId: string, field: ConcreteMixStrengthField, current: string) => void;
  onCellChange: (v: string) => void;
  onSaveCell: () => void;
  onCancelCell: () => void;
  assumptionField: 'bau_scm_content_pct' | 'default_max_fly_ash_pct' | null;
  assumptionDraft: string;
  onEditAssumption: (
    field: 'bau_scm_content_pct' | 'default_max_fly_ash_pct',
    current: string,
  ) => void;
  onAssumptionChange: (v: string) => void;
  onSaveAssumption: () => void;
  onCancelAssumption: () => void;

  saving: boolean;
  saveError: string;
}
