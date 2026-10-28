import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { resolveTableConfig } from "../tableConfigRegistry";
import { createNewRowSaveHandler } from "./newRowSaveHandler";

vi.mock("@/services/ActivityData.service", () => ({
  default: { createRow: vi.fn() },
}));
vi.mock("../tableConfigRegistry", () => ({
  resolveTableConfig: vi.fn(),
}));

describe("createNewRowSaveHandler server calculation result", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the persisted calculation instead of an optimistic asset preview", async () => {
    vi.mocked(resolveTableConfig).mockReturnValue({ rules: [] } as never);
    vi.mocked(ActivityDataService.createRow).mockResolvedValue({
      id: "saved-asset",
      emissions_tco2e: "24322.5",
      extra_fields: {},
    } as never);
    const updateRows = vi.fn();
    const handler = createNewRowSaveHandler({
      activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" } as never,
      projectId: "project-1",
      activeOptionId: "option-1",
      activePeriod: null,
      user: null,
      getRows: () => [],
      updateRows,
      setErrorForKey: vi.fn(),
      resolveMetricId: vi.fn().mockResolvedValue("metric-1"),
      apiRowToUiRow: (row) => ({ id: row.id, emissions_tco2e: row.emissions_tco2e }),
      computeEmissionsForRow: vi.fn().mockResolvedValue({ total_emissions_tco2e: 68550 }),
      refreshOptionTotals: vi.fn().mockResolvedValue(undefined),
      validateComponentReplLife: () => null,
      validateElectricityYear: () => null,
      recalcElectricitySiblings: vi.fn().mockResolvedValue(undefined),
    });

    await expect(handler({
      quantity: 150000000,
      mastertype: "Road",
      typecast: "Low Use Road",
      sensitivity: "Mid",
      functional_unit: "CAPEX",
    }, "asset")).resolves.toBe(true);

    const addRow = updateRows.mock.calls[0]?.[1] as (rows: unknown[]) => unknown[];
    expect(addRow([])).toEqual([expect.objectContaining({
      id: "saved-asset",
      emissions_tco2e: "24322.5",
      total_emissions_tco2e: "24322.5",
    })]);
  });
});
