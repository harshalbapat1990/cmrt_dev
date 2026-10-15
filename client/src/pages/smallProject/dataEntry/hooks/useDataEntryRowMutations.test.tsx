import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import type { DataEntryRow } from "../dataEntryTypes";
import { useDataEntryRowMutations } from "./useDataEntryRowMutations";
import type { CalcConfig } from "../useEmissionsCalc";

vi.mock("@/services/ActivityData.service", () => ({
  default: { deleteRow: vi.fn(), updateRow: vi.fn() },
}));
vi.mock("../refurbishmentTableConfig", () => ({ fetchAllActiveMrFactors: vi.fn() }));

describe("useDataEntryRowMutations synchronized component deletion", () => {
  it("deletes the linked replacement row before removing the component", async () => {
    const component: DataEntryRow = { id: "component-1" };
    const replacement: DataEntryRow = {
      id: "replacement-1",
      _fromApi: true,
      _syncedSourceId: "component-1",
    };
    const componentRows: DataEntryRow[] = [component];
    const replacementRows: DataEntryRow[] = [replacement];
    const updateRows = vi.fn();
    const setDeleteTarget = vi.fn();
    const setErrorForKey = vi.fn();
    const refreshOptionTotals = vi.fn(async () => undefined);
    vi.mocked(ActivityDataService.deleteRow).mockResolvedValue(undefined as never);
    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: (key) => key === "componentRepl" ? replacementRows : componentRows,
      updateRows,
      setErrorForKey,
      getCalcConfig: () => null,
      computeEmissionsForRow: async () => null,
      refreshOptionTotals,
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: { id: "component-1", tableKey: "component" },
      setDeleteTarget,
    }));

    await act(async () => result.current.doDeleteRow());

    expect(ActivityDataService.deleteRow).toHaveBeenNthCalledWith(1, "replacement-1");
    expect(ActivityDataService.deleteRow).toHaveBeenNthCalledWith(2, "component-1");
    expect(updateRows).toHaveBeenCalledWith("componentRepl", expect.any(Function));
    expect(updateRows).toHaveBeenCalledWith("component", expect.any(Function));
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
    expect(setDeleteTarget).toHaveBeenCalledWith(null);
  });

  it("synchronizes an edited component quantity through the replacement update action", async () => {
    const component: DataEntryRow = { id: "component-1", quantity: 2, _fromApi: true };
    const replacement: DataEntryRow = {
      id: "replacement-1",
      quantity: 2,
      _fromApi: true,
      _syncedSourceId: "component-1",
    };
    const config: CalcConfig = {
      grade: 1,
      requiredKeys: [],
      triggerKeys: ["quantity"],
      buildPayload: () => ({}),
      calculate: async () => null,
      mapResultToRow: () => ({}),
    };
    const componentRows = [component];
    const replacementRows = [replacement];
    const updateRows = vi.fn();
    const refreshOptionTotals = vi.fn(async () => undefined);
    const computeEmissionsForRow = vi.fn(async (key: string, row: DataEntryRow) =>
      key === "componentRepl" ? { total_emissions_tco2e: Number(row.quantity) * 2 } : { total_emissions_tco2e: 6 },
    );
    vi.mocked(ActivityDataService.updateRow).mockResolvedValue(undefined as never);

    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: (key) => key === "componentRepl" ? replacementRows : componentRows,
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => config,
      computeEmissionsForRow,
      refreshOptionTotals,
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: null,
      setDeleteTarget: vi.fn(),
    }));

    await act(async () => result.current.onRowPatch("component", vi.fn())({
      id: "component-1",
      patch: { quantity: 5 },
      item: component,
    }));

    expect(computeEmissionsForRow).toHaveBeenCalledWith("componentRepl", expect.objectContaining({ quantity: 5 }));
    expect(ActivityDataService.updateRow).toHaveBeenNthCalledWith(2, "replacement-1", expect.objectContaining({
      quantity: 5,
      emissions_tco2e: 10,
      extra_fields: expect.not.objectContaining({ _fromApi: true, id: "replacement-1" }),
    }));
    expect(updateRows).toHaveBeenCalledWith("componentRepl", expect.any(Function));
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("keeps a row in place and leaves confirmation open when deletion fails", async () => {
    const updateRows = vi.fn();
    const setDeleteTarget = vi.fn();
    vi.mocked(ActivityDataService.deleteRow).mockRejectedValueOnce(new Error("Delete failed"));
    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: () => [],
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => null,
      computeEmissionsForRow: async () => null,
      refreshOptionTotals: vi.fn(async () => undefined),
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: { id: "row-1", tableKey: "asset" },
      setDeleteTarget,
    }));

    await expect(result.current.doDeleteRow()).rejects.toThrow("Delete failed");
    expect(updateRows).not.toHaveBeenCalled();
    expect(setDeleteTarget).not.toHaveBeenCalledWith(null);
  });
});
