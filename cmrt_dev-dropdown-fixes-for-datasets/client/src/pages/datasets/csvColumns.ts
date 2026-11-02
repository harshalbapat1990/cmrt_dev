import type { CsvColumn } from '@/utils/downloadCsv';

// Recycled Content
export const RECYCLED_CONTENT_COLS: CsvColumn[] = [
  { key: 'id',              label: 'id' },
  { key: 'material_name',   label: 'Material' },
  { key: 'percent',         label: 'Percent (0-1)',   format: (v) => v != null ? String(v) : '' },
  { key: 'jurisdiction_name', label: 'Jurisdiction' },
  { key: 'effective_from',  label: 'Effective From' },
  { key: 'effective_to',    label: 'Effective To' },
  { key: 'notes',           label: 'Notes' },
];

// Default Transport Distances
export const TRANSPORT_COLS: CsvColumn[] = [
  { key: 'id',                      label: 'id' },
  { key: 'material_name',           label: 'Material' },
  { key: 'emissions_category_name', label: 'Emissions Category' },
  { key: 'jurisdiction_name',       label: 'Jurisdiction' },
  { key: 'truck_distance',          label: 'Truck Distance' },
  { key: 'truck_transport_mode',    label: 'Truck Mode' },
  { key: 'rail_distance',           label: 'Rail Distance' },
  { key: 'rail_transport_mode',     label: 'Rail Mode' },
  { key: 'sea_distance',            label: 'Sea Distance' },
  { key: 'sea_transport_mode',      label: 'Sea Mode' },
  { key: 'source',                  label: 'Source' },
  { key: 'effective_from',          label: 'Effective From' },
  { key: 'effective_to',            label: 'Effective To' },
];

// Waste Rates
export const WASTE_COLS: CsvColumn[] = [
  { key: 'id',               label: 'id' },
  { key: 'material_name',    label: 'Material' },
  { key: 'waste_treatment_name', label: 'Waste Treatment' },
  { key: 'jurisdiction_name', label: 'Jurisdiction' },
  { key: 'basis',            label: 'Basis' },
  { key: 'rate',             label: 'Rate' },
  { key: 'effective_from',   label: 'Effective From' },
  { key: 'effective_to',     label: 'Effective To' },
  { key: 'notes',            label: 'Notes' },
];

// Electricity (flat rows — not pivoted)
export const DECARB_COLS: CsvColumn[] = [
  { key: 'id',               label: 'id' },
  { key: 'factor_type_code', label: 'Factor Type' },
  { key: 'jurisdiction_name', label: 'Jurisdiction' },
  { key: 'region_name',      label: 'Region' },
  { key: 'year',             label: 'Year' },
  { key: 'value',            label: 'Value' },
  { key: 'value_qualifier',  label: 'Qualifier (D=disclosed)' },
  { key: 'unit',             label: 'Unit' },
];

// EV Uptake (flat rows)
export const EV_UPTAKE_COLS: CsvColumn[] = [
  { key: 'id',                    label: 'id' },
  { key: 'jurisdiction_name',     label: 'Jurisdiction' },
  { key: 'scenario_name',         label: 'Scenario' },
  { key: 'vehicle_category_name', label: 'Vehicle Category' },
  { key: 'energy_type_name',      label: 'Energy Type' },
  { key: 'year',                  label: 'Year' },
  { key: 'uptake_pct',            label: 'Uptake % (0-1)' },
];

// VEPM
export const VEPM_COLS: CsvColumn[] = [
  { key: 'id',                          label: 'id' },
  { key: 'year',                         label: 'Year' },
  { key: 'speed_kmh',                    label: 'Speed (km/h)' },
  { key: 'fleet_average_co2e_g_km',      label: 'Fleet Avg CO2e (g/km)' },
  { key: 'light_vehicle_co2e_g_km',      label: 'Light Vehicle (g/km)' },
  { key: 'heavy_vehicle_co2e_g_km',      label: 'Heavy Vehicle (g/km)' },
  { key: 'bus_co2e_g_km',               label: 'Bus (g/km)' },
];

// Freight Rail
export const FREIGHT_RAIL_COLS: CsvColumn[] = [
  { key: 'id',                             label: 'id' },
  { key: 'train_type',                     label: 'Train Type' },
  { key: 'terrain',                        label: 'Terrain' },
  { key: 'fuel_consumption_l_per_000_gtk', label: 'Fuel Consumption (L/000 GTK)' },
  { key: 'source_note',                    label: 'Source Note' },
];

// Maintenance & Replacement
export const MAINTENANCE_REPLACEMENT_COLS: CsvColumn[] = [
  { key: 'id',                       label: 'id' },
  { key: 'jurisdiction_name',        label: 'Jurisdiction' },
  { key: 'activity_type',            label: 'Activity Type' },
  { key: 'item',                     label: 'Item' },
  { key: 'unit_code',                label: 'Unit' },
  { key: 'emissions_intensity_tco2e', label: 'Emissions Intensity (tCO2e/UoM)' },
  { key: 'default_frequency_years',  label: 'Default Frequency (years)' },
  { key: 'source_note',              label: 'Source / Comments' },
];

// Operational Equipment
export const OPERATIONAL_EQUIPMENT_COLS: CsvColumn[] = [
  { key: 'id',                                   label: 'id' },
  { key: 'group_name',                           label: 'Group' },
  { key: 'item',                                 label: 'Item' },
  { key: 'power_kw',                             label: 'Power (kW)' },
  { key: 'hours_per_day',                        label: 'Hours/Day' },
  { key: 'days_per_year',                        label: 'Days/Year' },
  { key: 'annual_electricity_consumption_mwh',   label: 'Annual Electricity (MWh)' },
  { key: 'source',                               label: 'Source' },
];

// Densities
export const DENSITIES_COLS: CsvColumn[] = [
  { key: 'id',                    label: 'id' },
  { key: 'emissions_category',    label: 'Category',        format: (_, row) => row.emissions_category?.name ?? '' },
  { key: 'emissions_sub_category', label: 'Sub-Category',  format: (_, row) => row.emissions_sub_category?.name ?? '' },
  { key: 'emissions_source',      label: 'Emissions Source' },
  { key: 'unit',                  label: 'Unit',            format: (_, row) => row.unit?.code ?? '' },
  { key: 'density',               label: 'Density' },
  { key: 'source',                label: 'Source Note' },
];

// Unit Conversions
export const UNIT_CONVERSIONS_COLS: CsvColumn[] = [
  { key: 'id',         label: 'id' },
  { key: 'from_unit',  label: 'From Unit', format: (_, row) => row.from_unit?.code ?? '' },
  { key: 'to_unit',    label: 'To Unit',   format: (_, row) => row.to_unit?.code ?? '' },
  { key: 'factor',     label: 'Factor' },
];

// Fugitives
export const FUGITIVES_COLS: CsvColumn[] = [
  { key: 'id',                          label: 'id' },
  { key: 'jurisdiction_name',           label: 'Jurisdiction', format: (_, row) => row.jurisdiction?.name ?? '' },
  { key: 'equipment_type',              label: 'Equipment Type' },
  { key: 'default_annual_leakage_rate', label: 'Leakage Rate (%)' },
  { key: 'source_comments',             label: 'Source/Comments' },
];

// Energy Density Conversions
export const ENERGY_DENSITY_COLS: CsvColumn[] = [
  { key: 'id',               label: 'id' },
  { key: 'category',         label: 'Category' },
  { key: 'name',             label: 'Name' },
  { key: 'unit',             label: 'Unit', format: (_, row) => row.unit?.code ?? '' },
  { key: 'energy_density',   label: 'Energy Density' },
  { key: 'source_comments',  label: 'Source/Comments' },
];

// Vehicle Masses
export const VEHICLE_MASSES_COLS: CsvColumn[] = [
  { key: 'id',                    label: 'id' },
  { key: 'vehicle_class_name',    label: 'Vehicle Class' },
  { key: 'reference_gcm_tonnes',  label: 'Reference GCM (t)' },
  { key: 'max_payload_tonnes',    label: 'Max Payload (t)' },
  { key: 'gvm_tonnes',            label: 'GVM (t)' },
  { key: 'assumed_payload_pct',   label: 'Assumed Payload %' },
];

// Fuel use variables - stop-start
export const INTERRUPTED_VEHICLES_COLS: CsvColumn[] = [
  { key: 'id',                 label: 'id' },
  { key: 'vehicle_class_name', label: 'Vehicle Class' },
  { key: 'coefficient_a',      label: 'Coefficient A' },
  { key: 'coefficient_b',      label: 'Coefficient B' },
];

// Fuel use variables - free flow
export const UNINTERRUPTED_VEHICLES_COLS: CsvColumn[] = [
  { key: 'id',                   label: 'id' },
  { key: 'vehicle_class_name',   label: 'Vehicle Class' },
  { key: 'gradient_m_per_km',    label: 'Gradient (m/km)' },
  { key: 'curvature_deg_per_km', label: 'Curvature (deg/km)' },
  { key: 'base_fuel_l_per_100km', label: 'Base Fuel (L/100km)' },
  { key: 'k1', label: 'k1' },
  { key: 'k2', label: 'k2' },
  { key: 'k3', label: 'k3' },
  { key: 'k4', label: 'k4' },
  { key: 'k5', label: 'k5' },
];

// Vehicle Energy Conversions
export const VEHICLE_ENERGY_COLS: CsvColumn[] = [
  { key: 'id',                            label: 'id' },
  { key: 'vehicle_class_name',            label: 'Vehicle Class' },
  { key: 'ev_projection_category',        label: 'EV Projection Category' },
  { key: 'primary_ice_fuel',              label: 'Primary ICE Fuel' },
  { key: 'hybrid_fuel_savings_pct',       label: 'Hybrid Fuel Savings %' },
  { key: 'phev_fuel_savings_pct',         label: 'PHEV Fuel Savings %' },
  { key: 'bev_energy_shift_kwh_per_l',    label: 'BEV Energy Shift (kWh/L)' },
  { key: 'fcev_hydrogen_consumption_kwh_per_l', label: 'FCEV Hydrogen (kWh/L)' },
  { key: 'source_comments',              label: 'Source/Comments' },
];

// Carbon Values (flat rows)
export const CARBON_VALUES_COLS: CsvColumn[] = [
  { key: 'id',               label: 'id' },
  { key: 'jurisdiction_name', label: 'Jurisdiction' },
  { key: 'range_name',       label: 'Range' },
  { key: 'year',             label: 'Year' },
  { key: 'value',            label: 'Value' },
  { key: 'currency',         label: 'Currency' },
  { key: 'source',           label: 'Source' },
];

// Content Recycled (recycled_content_factors) — aligned with contentRecycled.xlsx
export const CONTENT_RECYCLED_COLS: CsvColumn[] = [
  {
    key: 'jurisdiction_name',
    label: 'Jurisdiction Name',
    format: (_, row) => String(row.jurisdiction_name ?? ''),
  },
  {
    key: 'category_name',
    label: 'Emissions Sub-Category',
    format: (_, row) => String(row.category_name ?? ''),
  },
  { key: 'emissions_source', label: 'Emissions Source' },
  {
    key: 'recycled_content_pct',
    label: 'Recycled Content (%)',
    format: (v) => (v != null && v !== '' ? String(parseFloat(String(v)) * 100) : ''),
  },
  {
    key: 'reused_content_pct',
    label: 'Reused Content %',
    format: (v) => (v != null && v !== '' ? String(parseFloat(String(v)) * 100) : ''),
  },
  { key: 'notes', label: 'Source/Comments' },
];

// Wastage Rates
export const WASTAGE_RATES_COLS: CsvColumn[] = [
  { key: 'id',                       label: 'id' },
  { key: 'jurisdiction',             label: 'Jurisdiction', format: (_, row) => row.jurisdiction?.name ?? '' },
  { key: 'material',                 label: 'Material',     format: (_, row) => row.material?.name ?? '' },
  { key: 'construction_wastage_rate', label: 'Construction Wastage Rate' },
  { key: 'recycling_rate',           label: 'Recycling Rate' },
  { key: 'landfill_rate',            label: 'Landfill Rate' },
  { key: 'source',                   label: 'Source' },
];

// Renewable Energy Classifications
export const RENEWABLE_ENERGY_COLS: CsvColumn[] = [
  { key: 'id',               label: 'id' },
  { key: 'emissions_source', label: 'Emissions Source' },
  { key: 'classification',   label: 'Classification' },
  { key: 'notes',            label: 'Notes' },
];

// Grade 1 flat export
export const GRADE1_COLS: CsvColumn[] = [
  { key: 'jurisdiction',  label: 'Jurisdiction' },
  { key: 'mastertype',    label: 'Mastertype' },
  { key: 'typecast',      label: 'Typecast' },
  { key: 'metric',        label: 'Metric' },
  { key: 'unit',          label: 'Unit' },
  { key: 'low',           label: 'Low' },
  { key: 'mid',           label: 'Mid' },
  { key: 'high',          label: 'High' },
  { key: 'source',        label: 'Source' },
  { key: '_low_id',       label: 'low_id' },
  { key: '_mid_id',       label: 'mid_id' },
  { key: '_high_id',      label: 'high_id' },
];

// Grade 2
export const GRADE2_COLS: CsvColumn[] = [
  { key: 'jurisdiction',       label: 'Jurisdiction' },
  { key: 'emissions_category', label: 'Category' },
  { key: 'emissions_subcategory', label: 'Subcategory' },
  { key: 'emissions_source',   label: 'Emissions Source' },
  { key: 'unit',               label: 'Unit' },
  { key: 'carbon_storage',     label: 'Carbon Storage' },
  { key: 'a1_a3',              label: 'A1-A3' },
  { key: 'a4',                 label: 'A4' },
  { key: 'a5',                 label: 'A5' },
  { key: 'source',             label: 'Source' },
  { key: '_cs_id',             label: 'cs_id' },
  { key: '_a1a3_id',           label: 'a1a3_id' },
  { key: '_a4_id',             label: 'a4_id' },
  { key: '_a5_id',             label: 'a5_id' },
];

// Grade 3/4
export const GRADE34_COLS: CsvColumn[] = [
  { key: 'jurisdiction',       label: 'Jurisdiction' },
  { key: 'emissions_category', label: 'Category' },
  { key: 'emissions_subcategory', label: 'Subcategory' },
  { key: 'emissions_source',   label: 'Emissions Source' },
  { key: 'unit',               label: 'Unit' },
  { key: 'carbon_storage',     label: 'Carbon Storage' },
  { key: 'scope1',             label: 'Scope 1' },
  { key: 'scope2',             label: 'Scope 2' },
  { key: 'scope3',             label: 'Scope 3' },
  { key: 'source',             label: 'Source' },
  { key: '_cs_id',             label: 'cs_id' },
  { key: '_s1_id',             label: 's1_id' },
  { key: '_s2_id',             label: 's2_id' },
  { key: '_s3_id',             label: 's3_id' },
];

// Default concrete mix designs (Business-as-usual Assumptions)
export const CONCRETE_MIX_DESIGN_COLS: CsvColumn[] = [
  { key: 'component_label',     label: 'Component' },
  { key: 'strength_20_kg_m3',   label: '20 MPa (kg/m3)' },
  { key: 'strength_25_kg_m3',   label: '25 MPa (kg/m3)' },
  { key: 'strength_32_kg_m3',   label: '32 MPa (kg/m3)' },
  { key: 'strength_40_kg_m3',   label: '40 MPa (kg/m3)' },
  { key: 'strength_50_kg_m3',   label: '50 MPa (kg/m3)' },
  { key: 'strength_65_kg_m3',   label: '65 MPa (kg/m3)' },
  { key: 'strength_80_kg_m3',   label: '80 MPa (kg/m3)' },
  { key: 'strength_100_kg_m3',  label: '100 MPa (kg/m3)' },
];

export const DIRECT_SUBSTITUTION_COLS: CsvColumn[] = [
  { key: 'jurisdiction_name', label: 'jurisdiction_name', format: (_, row) => String(row.jurisdiction_name ?? '') },
  { key: 'user_emissions_source', label: 'user_emissions_source' },
  { key: 'user_unit', label: 'user_unit' },
  { key: 'bau_equivalent_emission_source', label: 'bau_equivalent_emission_source' },
  { key: 'bau_equivalent_unit', label: 'bau_equivalent_unit' },
  { key: 'bau_quantity_per_user_unit', label: 'bau_quantity_per_user_unit', format: (v) => (v != null && v !== '' ? String(v) : '') },
];

export const ELECTRICITY_RECYCLING_ASSUMPTION_COLS: CsvColumn[] = [
  {
    key: 'jurisdiction_name',
    label: 'Jurisdiction Name',
    format: (_, row) => String(row.jurisdiction_name ?? ''),
  },
  {
    key: 'metric_label',
    label: 'Metric',
    format: (_, row) => String(row.metric_label ?? ''),
  },
  {
    key: 'default_bau_pct',
    label: 'Default BAU(%)',
    format: (v) => formatEraBauPctNumber(v),
  },
];

const ERA_CALCULATED_METRICS = new Set([
  'grid electricity (construction)',
  'grid electricity (operation)',
]);

export function formatEraBauPctNumber(v: unknown): string {
  if (v == null || v === '') return '';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (!Number.isFinite(n)) return '';
  const pct = n <= 1 && n >= 0 ? n * 100 : n;
  if (Number.isInteger(pct)) return String(pct);
  return String(Number(pct.toFixed(4).replace(/\.?0+$/, '')));
}

export function parseEraUploadRow(r: Record<string, string>) {
  return {
    jurisdiction: String(r['Jurisdiction Name'] ?? r.jurisdiction_name ?? r.jurisdiction ?? '').trim(),
    metric: String(r['Metric'] ?? r.metric_label ?? r.metric ?? r.metric_code ?? '').trim(),
    pctRaw: String(r['Default BAU(%)'] ?? r.default_bau_pct ?? '').trim(),
  };
}

export function isEraCalculatedMetric(metric: string): boolean {
  return ERA_CALCULATED_METRICS.has(metric.trim().toLowerCase());
}

export function eraRowsForCsvExport(rows: Array<{ is_calculated?: boolean }>) {
  return rows.filter(r => !r.is_calculated);
}

export function parseContentRecycledUploadRow(r: Record<string, string>) {
  return {
    jurisdiction: String(
      r['Jurisdiction Name'] ?? r['Jurisdiction'] ?? r.jurisdiction ?? r.jurisdiction_name ?? '',
    ).trim(),
    category: String(
      r['Emissions Sub-Category'] ?? r['Category'] ?? r.category_name ?? r.emissions_sub_category ?? '',
    ).trim(),
    source: String(
      r['Emissions Source'] ?? r.emissions_source ?? '',
    ).trim(),
    recycledRaw: String(
      r['Recycled Content (%)'] ?? r.recycled_content_pct ?? '',
    ).trim(),
    reusedRaw: String(
      r['Reused Content %'] ?? r['Reused Content (%)'] ?? r.reused_content_pct ?? '',
    ).trim(),
    notes: String(
      r['Source/Comments'] ?? r.notes ?? '',
    ).trim(),
  };
}

export function parseContentRecycledPctUpload(raw: string): number | null | undefined {
  const cleaned = raw.trim().replace(/%$/, '');
  if (!cleaned) return null;
  const n = parseFloat(cleaned);
  if (!Number.isFinite(n)) return undefined;
  if (n > 1) return n / 100;
  return n;
}