// componentConfig.ts
import LookupsService, { type UnitOption } from "@/services/Lookups.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";

const GRADE2_IDS = [2];

const mapToOptions = (list: any[], labelField = "name", valueField = "id") =>
  (list ?? []).map((x) => ({ label: x[labelField], value: x[valueField] }));


const pickLabel = (v: any) => {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  return v.label ?? v.name ?? v.value ?? "";
};


export const constructionG2Config = (projectId?: string) => ({
  tableName: "Component level",
  
calculation: {
    grade: 2,
    // compute only when these exist
    requiredKeys: [
      "emissions_category",
      "emissions_subcategory",
      "emissions_source_name",
      "quantity",
      "unit_code",
    ],
    // if any of these change → recalc
    triggerKeys: [
      "emissions_category",
      "emissions_category_id",
      "emissions_subcategory",
      "emissions_subcategory_id",
      "emissions_source_name",
      "emissions_source",
      "quantity",
      "unit_code",
      "unit_id",
    // build API payload from row data
    ],
    buildPayload: (row: any, ctx: { jurisdiction: string }) => {
      const emissions_category = pickLabel(row.emissions_category);
      const emissions_sub_category = pickLabel(row.emissions_subcategory);
      const emissions_source = pickLabel(row.emissions_source_name);
      const quantity = row.quantity != null ? Number(row.quantity) : NaN;
      const unit = pickLabel(row.unit_code);

      if (!emissions_category || !emissions_sub_category || !emissions_source || Number.isNaN(quantity) || !unit) {
        return null;
      }

      return {
        emissions_category: emissions_category,
        emissions_source: emissions_source,
        emissions_sub_category: emissions_sub_category,
        jurisdiction: ctx.jurisdiction,
        quantity: quantity,
        unit: unit,
      };
    },
    
// table-specific API call
    calculate: async (payload: any) => {
      // For component table, use grade2 endpoint OR your table endpoint
      return EmissionCalculationsService.grade2EmissionValues(payload);
    },

    // map API response -> row changes
    mapResultToRow: (apiRes: any) => ({
      emissions_tco2e: apiRes?.total_emissions_tco2e ?? null,
      total_emissions_tco2e: apiRes?.total_emissions_tco2e ?? null, // for easier access in calculations
    }),

  },

  fileHeaders: [
    { key: "emissions_category", label: "Emissions category" },
    { key: "emissions_subcategory", label: "Emissions sub-category" },
    { key: "emissions_source_name", label: "Emissions source" },
    { key: "unit_code", label: "Unit" },
    { key: "quantity", label: "Quantity" },
    { key: "notes", label: "Notes/Comments (optional)" },
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
    {
      label: "Unit",
      keySource: "unit_code",
      key: "unit_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const source = ctx?.row?.emissions_source;
          const subCategoryId = ctx?.row?.emissions_subcategory_id;
          if (source && subCategoryId) {
            const datasetRevisionId = projectId ? await LookupsService.resolveProjectDatasetRevisionId(projectId) : null;
            const list = await LookupsService.fetchBgmSourceUnits(GRADE2_IDS, subCategoryId, source, datasetRevisionId);
            return mapToOptions(list);
          }
          return [];
        },
        labelField: "label",
        idField: "value",
      },
    },
    { 
      label: "Quantity", 
      keySource: "quantity", 
      key: "quantity", 
      number: true, 
      required: true 
    },
    { 
      label: "Notes/Comments (optional)", 
      keySource: "notes", 
      key: "notes" 
    },
  ],

  columns: () => [
    {
      header: "Emissions category",
      width: "20%",
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
        "unit_code",
        "unit_id",
      ],
    },
    {
      header: "Emissions sub-category",
      width: "18%",
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
      clearsOnChange: ["emissions_source_name", "emissions_source", "unit_code", "unit_id"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Emissions source",
      width: "22%",
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
      clearsOnChange: ["unit_code", "unit_id"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Unit",
      width: "8%",
      key: "unit_code",
      editable: true,
      editorType: "select",
      idKey: "unit_id",
      dependsOnKeys: ["emissions_source"],
      getOptions: async (ctx?: { row?: any }) => {
        const source = ctx?.row?.emissions_source;
        const subCategoryId = ctx?.row?.emissions_subcategory_id;
        const datasetRevisionId = (source && subCategoryId && projectId)
          ? await LookupsService.resolveProjectDatasetRevisionId(projectId) : null;
        if (!source || !subCategoryId) return [];
        const list: UnitOption[] = await LookupsService.fetchBgmSourceUnits(GRADE2_IDS, subCategoryId, source, datasetRevisionId);
        return list.map(u => ({
          label: u.name,
          value: u.id,
          is_canonical: u.is_canonical,
          canonical_unit_id: u.canonical_unit_id ?? null,
          canonical_unit_code: u.canonical_unit_code ?? u.name,
          to_canonical_factor: u.to_canonical_factor ?? null,
        }));
      },
      onSelect: (selected: any) => ({
        canonical_unit_id: selected?.canonical_unit_id ?? null,
        unit_conversion_factor: selected?.to_canonical_factor ?? null,
        canonical_unit_code: selected?.canonical_unit_code ?? selected?.label ?? null,
      }),
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Quantity",
      width: "10%",
      key: "quantity",
      editable: true,
      editorType: "number",
    },
    { 
      header: "Emissions (tCO2e)", 
      width: "12%", 
      key: "emissions_tco2e", 
      editable: false 
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
