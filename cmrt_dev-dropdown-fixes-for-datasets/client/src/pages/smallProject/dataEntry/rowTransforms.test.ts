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
