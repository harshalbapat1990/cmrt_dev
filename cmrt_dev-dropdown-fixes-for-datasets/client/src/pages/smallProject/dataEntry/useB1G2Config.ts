import http from "@/http";
import  EmissionCalculationsService from "@/services/EmissionCalculations.service";
import LookupsService from "@/services/Lookups.service";
import type { DataEntryRow } from "./dataEntryTypes";

type LookupOption = { label: string; value: string };
type FugitiveRecord = {
  id: string;
  equipment_type: string;
  default_annual_leakage_rate?: string | number | null;
  jurisdiction?: { name?: string | null } | null;
};

const asRecord = (value: unknown): Record<string, unknown> =>
  typeof value === "object" && value !== null ? value as Record<string, unknown> : {};

const mapToOptions = (list: unknown[], labelField = "name", valueField = "id"): LookupOption[] =>
  list.map((value) => {
    const record = asRecord(value);
    return { label: String(record[labelField] ?? ""), value: String(record[valueField] ?? "") };
  });

const pickLabel = (v: unknown): string => {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  const record = asRecord(v);
  return pickLabel(record.label ?? record.name ?? record.value);
};


export const requireGasesCategoryId = async (): Promise<string> => {
  const response: unknown = await LookupsService.fetchCategories(true);
  const categories = Array.isArray(response) ? response.map(asRecord) : [];
  const gasesCategory = categories.find((category) =>
    category.is_active !== false &&
    typeof category.name === "string" &&
    category.name.trim().toLowerCase() === "gases" &&
    category.parent_category_id == null,
  );
  if (!gasesCategory?.id) {
    throw new Error('The active "Gases" emissions category could not be found.');
  }
  return String(gasesCategory.id);
};

const fetchProjectFugitives = async (projectId?: string): Promise<FugitiveRecord[]> => {
  if (!projectId) return [];
  const datasetRevisionId = await LookupsService.resolveProjectDatasetRevisionId(projectId);
  if (!datasetRevisionId) return [];

  const res = await http.get("/api/fugitives", {
    params: { limit: 500, dataset_revision_id: datasetRevisionId, global_only: false },
  });
  if (!Array.isArray(res.data)) return [];
  return res.data.map(asRecord).flatMap((record) => {
    if (typeof record.id !== "string" && typeof record.id !== "number") return [];
    if (typeof record.equipment_type !== "string") return [];
    const jurisdiction = asRecord(record.jurisdiction);
    const rate = record.default_annual_leakage_rate;
    return [{
      id: String(record.id),
      equipment_type: record.equipment_type,
      default_annual_leakage_rate: typeof rate === "string" || typeof rate === "number" ? rate : null,
      jurisdiction: typeof jurisdiction.name === "string" ? { name: jurisdiction.name } : null,
    }];
  });
};

export const createB1G2Config = (jurisdictionName: string | null, projectId?: string, ) => ({
  tableName: "Component Level (Grade 2)",
  calculation: {
      grade: 2,
      // compute only when these exist
      requiredKeys: [
        "application_type",
        "charge_kg",
        "gas",
        "gas_type",
      ],
      // if any of these change → recalc
      triggerKeys: [
        "application_type",
        "application_type_id",
        "charge_kg",
        "gas",
        "emissions_source",
        "gas_type",
        "emissions_subcategory_id",
      ],
      buildPayload: (row: DataEntryRow, ctx: { jurisdiction: string; ops_start_year: number; reference_period: number }) => {
        const application_type = pickLabel(row.application_type);
        const charge_kg = pickLabel(row.charge_kg);
        const gas = pickLabel(row.gas);
        const gas_type = pickLabel(row.gas_type);
        
  const ops_start = ctx.ops_start_year;
  const ops_end = ops_start + ctx.reference_period;
  
        if (!application_type || !charge_kg || !gas || !gas_type ) {
          return null;
        }
  
        return {
          application_type,
          charge_kg,
          gas,
          gas_type,
          jurisdiction: ctx.jurisdiction,
          ops_start,
          ops_end,
          project_id: projectId,
        };
      },
      
  // table-specific API call
      calculate: async (payload: Record<string, unknown>) => {
        // For component table, use grade2 endpoint OR your table endpoint
        return EmissionCalculationsService.calculateB1G2Calculations(payload);
      },
  
      // map API response -> row changes
      mapResultToRow: (apiRes: unknown) => {
        const result = asRecord(apiRes);
        return {
          emissions_tco2e: result.total_emissions_tco2e ?? "-",
          annual_leakage_rate_percent: result.annual_leakage_rate_percent ?? "-",
          _ops_start: result.ops_start ?? null,
          _ops_end: result.ops_end ?? null,
        };
      },
  
    },

  fileHeaders: [
    { key: "application_type", label: "Application Type" },
    { key: "gas_type", label: "Gas Type" },
    { key: "gas", label: "Gas" },
    { key: "charge_kg", label: "Charge (kg)" },
    { key: "notes", label: "Notes/Comments (optional)" },
  ],

  rules: [
    {
      label: "application_type",
      keySource: "application_type",
      key: "application_type_id",
      required: true,
      lookup: {
        fetch: async () => {
          const list = await fetchProjectFugitives(projectId);
          const filtered = jurisdictionName
            ? list.filter((item) => item.jurisdiction?.name === jurisdictionName)
            : list;
          return filtered.map((item) => ({ label: item.equipment_type, value: item.id }));
        },
      },
    },
    {
      label: "gas_type",
      keySource: "gas_type",
      key: "emissions_subcategory_id",
      required: true,
      lookup: {
        fetch: async () => {
          const gasesCategoryId = await requireGasesCategoryId();
          const list = await LookupsService.fetchSubcategoriesByCategory(gasesCategoryId, projectId);
          return mapToOptions(list);
        },
      },
    },
    {
      label: "gas",
      keySource: "gas",
      key: "emissions_source",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: DataEntryRow }) => {
          const subcategoryId = ctx?.row?.emissions_subcategory_id;
          if (!subcategoryId) return [];
          const list = await LookupsService.fetchBgmSources([3, 4], subcategoryId, projectId);
          return mapToOptions(list);
        },
      },
    },
    { label: "charge_kg", keySource: "charge_kg", key: "charge_kg", number: true, required: true },
    { label: "notes", keySource: "notes", key: "notes" },
  ],

  columns: () => [
    {
      header: "Application Type",
      width: "16%",
      key: "application_type",
      editable: true,
      editorType: "select",
      idKey: "application_type_id",
      getOptions: async () => {
        const list = await fetchProjectFugitives(projectId);
        const filtered = jurisdictionName
          ? list.filter((item) => item.jurisdiction?.name === jurisdictionName)
          : list;
        return filtered.map((item) => ({
          label: item.equipment_type,
          value: item.id,
          leakageRate: item.default_annual_leakage_rate != null
            ? Number.parseFloat(String(item.default_annual_leakage_rate))
            : null,
        }));
      },
      onSelect: (selected?: Record<string, unknown>) => ({
        annual_leakage_rate_percent: selected?.leakageRate ?? null,
      }),
      clearsOnChange: [],
    },
    {
      header: "Gas Type",
      width: "14%",
      key: "gas_type",
      editable: true,
      editorType: "select",
      idKey: "emissions_subcategory_id",
      getOptions: async () => {
        const gasesCategoryId = await requireGasesCategoryId();
        const list = await LookupsService.fetchSubcategoriesByCategory(gasesCategoryId, projectId);
        return mapToOptions(list);
      },
      clearsOnChange: ["gas"],
    },
    {
      header: "Gas",
      width: "14%",
      key: "gas",
      editable: true,
      editorType: "select",
      idKey: "emissions_source",
      dependsOnKeys: ["emissions_subcategory_id"],
      getOptions: async (ctx?: { row?: DataEntryRow }) => {
        const subcategoryId = ctx?.row?.emissions_subcategory_id;
        if (!subcategoryId) return [];
        const list = await LookupsService.fetchBgmSources([3, 4], subcategoryId, projectId);
        return mapToOptions(list);
      },
      noCache: true,
      refreshOnDepsChange: true,
      clearsOnChange: [],
    },
    {
      header: "Annual Leakage Rate (%)",
      width: "14%",
      key: "annual_leakage_rate_percent",
      editable: false,
      editorType: "number",
    },
    {
      header: "Charge (kg)",
      width: "10%",
      key: "charge_kg",
      editable: true,
      editorType: "number",
    },
    {
      header: "Emissions (tCO2e)",
      width: "12%",
      key: "emissions_tco2e",
      editable: false,
    },
    {
      header: "Notes / Comments (optional)",
      width: "20%",
      key: "notes",
      editable: true,
      editorType: "text",
    },
  ],
});
