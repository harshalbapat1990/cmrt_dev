import http from "@/http";
import LookupsService from "@/services/Lookups.service";
import type { DataEntryRow } from "./dataEntryTypes";
import { isGrade34DetailedTable, type UploadKey } from "./stageConstants";

export type MetricLookupDraft = Pick<
  DataEntryRow,
  | "mastertype_id"
  | "typecast_id"
  | "band_code"
  | "emissions_category_id"
  | "emissions_subcategory_id"
  | "emission_subcategory_id"
>;

const CATEGORY_SUBCATEGORY_TABLES: readonly UploadKey[] = [
  "constructionG2",
  "useB1G2",
  "useB1G3",
  "opEnergyDetailed",
  "replDetailed",
];

/** Builds the existing background-metric query for one supported activity table. */
export function buildMetricLookupParams(
  draft: MetricLookupDraft,
  tableKey: UploadKey,
  datasetRevisionId?: string | null,
): URLSearchParams | null {
  // These rows are calculated by the Grade 3/4 detailed-level service, whose
  // lookup includes source and unit. Category/sub-category alone is ambiguous.
  if (isGrade34DetailedTable(tableKey)) return null;
  const params = new URLSearchParams({ limit: "1" });
  if (datasetRevisionId) params.set("dataset_revision_id", datasetRevisionId);
  if (tableKey === "asset") {
    if (draft.mastertype_id) params.set("mastertype_id", draft.mastertype_id);
    if (draft.typecast_id) params.set("typecast_id", draft.typecast_id);
    if (draft.band_code) params.set("band_code", draft.band_code);
    return params;
  }

  if (tableKey === "component" || tableKey === "componentRepl") {
    if (draft.emissions_category_id) params.set("emissions_category_id", draft.emissions_category_id);
    if (draft.emissions_subcategory_id) params.set("emissions_subcategory_id", draft.emissions_subcategory_id);
    return params;
  }

  if (CATEGORY_SUBCATEGORY_TABLES.includes(tableKey)) {
    if (draft.emissions_category_id) params.set("emissions_category_id", draft.emissions_category_id);
    const subcategoryId = draft.emissions_subcategory_id ?? draft.emission_subcategory_id;
    if (subcategoryId) params.set("emissions_subcategory_id", subcategoryId);
    return params;
  }

  return null;
}

export async function resolveMetricId(
  draft: MetricLookupDraft,
  tableKey: UploadKey,
  projectId: string,
): Promise<string | null> {
  const params = buildMetricLookupParams(draft, tableKey);
  if (!params || !projectId) return null;
  try {
    const datasetRevisionId = await LookupsService.resolveProjectDatasetRevisionId(projectId);
    if (!datasetRevisionId) return null;
    const revisionScopedParams = buildMetricLookupParams(draft, tableKey, datasetRevisionId);
    if (!revisionScopedParams) return null;
    const response = await http.get(`/api/background-grade-metrics?${revisionScopedParams.toString()}`);
    const metrics: unknown = response.data;
    return Array.isArray(metrics) && typeof metrics[0]?.id === "string" ? metrics[0].id : null;
  } catch {
    return null;
  }
}
