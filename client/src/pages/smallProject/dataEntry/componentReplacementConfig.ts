import LookupsService from "@/services/Lookups.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";

const GRADE2_IDS = [2];

const mapToOptions = (list: any[], labelField = "name", valueField = "id") =>
  (list ?? []).map((x) => ({ label: x[labelField], value: x[valueField] }));


const pickLabel = (v: any) => {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  return v.label ?? v.name ?? v.value ?? "";
};

export const componentReplacementConfig = (projectId?: string) => ({
  tableName: "Component level",
  calculation: {
    grade: 2,
    // compute only when these exist
    requiredKeys: [
      "emissions_category",
      "emissions_subcategory",
      "emissions_source_name",
      "life",
      "quantity",
    ],
    // if any of these change → recalc
    triggerKeys: [
      "emissions_category",
      "emissions_category_id",
      "emissions_subcategory",
      "emissions_subcategory_id",
      "emissions_source_name",
      "emissions_source",
      "life",
      "quantity",
    ],
    buildPayload: (row: any, ctx: { project_id?: string }) => {
      const emissions_category = pickLabel(row.emissions_category);
      const emissions_sub_category = pickLabel(row.emissions_subcategory);
      const emissions_source = pickLabel(row.emissions_source_name);
      const life_years =
        row.life !== undefined &&
          row.life !== null &&
          String(row.life).trim() !== ""
          ? Number(row.life)
          : NaN;
      const quantity = row.quantity != null ? Number(row.quantity) : NaN;

      if (
        !ctx.project_id ||
        !emissions_category ||
        !emissions_sub_category ||
        !emissions_source ||
        Number.isNaN(quantity) ||
        quantity <= 0 ||
        Number.isNaN(life_years) ||
        life_years <= 0
      ) {
        return null;
      }


      return {
        emissions_category: emissions_category,
        emissions_source: emissions_source,
        emissions_sub_category: emissions_sub_category,
        project_id: ctx.project_id,
        life_years,
        quantity,
      };
    },

    // table-specific API call
    calculate: async (payload: any) => {
      // For component table, use grade2 endpoint OR your table endpoint
      return EmissionCalculationsService.grade2B4ReplCalculations(payload);
    },

    // map API response -> row changes
    mapResultToRow: (apiRes: any) => ({
      emissions_tco2e: apiRes?.total_emissions_tco2e ?? null,
      total_emissions_tco2e: apiRes?.total_emissions_tco2e ?? null,
    }),

  },

  fileHeaders: [
    { 
      key: "emissions_category", 
      label: "Emissions category" 
    },
    { 
      key: "emissions_subcategory", 
      label: "Emissions sub-category" 
    },
    { 
      key: "emissions_source_name", 
      label: "Emissions source" 
    },
    { 
      key: "life", 
      label: "Life (years)" 
    },
    { 
      key: "notes", 
      label: "Notes/Comments (optional)" 
    },
  ],

  rules: [
    {
      label: "Emissions category",
      keySource: "emissions_category",
      key: "emissions_category_id",
      required: true,
      lookup: {
        fetch: async () => {
          const list = await LookupsService.fetchBgmCategories(GRADE2_IDS, projectId);
          return mapToOptions(list);
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Emissions sub-category",
      keySource: "emissions_subcategory",
      key: "emissions_subcategory_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const categoryId = ctx?.row?.emissions_category_id;
          if (!categoryId) return [];
          const list = await LookupsService.fetchBgmSubcategories(GRADE2_IDS, categoryId, projectId);
          return mapToOptions(list);
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Emissions source",
      keySource: "emissions_source_name",
      key: "emissions_source",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const subCategoryId = ctx?.row?.emissions_subcategory_id;
          if (!subCategoryId) return [];
          const list = await LookupsService.fetchBgmSources(GRADE2_IDS, subCategoryId, projectId);
          return mapToOptions(list);
        },
        labelField: "label",
        idField: "value",
      },
    },
    { label: "Life (years)", keySource: "life", key: "life", number: true, required: true },
    { label: "Notes / Comments (optional)", keySource: "notes", key: "notes" },
  ],

  columns: () => [
    {
      header: "Emissions category",
      width: "22%",
      key: "emissions_category",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "emissions_category_id",
      getOptions: async () => {
        const list = await LookupsService.fetchBgmCategories(GRADE2_IDS, projectId);
        return mapToOptions(list);
      },
      clearsOnChange: [
        "emissions_subcategory",
        "emissions_subcategory_id",
        "emissions_source_name",
        "emissions_source",
      ],
    },
    {
      header: "Emissions sub-category",
      width: "22%",
      key: "emissions_subcategory",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "emissions_subcategory_id",
      dependsOnKeys: ["emissions_category_id"],
      getOptions: async (ctx?: { row?: any }) => {
        const categoryId = ctx?.row?.emissions_category_id;
        if (!categoryId) return [];
        const list = await LookupsService.fetchBgmSubcategories(GRADE2_IDS, categoryId, projectId);
        return mapToOptions(list);
      },
      clearsOnChange: ["emissions_source_name", "emissions_source"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Emissions source",
      width: "24%",
      key: "emissions_source_name",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "emissions_source",
      dependsOnKeys: ["emissions_subcategory_id"],
      getOptions: async (ctx?: { row?: any }) => {
        const subCategoryId = ctx?.row?.emissions_subcategory_id;
        if (!subCategoryId) return [];
        const list = await LookupsService.fetchBgmSources(GRADE2_IDS, subCategoryId, projectId);
        return mapToOptions(list);
      },
      clearsOnChange: ["life"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Life (years)",
      width: "10%",
      key: "life",
      editable: true,
      editorType: "number",
    },
    {
      header: "Emissions (tCO2e)", 
      width: "12%", 
      key: "emissions_tco2e", 
      editable: false,
      render: (row: any) =>
        row.emissions_tco2e == null || row.emissions_tco2e === "-"
          ? "-"
          : row.emissions_tco2e,
    },
    {
      header: "Notes / Comments (optional)",
      width: "10%",
      key: "notes",
      editable: true,
      editorType: "text",
    },
  ],
});
