import http from "@/http";
import  EmissionCalculationsService from "@/services/EmissionCalculations.service";
import LookupsService from "@/services/Lookups.service";

const mapToOptions = (list: any[], labelField = "name", valueField = "id") =>
  (list ?? []).map((x) => ({ label: x[labelField], value: x[valueField] }));

const pickLabel = (v: any) => {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  return v.label ?? v.name ?? v.value ?? "";
};


export const requireGasesCategoryId = async (): Promise<string> => {
  const categories = await LookupsService.fetchCategories(true);
  const gasesCategory = categories.find(
    (category: any) =>
      category?.is_active !== false &&
      category?.name?.trim().toLowerCase() === "gases" &&
      category?.parent_category_id == null,
  );
  if (!gasesCategory?.id) {
    throw new Error('The active "Gases" emissions category could not be found.');
  }
  return String(gasesCategory.id);
};

const fetchProjectFugitives = async (projectId?: string) => {
  if (!projectId) return [];
  const datasetRevisionId = await LookupsService.resolveProjectDatasetRevisionId(projectId);
  if (!datasetRevisionId) return [];

  const res = await http.get("/api/fugitives", {
    params: { limit: 500, dataset_revision_id: datasetRevisionId, global_only: false },
  });
  return Array.isArray(res.data) ? res.data : [];
};

export const useB1G2Config = (jurisdictionName: string | null, projectId?: string, ) => ({
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
      buildPayload: (row: any, ctx: { jurisdiction: string , ops_start_year: number, reference_period: number}) => {
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
      calculate: async (payload: any) => {
        // For component table, use grade2 endpoint OR your table endpoint
        return EmissionCalculationsService.useB1G2Calculations(payload);
      },
  
      // map API response -> row changes
      mapResultToRow: (apiRes: any) => ({
        emissions_tco2e: apiRes?.total_emissions_tco2e ?? "-",
        annual_leakage_rate_percent: apiRes?.annual_leakage_rate_percent ?? "-",
        _ops_start: apiRes?.ops_start ?? null,
        _ops_end: apiRes?.ops_end ?? null,
      }),
  
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
            ? list.filter((item: any) => item.jurisdiction?.name === jurisdictionName)
            : list;
          return filtered.map((x: any) => ({ label: x.equipment_type, value: x.id }));
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
        fetch: async (ctx?: { row?: any }) => {
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
          ? list.filter((item: any) => item.jurisdiction?.name === jurisdictionName)
          : list;
        return filtered.map((x: any) => ({
          label: x.equipment_type,
          value: x.id,
          leakageRate: x.default_annual_leakage_rate != null
            ? parseFloat(x.default_annual_leakage_rate)
            : null,
        }));
      },
      onSelect: (selected: any) => ({
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
      getOptions: async (ctx?: { row?: any }) => {
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
