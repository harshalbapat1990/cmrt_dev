import { describe, expect, it } from "vitest";
import { assetTableConfig } from "./assetConfig";
import { componentTableConfig } from "./componentConfig";
import { componentReplacementConfig } from "./componentReplacementConfig";
import { createB1G2Config } from "./useB1G2Config";
import { constructionG2Config } from "./constructionG2Config";
import { constructionG3Config } from "./constructionG3Config";
import { opEnergyTableConfig } from "./opEnergyTableConfig";
import { refurbishmentTableConfig } from "./refurbishmentTableConfig";
import { electricityConfig } from "./electricityConfig";
import { createB1G3Config } from "./useB1G3Config";
import { concreteRegSimplifiedConfig } from "./ConcreteRegSimplifiedConfig";
import { concreteRegDetailedConfig } from "./concreteRegDetailedConfig";
import type { DataEntryRow } from "./dataEntryTypes";
import { isCalcConfig } from "./useEmissionsCalc";

describe("table calculation configuration contracts", () => {
  it("accepts complete calculation configs and rejects malformed config values", () => {
    const calculation = assetTableConfig("project-1").calculation;
    expect(isCalcConfig(calculation)).toBe(true);
    expect(isCalcConfig({ ...calculation, grade: 9 })).toBe(false);
    expect(isCalcConfig({ ...calculation, requiredKeys: ["quantity", 1] })).toBe(false);
    expect(isCalcConfig({ grade: 1 })).toBe(false);
    expect(isCalcConfig(null)).toBe(false);
  });

  it("builds an asset calculation payload using canonical unit conversion", () => {
    const config = assetTableConfig("project-1").calculation;
    const payload = config.buildPayload({
      mastertype_name: "Road",
      typecast_name: "Arterial",
      band_code: "Mid",
      canonical_unit_code: "km",
      unit_conversion_factor: 0.001,
      quantity: 2000,
    }, { jurisdiction: "Australia" });

    expect(payload).toEqual({
      mastertype: "Road",
      typecast: "Arterial",
      sensitivity: "Mid",
      functional_unit: "km",
      quantity: 2,
      jurisdiction: "Australia",
    });
    expect(config.mapResultToRow({ total_emissions_tco2e: "12.5" })).toEqual({ emissions_tco2e: 12.5 });
  });

  it("preserves component and replacement payload fields and ignores malformed responses", () => {
    const component = componentTableConfig("project-1").calculation;
    const replacement = componentReplacementConfig("project-1").calculation;
    const row: DataEntryRow = {
      emissions_category: "Materials",
      emissions_subcategory: "Concrete",
      emissions_source_name: "Ready mix",
      quantity: 3,
      unit_code: "m3",
      life: 20,
    };

    expect(component.buildPayload(row, { jurisdiction: "Australia" })).toMatchObject({
      emissions_category: "Materials",
      emissions_sub_category: "Concrete",
      emissions_source: "Ready mix",
      quantity: 3,
      unit: "m3",
    });
    expect(replacement.buildPayload(row, { project_id: "project-1" })).toMatchObject({
      emissions_category: "Materials",
      emissions_sub_category: "Concrete",
      emissions_source: "Ready mix",
      project_id: "project-1",
      life_years: 20,
    });
    expect(component.mapResultToRow(null)).toEqual({ emissions_tco2e: null, total_emissions_tco2e: null });
  });

  it("builds a fugitive calculation with the selected operation period", () => {
    const config = createB1G2Config("Australia", "project-1").calculation;
    expect(config.buildPayload({
      application_type: "Chiller",
      charge_kg: 4,
      gas: "R32",
      gas_type: "HFC",
    }, {
      jurisdiction: "Australia",
      ops_start_year: 2030,
      reference_period: 25,
    })).toEqual({
      application_type: "Chiller",
      charge_kg: "4",
      gas: "R32",
      gas_type: "HFC",
      jurisdiction: "Australia",
      ops_start: 2030,
      ops_end: 2055,
      project_id: "project-1",
    });
    expect(config.mapResultToRow({ total_emissions_tco2e: 10, annual_leakage_rate_percent: 2 }))
      .toMatchObject({ emissions_tco2e: 10, annual_leakage_rate_percent: 2 });
  });

  it("keeps construction grade 2 and grade 3 lookup values in their calculation payloads", () => {
    const constructionRow: DataEntryRow = {
      emissions_category: "Materials",
      emissions_subcategory: "Asphalt",
      emissions_source_name: "Hot mix",
      unit_code: "t",
      quantity: 5,
    };
    const context = { jurisdiction: "Australia" };

    expect(constructionG2Config("project-1").calculation.buildPayload(constructionRow, context))
      .toMatchObject({ emissions_category: "Materials", emissions_sub_category: "Asphalt", emissions_source: "Hot mix", quantity: 5, unit: "t" });
    expect(constructionG3Config("project-1").calculation.buildPayload({
      ...constructionRow,
      canonical_unit_code: "kg",
      unit_conversion_factor: 1000,
    }, context)).toMatchObject({
      emissions_category: "Materials",
      emissions_sub_category: "Asphalt",
      emissions_source: "Hot mix",
      quantity: 5000,
      unit: "kg",
    });
  });

  it("builds operational energy payloads with the selected operation period", () => {
    const config = opEnergyTableConfig("project-1").calculation;
    expect(config.buildPayload({ item: "LED lighting", quantity: 8 }, {
      jurisdiction: "New Zealand",
      ops_start_year: 2032,
      reference_period: 30,
    })).toMatchObject({
      jurisdiction: "New Zealand",
      ops_start: 2032,
      ops_end: 2062,
      emissions_source: "LED lighting",
      quantity: 8,
    });
    expect(config.mapResultToRow({ location_based_total_tco2e: 5, market_based_total_tco2e: 4 }))
      .toMatchObject({ emissions_tco2e: 5, market_based_total_tco2e: 4 });
  });

  it("keeps refurbishment calculation blocked when a matching factor is unavailable", () => {
    const config = refurbishmentTableConfig("New Zealand").calculation;
    expect(config.buildPayload({ mr_factor_id: "missing", quantity: 3, frequency: 5 }, {
      reference_period: 20,
    })).toBeNull();
    expect(config.mapResultToRow(null)).toEqual({
      emissions_tco2e: null,
      total_emissions_tco2e: null,
    });
  });

  it("builds electricity payloads within the selected project period", () => {
    const calculation = electricityConfig("project-1").calculation;
    const payload = calculation.buildPayload({
      emission_source: "Grid Electricity",
      year: "2035",
      quantity_mwh: 100,
      unit_display: "MWh",
    }, {
      jurisdiction: "Australia",
      ops_start_year: 2030,
      reference_period: 25,
      construction_start_year: "2029-01-01",
      construction_end_year: "2032-12-31",
      tableKey: "electricity",
    });

    expect(payload).toMatchObject({
      project_id: "project-1",
      emission_source: "Grid Electricity",
      year: 2035,
      quantity: 100,
      construction_start_year: 2029,
      construction_end_year: 2032,
    });
    expect(calculation.mapResultToRow({ location_based_total_tco2e: 3 }, { unit_display: "MWh" }))
      .toMatchObject({ total_emissions_tco2e: 3, unit_display: "MWh" });
  });

  it("normalizes operational periods and converts detailed use quantities", () => {
    const calculation = createB1G3Config("project-1").calculation;
    expect(calculation.buildPayload({
      emissions_category: "Materials",
      emissions_subcategory: "Steel",
      emissions_source_name: "Recycled steel",
      quantity: 2,
      unit_code: "tonne",
      unit_conversion_factor: 1000,
      period: "Annual Average",
    }, {
      jurisdiction: "Australia",
      ops_start_year: 2031,
      reference_period: 20,
      tableKey: "useB1G3",
      construction_start_year: "2029",
      construction_end_year: "2030",
    })).toMatchObject({
      period: "Annual",
      quantity: 2000,
      unit: "tonne",
      ops_start: 2031,
      ops_end: 2051,
      project_id: "project-1",
    });
  });

  it("builds concrete register payloads for simplified and mix design entries", () => {
    const simplified = concreteRegSimplifiedConfig().calculation;
    expect(simplified.buildPayload({
      mixType: "READY_MIX",
      strength: "32MPa",
      targetSCMContent: 25,
      volume: 10,
    }, { project_id: "project-1" })).toEqual({
      project_id: "project-1",
      mix_type: "Ready-mix",
      strength_mpa: 32,
      scm_pct: 25,
      volume_m3: 10,
    });

    const detailed = concreteRegDetailedConfig().calculation;
    const payload = detailed.buildPayload({
      method: "mix_design",
      mixId: "mix-1",
      mixType: "PRECAST",
      strength: "40MPa",
      volume: 12,
      materials: [{ materialName: "Cement", quantityKgM3: 300 }],
    }, { project_id: "project-1" });
    expect(payload).toEqual({
      method: "mix_design",
      request: {
        project_id: "project-1",
        mix_id_label: "mix-1",
        mix_type: "Precast",
        strength_mpa: 40,
        volume_m3: 12,
        materials: [{ material_name: "Cement", quantity_kg_m3: 300 }],
      },
    });
    expect(detailed.mapResultToRow({ data: { emissions_tco2e: "7.5" } }))
      .toMatchObject({ emissions_tco2e: 7.5 });
  });
});
