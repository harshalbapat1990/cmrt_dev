import LookupsService, { type UnitOption } from "@/services/Lookups.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import type { UploadKey } from "./stageConstants";
import type { DataEntryRow } from "./dataEntryTypes";
import type { CalcCtx } from "./useEmissionsCalc";
import { asTableConfigRecord, mapTableLookupOptions, pickTableLabel } from "./tableConfigUtils";

const GRADE34_IDS = [3, 4];

const filterAllowedCategories = (items: unknown[], allowedNames?: string[]) => {
  if (!allowedNames?.length) return items;
  const allowed = new Set(allowedNames);
  return items.filter((item) => {
    const name = asTableConfigRecord(item).name;
    return typeof name === "string" && allowed.has(name);
  });
};

const normalizePeriod = (value: unknown) => {
  const raw = pickTableLabel(value).trim();

  const map: Record<string, "Annual" | "Total Operational Life"> = {
    "Annual": "Annual",
    "Annual Average": "Annual",
    "annual": "Annual",
    "annual average": "Annual",

    "Total": "Total Operational Life",
    "Total Operational Life": "Total Operational Life",
    "total": "Total Operational Life",
    "total operational life": "Total Operational Life",
  };

  return map[raw] ?? map[raw.toLowerCase()] ?? "";
};

export const createB1G3Config = (projectId?: string, allowedCategoryNames?: string[]) => ({
  tableName: "Detailed level (Grade 3)",
  calculation: {
    grade: 3,
    // compute only when these exist
    requiredKeys: [
      "emissions_category",
      "emissions_subcategory",
      "emissions_source_name",
      "quantity",
      "period",
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
      "period",
      "unit_code",
      "unit",
      "unit_id",
    ],
    buildPayload: (row: DataEntryRow, ctx: { jurisdiction: string; ops_start_year: number; reference_period: number }) => {
      const emissions_category = pickTableLabel(row.emissions_category);
      const emissions_sub_category = pickTableLabel(row.emissions_subcategory);
      const emissions_source = pickTableLabel(row.emissions_source_name);
      const quantity = row.quantity != null ? Number(row.quantity) : NaN;
      const unit = pickTableLabel(row.canonical_unit_code || row.unit_code);
      const convFactor = row.unit_conversion_factor != null ? Number(row.unit_conversion_factor) : 1;
      const convertedQuantity = Number.isNaN(quantity) ? NaN : quantity * convFactor;
      const period = normalizePeriod(row.period);


      if (!ctx.ops_start_year || !ctx.reference_period) {
        return null;
      }

      if (!emissions_category || !emissions_sub_category || !emissions_source || Number.isNaN(convertedQuantity) || !unit || !period) {
        return null;
      }

      const ops_start = ctx.ops_start_year;
      const ops_end = ctx.ops_start_year + ctx.reference_period;


      return {
        emissions_category: emissions_category,
        emissions_source: emissions_source,
        emissions_sub_category: emissions_sub_category,
        jurisdiction: ctx.jurisdiction,
        quantity: convertedQuantity,
        unit,
        period,
        ops_end,
        ops_start,
        project_id: projectId,
      };
    },

    calculate: async (
      payload: Record<string, unknown>,
      _ctx: CalcCtx,
      tableKey: UploadKey
    ) => {

      if (tableKey === "replDetailed") {
        return EmissionCalculationsService.replDetailedG3Calculations(payload);
      }

      if (tableKey === "opEnergyDetailed") {
        return EmissionCalculationsService.opEnergyDetailedCalculations({
          emissions_category: payload.emissions_category,
          emissions_sub_category: payload.emissions_sub_category,
          emissions_source: payload.emissions_source,
          jurisdiction: payload.jurisdiction,
          quantity: payload.quantity,
          unit: payload.unit,
          project_id: projectId,
          period: payload.period,
        });
      }

      if (tableKey === "useB1G3") {
        return EmissionCalculationsService.detailedG3Calculations(payload);
      }
    },

    // map API response -> row changes
    mapResultToRow: (apiRes: unknown) => ({
      emissions_tco2e: asTableConfigRecord(apiRes).total_emissions_tco2e ?? null,
    }),

  },

  fileHeaders: [
    { key: "emissions_category", label: "Emissions category" },
    { key: "emissions_subcategory", label: "Emissions sub-category" },
    { key: "emissions_source_name", label: "Emissions source" },
    { key: "period", label: "Period" },
    { key: "unit_code", label: "Unit" },
    { key: "quantity", label: "Quantity (unit)" },
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
          const filtered = filterAllowedCategories(list, allowedCategoryNames);
          return mapTableLookupOptions(filtered);
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Emissions subcategory",
      keySource: "emissions_subcategory",
      key: "emissions_subcategory_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: DataEntryRow }) => {
          const categoryId = ctx?.row?.emissions_category_id;
          if (!categoryId) return [];
          const list = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, categoryId, projectId);
          return mapTableLookupOptions(list);
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
        fetch: async (ctx?: { row?: DataEntryRow }) => {
          const subCategoryId = ctx?.row?.emissions_subcategory_id;
          if (!subCategoryId) return [];
          const list = await LookupsService.fetchBgmSources(GRADE34_IDS, subCategoryId, projectId);
          return mapTableLookupOptions(list);
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Period",
      keySource: "period",
      key: "period",
      required: true,
    },
    {
      label: "Unit",
      keySource: "unit_code",
      key: "unit_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: DataEntryRow }) => {
          const sourceValue = ctx?.row?.emissions_source;
          const source = typeof sourceValue === "string" ? sourceValue : null;
          const subCategoryId = ctx?.row?.emissions_subcategory_id;
          if (source && subCategoryId) {
            const datasetRevisionId = projectId ? await LookupsService.resolveProjectDatasetRevisionId(projectId) : null;
            const list = await LookupsService.fetchBgmSourceUnits(GRADE34_IDS, subCategoryId, source, datasetRevisionId);
            return mapTableLookupOptions(list);
          }
          return [];
        },
        labelField: "label",
        idField: "value",
      },
    },
    { label: "Quantity", keySource: "quantity", key: "quantity", number: true, required: true },
    { label: "notes", keySource: "notes", key: "notes" },
  ],

  columns: () => [
    {
      header: "Emissions category",
      width: "18%",
      key: "emissions_category",
      editable: true,
      editorType: "select",
      idKey: "emissions_category_id",
      getOptions: async () => {
        const list = await LookupsService.fetchBgmCategories(GRADE34_IDS, projectId);
        const filtered = filterAllowedCategories(list, allowedCategoryNames);
        return mapTableLookupOptions(filtered);
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
      editorType: "select",
      idKey: "emissions_subcategory_id",
      dependsOnKeys: ["emissions_category_id"],
      getOptions: async (ctx?: { row?: DataEntryRow }) => {
        const categoryId = ctx?.row?.emissions_category_id;
        if (!categoryId) return [];
        const list = await LookupsService.fetchBgmSubcategories(GRADE34_IDS, categoryId, projectId);
        return mapTableLookupOptions(list);
      },
      clearsOnChange: ["emissions_source_name", "emissions_source", "unit_code", "unit_id"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Emissions source",
      width: "18%",
      key: "emissions_source_name",
      editable: true,
      editorType: "select",
      idKey: "emissions_source",
      dependsOnKeys: ["emissions_subcategory_id"],
      getOptions: async (ctx?: { row?: DataEntryRow }) => {
        const subCategoryId = ctx?.row?.emissions_subcategory_id;
        if (!subCategoryId) return [];
        const list = await LookupsService.fetchBgmSources(GRADE34_IDS, subCategoryId, projectId);
        return mapTableLookupOptions(list);
      },
      clearsOnChange: ["unit_code", "unit_id"],
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Period",
      width: "10%",
      key: "period",
      editable: true,
      editorType: "select",
      getOptions: async () => [
        { label: "Annual Average", value: "Annual" },
        { label: "Total Operational Life", value: "Total" },
      ],
    },
    {
      header: "Unit",
      width: "7%",
      key: "unit_code",
      editable: true,
      editorType: "select",
      idKey: "unit_id",
      dependsOnKeys: ["emissions_source"],
      getOptions: async (ctx?: { row?: DataEntryRow }) => {
        const sourceValue = ctx?.row?.emissions_source;
        const source = typeof sourceValue === "string" ? sourceValue : null;
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
      onSelect: (selected?: Record<string, unknown>) => ({
        canonical_unit_id: selected?.canonical_unit_id ?? null,
        unit_conversion_factor: selected?.to_canonical_factor ?? null,
        canonical_unit_code: selected?.canonical_unit_code ?? selected?.label ?? null,
      }),
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Quantity",
      width: "8%",
      key: "quantity",
      editable: true,
      editorType: "number",
    },
    { header: "Emissions (tCO2e)", 
      width: "10%", 
      key: "emissions_tco2e", 
      editable: false 
    },
    {
      header: "Notes / Comments (optional)",
      width: "13%",
      key: "notes",
      editable: true,
      editorType: "text",
    },
  ],
});
