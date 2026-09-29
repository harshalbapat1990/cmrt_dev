// electricityConfig.ts
// Table config for the Detailed Level – Electricity table.
// Used for LARGE projects in Business Case and Design → Construction sub-stage.

import EmissionCalculationsService from "../../../services/EmissionCalculations.service";
import LookupsService, { type UnitOption } from "../../../services/Lookups.service";
import { formatEmissionsOrQuantity } from "../../../utils/utils";

export const ELECTRICITY_EMISSION_SOURCES = [
  "Grid Electricity",
  "Onsite Renewable Electricity",
  "Offsite Renewable Electricity",
] as const;

export type ElectricityEmissionSource = (typeof ELECTRICITY_EMISSION_SOURCES)[number];

const getYear = (value: any): number | null => {
  if (value == null || value === "") return null;
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const str = String(value).trim();
  // Handles "2026"
  if (/^\d{4}$/.test(str)) {
    return Number(str);
  }
  // Handles "2026-06-24"
  const parsed = new Date(str);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.getFullYear();
  }
  return null;
};

export const electricityConfig = (projectId: string) => ({
  tableName: "",

  calculation: {
    grade: 1,
    requiredKeys: ["emission_source", "year", "quantity_mwh"],
    triggerKeys: ["emission_source", "year", "quantity_mwh", "unit_display", "unit_id"],
    buildPayload: (row: any, ctx: {
      jurisdiction: string,
      ops_start_year: number, 
      reference_period: number,
      construction_start_year: string, 
      construction_end_year: string, 
      project_id?: string, 
      tableKey: string,
      project_option_id?: string | null;
      project_stage_instance_id?: string | null;
    }) => {
      if (!row.emission_source || !row.year || !row.quantity_mwh) return null;
      const basePayload = {
        project_id: ctx.project_id ?? projectId,
        emission_source: row.emission_source,
        year: Number(row.year),
        quantity: Number(row.quantity_mwh),
        unit: row.unit_display ?? "MWh",
        project_option_id: ctx.project_option_id || null,
        project_stage_instance_id: ctx.project_stage_instance_id ?? null,
        ui_table_key: ctx.tableKey,
      };
      if (ctx.tableKey === "electricity") {
        const constructionStartYear = getYear(ctx.construction_start_year);
        const constructionEndYear = getYear(ctx.construction_end_year);

        if (!constructionStartYear || !constructionEndYear) {
          return null;
        }
        return {
          ...basePayload,
          construction_start_year: constructionStartYear,
          construction_end_year: constructionEndYear,
        };
      }
      if (ctx.tableKey === "opEnergyElectricity") {
        const opsStartYear = getYear(ctx.ops_start_year);
        const opsEndYear =
          opsStartYear && ctx.reference_period
            ? opsStartYear + Number(ctx.reference_period)
            : null;

        if (!opsStartYear || !opsEndYear) {
          return null;
        }

        return {
          ...basePayload,
          ops_start_year: opsStartYear,
          ops_end_year: opsEndYear,
        };
      }
      return null;
    },

    calculate: async (payload: any) => {
      const res = await EmissionCalculationsService.electricityCalculations(payload);
      return res?.data ?? res;
    },

    mapResultToRow: (apiRes: any, row?: any) => {
      const data = apiRes?.data ?? apiRes;

      const location = data?.location_based_total_tco2e ?? null;
      const market = data?.market_based_total_tco2e ?? null;
      const total = location ?? market ?? null;

      return {
        location_based_tco2e: location,
        market_based_tco2e: market,
        total_emissions_tco2e: total,
        emissions_tco2e: total,
        unit_display: row?.unit_display,
      };
    },

  },

  // Used by the Operational energy (B6) table's blank template and bulk upload.
  fileHeaders: [
    { key: "emission_source", label: "Emission source" },
    { key: "year", label: "Year" },
    { key: "quantity_mwh", label: "Quantity (MWh)" },
    { key: "unit_display", label: "Unit" },
    { key: "notes", label: "Notes/Comments (optional)" },
  ],

  // Validation rules (used by handleSaveNewRow required-field check)
  rules: [
    {
      label: "Emission source",
      key: "emission_source",
      required: true,
      options: [...ELECTRICITY_EMISSION_SOURCES],
    },
    { label: "year", key: "year", number: true, required: true },
    { label: "quantity_mwh", key: "quantity_mwh", number: true, required: true },
    { label: "Unit", key: "unit_display" },
    { label: "Notes/Comments", key: "notes" },
  ],

  columns: () => [
    {
      header: "Emission source",
      width: "22%",
      key: "emission_source",
      editable: true,
      editorType: "select",
      getOptions: async () =>
        ELECTRICITY_EMISSION_SOURCES.map((s) => ({ label: s, value: s })),
    },
    {
      header: "Year",
      width: "8%",
      key: "year",
      editable: true,
      editorType: "year", // Use a custom editor type
      render: (row: any) => (row.year ? String(row.year) : ""),
    },
    {
      header: "Quantity",
      width: "12%",
      key: "quantity_mwh",
      editable: true,
      editorType: "number",
    },
    {
      header: "Unit",
      width: "8%",
      key: "unit_display",
      editable: true,
      editorType: "select",
      idKey: "unit_id",
      defaultValue: "MWh",
      getOptions: async () => {
        const datasetRevisionId = await LookupsService.resolveProjectDatasetRevisionId(projectId);
        const list: UnitOption[] = await LookupsService.fetchElectricityUnits(datasetRevisionId);
        return list.map((u) => ({
          label: u.name,
          value: u.id,
          is_canonical: u.is_canonical,
          canonical_unit_id: u.canonical_unit_id ?? null,
          canonical_unit_code: u.canonical_unit_code ?? u.name,
          to_canonical_factor: u.to_canonical_factor ?? null,
        }));
      },
      onSelect: (selected: any) => ({
        unit_display: selected?.label ?? selected?.name ?? "MWh",
        canonical_unit_id: selected?.canonical_unit_id ?? null,
        unit_conversion_factor: selected?.to_canonical_factor ?? null,
        canonical_unit_code: selected?.canonical_unit_code ?? selected?.label ?? null,
      }),
      noCache: false,
      render: (row: any) => row?.unit_display ?? "MWh",
    },
    {
      header: "Location-based (tCO₂e)",
      width: "16%",
      key: "location_based_tco2e",
      editable: false,
      editorType: "number",
      render: (row: any) => formatEmissionsOrQuantity(row.location_based_tco2e),
    },
    {
      header: "Market-based (tCO₂e)",
      width: "16%",
      key: "market_based_tco2e",
      editable: false,
      editorType: "number",
      render: (row: any) => formatEmissionsOrQuantity(row.market_based_tco2e),
    },
    {
      header: "Notes / Comments (optional)",
      width: "18%",
      key: "notes",
      editable: true,
      editorType: "text",
    },
  ],
});
