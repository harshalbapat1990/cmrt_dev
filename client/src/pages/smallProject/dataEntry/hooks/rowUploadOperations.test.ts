import { describe, expect, it, vi } from "vitest";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow } from "../dataEntryTypes";
import { createRowUploadOperations } from "./rowUploadOperations";

const { bulkUpsert } = vi.hoisted(() => ({ bulkUpsert: vi.fn() }));
vi.mock("@/services/ActivityData.service", () => ({
  default: { bulkUpsert },
}));

function createOperations(overrides: Partial<Parameters<typeof createRowUploadOperations>[0]> = {}) {
  const updateRows = vi.fn();
  const setErrorForKey = vi.fn();
  const refreshOptionTotals = vi.fn(async () => undefined);
  const apiRowToUiRow = (row: ActivityDataOut) => ({
    id: row.id,
    emissions_tco2e: row.emissions_tco2e,
    total_emissions_tco2e: row.emissions_tco2e,
  } as DataEntryRow);
  const operations = createRowUploadOperations({
    activeStageInstance: { id: "stage-1", stage: "DESIGN" },
    projectId: "project-1",
    activeOptionId: "option-1",
    activePeriod: null,
    getRows: () => [],
    updateRows,
    setErrorForKey,
    resolveMetricId: async () => "metric-1",
    apiRowToUiRow,
    computeEmissionsForRow: async () => ({ total_emissions_tco2e: 2 }),
    refreshOptionTotals,
    validateComponentReplLife: () => null,
    ...overrides,
  });
  return { operations, updateRows, setErrorForKey, refreshOptionTotals, apiRowToUiRow };
}

describe("createRowUploadOperations", () => {
  it("calculates and persists uploaded rows, then replaces optimistic rows with saved rows", async () => {
    bulkUpsert.mockResolvedValueOnce([
      { id: "saved-row", project_id: "project-1", project_stage_instance_id: "stage-1", quantity: 4, ui_table_key: "asset", emissions_tco2e: "24322.5" },
    ]);
    const { operations, updateRows, refreshOptionTotals } = createOperations({
      computeEmissionsForRow: async () => ({ total_emissions_tco2e: 68550 }),
    });
    const rows: DataEntryRow[] = [{ quantity: 4, notes: "uploaded" }];

    await operations.onUploadSuccess(rows, "asset");

    expect(bulkUpsert).toHaveBeenCalledWith("stage-1", "asset", [expect.objectContaining({
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      project_option_id: "option-1",
      metric_id: "metric-1",
      quantity: 4,
      ui_table_key: "asset",
      emissions_tco2e: 68550,
      extra_fields: expect.objectContaining({ notes: "uploaded", total_emissions_tco2e: 68550 }),
    })]);
    expect(updateRows).toHaveBeenLastCalledWith("asset", [{
      id: "saved-row",
      emissions_tco2e: "24322.5",
      total_emissions_tco2e: "24322.5",
    }]);
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("rejects an invalid component replacement upload before persisting", async () => {
    bulkUpsert.mockClear();
    const { operations, setErrorForKey } = createOperations({
      validateComponentReplLife: () => "Life exceeds the project limit",
    });

    await operations.onUploadSuccess([{ life: 12 }], "componentRepl");

    expect(bulkUpsert).not.toHaveBeenCalled();
    expect(setErrorForKey).toHaveBeenCalledWith("componentRepl", "Row 1: Life exceeds the project limit");
  });
});
