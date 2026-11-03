import { describe, expect, it } from "vitest";
import fc from "fast-check";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import { apiRowToUiRow, buildExtraFields } from "./rowTransforms";

describe("activity row transformation invariants", () => {
  it("round-trips finite emissions values and preserves row IDs", () => {
    fc.assert(
      fc.property(
        fc.uuid(),
        fc.double({ min: 0, max: 1_000_000, noNaN: true, noDefaultInfinity: true }),
        (id, value) => {
          const row = apiRowToUiRow({
            id,
            project_id: "project-1",
            project_stage_instance_id: "stage-1",
            ui_table_key: "asset",
            quantity: 0,
            emissions_tco2e: String(value),
            extra_fields: {},
          } satisfies ActivityDataOut);

          expect(row.id).toBe(id);
          expect(row.emissions_tco2e).toBe(value);
          expect(Number.isFinite(row.emissions_tco2e)).toBe(true);
        },
      ),
      { numRuns: 150, seed: 20261103 },
    );
  });

  it("preserves zero and finite numeric API emissions across generated values", () => {
    // Deterministic bounded property sweep: zero, whole values, and decimal values.
    const values = Array.from({ length: 501 }, (_, index) => index / 10);

    for (const value of values) {
      const row = apiRowToUiRow({
        id: `activity-${value}`,
        project_id: "project-1",
        project_stage_instance_id: "stage-1",
        ui_table_key: "asset",
        quantity: 0,
        emissions_tco2e: String(value),
        extra_fields: { total_emissions_tco2e: 999 },
      } satisfies ActivityDataOut);

      expect(row.emissions_tco2e).toBe(value);
      expect(row.total_emissions_tco2e).toBe(value);
      expect(Number.isFinite(row.emissions_tco2e)).toBe(true);
      expect(row.quantity).toBe(0);
    }
  });

  it("never leaks row identity or calculated totals into generic extra fields", () => {
    const ids = Array.from({ length: 25 }, (_, index) => `row-${index}`);
    for (const id of ids) {
      const extra = buildExtraFields({
        id,
        metric_id: `metric-${id}`,
        quantity: 0,
        unit_id: "unit-1",
        emissions_tco2e: 0,
        total_emissions_tco2e: 0,
        user_value: id,
      });

      expect(extra).toEqual({ user_value: id });
    }
  });
});
