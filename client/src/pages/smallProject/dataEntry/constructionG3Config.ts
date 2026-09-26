// constructionG3Config.ts
import LookupsService, { type UnitOption } from "@/services/Lookups.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";

const GRADE34_IDS = [3, 4];

const DATAQUALITY_OPTIONS = [
  { label: "Estimated", value: "Estimated" },
  { label: "Monitored", value: "Monitored" },
];

const mapToOptions = (list: any[], labelField = "name", valueField = "id") =>
  (list ?? []).map((x) => ({ label: x[labelField], value: x[valueField] }));


const pickLabel = (v: any) => {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  return v.label ?? v.name ?? v.value ?? "";
};


export const constructionG3Config = (projectId?: string, tableKey?: string, allowedCategories?: string[]) => {
  const showDataQuality = tableKey === "constructionG3";
  return {
    tableName: "Detailed level - construction stage",
    calculation: {
      grade: 2,
      // compute only when these exist
      requiredKeys: [
        "emissions_category",
        "emissions_subcategory",
        "emissions_source_name",
        "unit_code",
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
        "quantity",
        "unit_code",
        "unit_id",
      ],
      buildPayload: (row: any, ctx: { jurisdiction: string }) => {
        const emissions_category = pickLabel(row.emissions_category);
        const emissions_sub_category = pickLabel(row.emissions_subcategory);
        const emissions_source = pickLabel(row.emissions_source_name);
        const quantity = row.quantity != null ? Number(row.quantity) : NaN;
        const unit = pickLabel(row.canonical_unit_code || row.unit_code);
        const convFactor = row.unit_conversion_factor != null ? Number(row.unit_conversion_factor) : 1;
        const convertedQuantity = Number.isNaN(quantity) ? NaN : quantity * convFactor;

        if (!emissions_category || !emissions_sub_category || !emissions_source || Number.isNaN(convertedQuantity) || !unit) {
          return null;
        }

        return {
          emissions_category: emissions_category,
          emissions_source: emissions_source,
          emissions_sub_category: emissions_sub_category,
          jurisdiction: ctx.jurisdiction,
          quantity: convertedQuantity,
          unit,
        };
      },

      // table-specific API call
      calculate: async (payload: any) => {
        // For component table, use grade2 endpoint OR your table endpoint
        return EmissionCalculationsService.grade34Calculations(payload);
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
      ...(showDataQuality
        ? [{ key: "data_quality", label: "Data quality" }]
        : []),
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
            const list = await LookupsService.fetchBgmCategories(GRADE34_IDS, projectId);
            const opts = mapToOptions(list);
            if (!allowedCategories?.length) return opts;
            const allowed = new Set(allowedCategories.map((s) => s.trim().toLowerCase()));
            return opts.filter((o) => allowed.has(o.label.trim().toLowerCase()));
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
            const list = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, categoryId, projectId);
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
            const list = await LookupsService.fetchBgmSources(GRADE34_IDS, subCategoryId, projectId);
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
              const list = await LookupsService.fetchBgmSourceUnits(GRADE34_IDS, subCategoryId, source, datasetRevisionId);
              return mapToOptions(list);
            }
            return [];
          },
          labelField: "label",
          idField: "value",
        },
      },
      ...(showDataQuality
        ? [
          {
            label: "Data quality",
            keySource: "data_quality",
            key: "data_quality",
            required: true,
            options: DATAQUALITY_OPTIONS.map((x) => x.value),
          },
        ]
        : []),
      { label: "Quantity", keySource: "quantity", key: "quantity", number: true, required: true },
      { label: "Notes/Comments (optional)", keySource: "notes", key: "notes" },
    ],

    columns: () => [
      {
        header: "Emissions category",
        width: "18%",
        key: "emissions_category",
        editable: true,
        // editableWhen: (row: any) => row?.id === "__NEW__",
        editorType: "select",
        idKey: "emissions_category_id",
        getOptions: async () => {
          const list = await LookupsService.fetchBgmCategories(GRADE34_IDS, projectId);
          const opts = mapToOptions(list);
          if (!allowedCategories?.length) return opts;
          const allowed = new Set(allowedCategories.map((s) => s.trim().toLowerCase()));
          return opts.filter((o) => allowed.has(o.label.trim().toLowerCase()));
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
        width: "16%",
        key: "emissions_subcategory",
        editable: true,
        // editableWhen: (row: any) => row?.id === "__NEW__",
        editorType: "select",
        idKey: "emissions_subcategory_id",
        dependsOnKeys: ["emissions_category_id"],
        getOptions: async (ctx?: { row?: any }) => {
          const categoryId = ctx?.row?.emissions_category_id;
          if (!categoryId) return [];
          const list = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, categoryId, projectId);
          return mapToOptions(list);
        },
        clearsOnChange: ["emissions_source_name", "emissions_source", "unit_code", "unit_id"],
        noCache: true,
        refreshOnDepsChange: true,
      },
      {
        header: "Emissions source",
        width: "20%",
        key: "emissions_source_name",
        editable: true,
        // editableWhen: (row: any) => row?.id === "__NEW__",
        editorType: "select",
        idKey: "emissions_source",
        dependsOnKeys: ["emissions_subcategory_id"],
        getOptions: async (ctx?: { row?: any }) => {
          const subCategoryId = ctx?.row?.emissions_subcategory_id;
          if (!subCategoryId) return [];
          const list = await LookupsService.fetchBgmSources(GRADE34_IDS, subCategoryId, projectId);
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
        const list: UnitOption[] = await LookupsService.fetchBgmSourceUnits(GRADE34_IDS, subCategoryId, source, datasetRevisionId);
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
      ...(showDataQuality
        ? [
          {
            header: "Data quality",
            width: "10%",
            key: "data_quality",
            editable: true,
            editorType: "select",
            idKey: "data_quality",
            getOptions: async () => DATAQUALITY_OPTIONS,
          },
        ]
        : []),

      {
        header: "Quantity",
        width: "8%",
        key: "quantity",
        editable: true,
        editorType: "number",
      },
      {
        header: "Emissions (tCO2e)",
        width: "10%",
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
  };
};
