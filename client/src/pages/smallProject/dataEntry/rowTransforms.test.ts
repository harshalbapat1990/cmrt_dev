import { describe, expect, it } from "vitest";
import { apiRowToUiRow, buildExtraFields } from "./rowTransforms";
import type { ActivityDataOut } from "@/services/ActivityData.service";

describe("activity row transforms", () => {
  it("maps the API emissions result and reporting metadata into the editable row model", () => {
    const row = apiRowToUiRow({
      id: "activity-1",
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      ui_table_key: "asset",
      quantity: 2,
      emissions_tco2e: "12.5",
      extra_fields: { reporting_boundary_id: "boundary-1", custom_value: "kept" },
    } satisfies ActivityDataOut);

    expect(row).toMatchObject({
      id: "activity-1",
      quantity: 2,
      emissions_tco2e: 12.5,
      total_emissions_tco2e: 12.5,
      reporting_boundary_id: "boundary-1",
      custom_value: "kept",
      _fromBoundary: true,
    });
  });

  it.each([
    { apiValue: "0", expected: 0 },
    { apiValue: "12.75", expected: 12.75 },
    { apiValue: null, expected: null },
    { apiValue: "-", expected: null },
  ])("preserves valid zero and finite calculated values (%o)", ({ apiValue, expected }) => {
    const row = apiRowToUiRow({
      id: "stable-row",
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      ui_table_key: "asset",
      quantity: 0,
      emissions_tco2e: apiValue,
      extra_fields: { total_emissions_tco2e: 999 },
    } satisfies ActivityDataOut);

    expect(row.id).toBe("stable-row");
    expect(row.quantity).toBe(0);
    expect(row.emissions_tco2e).toBe(expected);
    expect(row.total_emissions_tco2e).toBe(expected);
  });

  it("keeps calculation outputs only when the target table supports them", () => {
    const row = {
      id: "activity-1",
      metric_id: "metric-1",
      quantity: 2,
      unit_id: "unit-1",
      emissions_tco2e: 12,
      total_emissions_tco2e: 12,
      location_based_tco2e: 4,
      market_based_tco2e: 8,
      custom_field: "value",
    };

    expect(buildExtraFields(row, { tableKey: "asset" })).toEqual({ custom_field: "value" });
    expect(buildExtraFields(row, { tableKey: "electricity", keepEmissions: true })).toEqual({
      location_based_tco2e: 4,
      market_based_tco2e: 8,
      total_emissions_tco2e: 12,
      custom_field: "value",
    });
  });
});
