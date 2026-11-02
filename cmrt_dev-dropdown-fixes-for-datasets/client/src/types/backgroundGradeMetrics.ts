export interface BackgroundGradeMetric {
  id: string;
  dataset_revision_id: string | null;
  grade_id: number;
  jurisdiction_id: string | null;
  super_sector: string | null;
  mastertype: string | null;
  typecast_name: string | null;
  emissions_category_id: string | null;
  emissions_subcategory_id: string | null;
  emissions_source: string | null;
  lifecycle_module_code: string | null;
  ghg_scope_id: number | null;
  metric_type_id: string;
  band_code: string | null;
  unit_id: string | null;
  value: number | null;
  assumed_quantity_default: number | null;
  source: string | null;
  created_at: string;
  // Joined human-readable fields
  grade_name: string | null;
  jurisdiction_name: string | null;
  emissions_category: string | null;
  emissions_subcategory: string | null;
  lifecycle_module_name: string | null;
  ghg_scope_name: string | null;
  metric_type_code: string | null;
  metric_type_name: string | null;
  unit_code: string | null;
}

export interface BackgroundGradeMetricFilters {
  dataset_revision_id?: string | null;
  grade_id?: number;
  jurisdiction_name?: string;
  super_sector?: string;
  mastertype?: string;
  typecast_name?: string;
  emissions_category?: string;
  emissions_subcategory?: string;
  lifecycle_module_code?: string;
  skip?: number;
  limit?: number;
}
